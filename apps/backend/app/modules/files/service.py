"""安全媒体文件的校验、落盘和清理。"""

from dataclasses import dataclass
import logging
from pathlib import Path, PurePosixPath
import time
import warnings
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings


logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    ".jpg": ("image/jpeg", "jpg"),
    ".jpeg": ("image/jpeg", "jpg"),
    ".png": ("image/png", "png"),
    ".webp": ("image/webp", "webp"),
}
SUPPORTED_PILLOW_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class MediaError(Exception):
    """可安全返回给调用方的媒体错误，不包含内部路径。"""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class StoredMedia:
    image_id: str
    storage_key: str
    mime: str
    size: int
    path: Path


def media_root(settings: Settings) -> Path:
    return Path(settings.media_root).expanduser().resolve()


def prize_media_root(settings: Settings) -> Path:
    root = media_root(settings) / "lottery-prizes"
    root.mkdir(parents=True, exist_ok=True)
    return root


def temporary_media_root(settings: Settings) -> Path:
    root = media_root(settings) / ".tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_storage_key(storage_key: str) -> tuple[str, ...]:
    if not storage_key or "\\" in storage_key or "\x00" in storage_key:
        raise MediaError("invalid_storage_key", "图片资源不存在")
    path = PurePosixPath(storage_key)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("lottery-prizes",):
        raise MediaError("invalid_storage_key", "图片资源不存在")
    if len(path.parts) != 2 or not path.parts[1]:
        raise MediaError("invalid_storage_key", "图片资源不存在")
    return path.parts


def storage_path(settings: Settings, storage_key: str) -> Path:
    parts = _safe_storage_key(storage_key)
    root = media_root(settings)
    unresolved = root / Path(*parts)
    if unresolved.is_symlink():
        raise MediaError("invalid_storage_key", "图片资源不存在")
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise MediaError("invalid_storage_key", "图片资源不存在") from error
    if candidate.is_symlink():
        raise MediaError("invalid_storage_key", "图片资源不存在")
    return candidate


def remove_storage_key(settings: Settings, storage_key: str | None) -> bool:
    if not storage_key:
        return True
    try:
        path = storage_path(settings, storage_key)
    except MediaError:
        logger.warning("拒绝清理非法媒体标识")
        return False
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
        return True
    except OSError:
        logger.exception("媒体文件清理失败")
        return False


def _validate_image_file(path: Path, extension: str, declared_mime: str | None) -> str:
    expected_mime = ALLOWED_IMAGE_TYPES[extension][0]
    if declared_mime != expected_mime:
        raise MediaError("image_mime_mismatch", "图片扩展名与声明类型不一致")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = image.format or ""
                actual_mime = SUPPORTED_PILLOW_FORMATS.get(image_format)
                image.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
        SyntaxError,
    ) as error:
        raise MediaError("invalid_image", "文件不是可识别的图片") from error
    if actual_mime != expected_mime:
        raise MediaError("image_mime_mismatch", "图片真实格式与扩展名不一致")
    return expected_mime


async def store_uploaded_image(upload: UploadFile, settings: Settings) -> StoredMedia:
    """分块写入临时文件，校验真实格式后原子移动到随机文件名。"""

    filename = upload.filename or ""
    if "\x00" in filename:
        raise MediaError("invalid_image", "图片文件名无效")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_TYPES:
        raise MediaError("unsupported_image_type", "仅支持 JPG、PNG 或 WebP 图片")

    temporary_root = temporary_media_root(settings)
    temporary_path = temporary_root / f"{uuid4().hex}.upload"
    size = 0
    try:
        await upload.seek(0)
        with temporary_path.open("xb") as target:
            while True:
                chunk = await upload.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_IMAGE_SIZE:
                    raise MediaError("image_too_large", "图片大小不能超过 5 MiB")
                target.write(chunk)
        mime = _validate_image_file(temporary_path, extension, upload.content_type)
        image_id = uuid4().hex
        stored_extension = ALLOWED_IMAGE_TYPES[extension][1]
        storage_key = f"lottery-prizes/{image_id}.{stored_extension}"
        final_path = storage_path(settings, storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.replace(final_path)
        return StoredMedia(image_id, storage_key, mime, size, final_path)
    except MediaError:
        raise
    except OSError as error:
        raise MediaError("storage_error", "图片存储失败，请稍后重试") from error
    finally:
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except OSError:
            logger.exception("临时媒体文件清理失败")


def scan_orphan_files(
    settings: Settings,
    referenced_storage_keys: set[str],
    *,
    grace_seconds: int = 300,
) -> list[str]:
    """清理过期临时文件和未被数据库引用的媒体文件。"""

    root = media_root(settings)
    now = time.time()
    normalized_keys: set[str] = set()
    for key in referenced_storage_keys:
        try:
            normalized_keys.add("/".join(_safe_storage_key(key)))
        except MediaError:
            logger.warning("数据库中存在非法媒体标识，跳过该引用")
    cleaned: list[str] = []
    scan_roots = [root / "lottery-prizes", root / ".tmp"]
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        try:
            candidates = tuple(scan_root.rglob("*"))
        except OSError:
            logger.exception("媒体孤儿扫描失败")
            continue
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                if now - candidate.stat().st_mtime < grace_seconds:
                    continue
                relative_key = candidate.relative_to(root).as_posix()
                if relative_key in normalized_keys:
                    continue
                candidate.unlink()
                cleaned.append(relative_key)
            except OSError:
                logger.exception("媒体孤儿文件清理失败")
    return cleaned
