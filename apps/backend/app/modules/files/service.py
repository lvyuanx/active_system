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
LOTTERY_PRIZES_NAMESPACE = "lottery-prizes"
CHAT_STICKERS_NAMESPACE = "chat-stickers"
ALLOWED_IMAGE_TYPES = {
    ".jpg": ("image/jpeg", "jpg"),
    ".jpeg": ("image/jpeg", "jpg"),
    ".png": ("image/png", "png"),
    ".webp": ("image/webp", "webp"),
}
CHAT_STICKER_IMAGE_TYPES = {
    **ALLOWED_IMAGE_TYPES,
    ".gif": ("image/gif", "gif"),
}
NAMESPACE_IMAGE_TYPES = {
    LOTTERY_PRIZES_NAMESPACE: ALLOWED_IMAGE_TYPES,
    CHAT_STICKERS_NAMESPACE: CHAT_STICKER_IMAGE_TYPES,
}
SUPPORTED_PILLOW_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
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
    width: int
    height: int


def media_root(settings: Settings) -> Path:
    return Path(settings.media_root).expanduser().resolve()


def _assert_no_symlink_components(root: Path, target: Path, detail: str) -> None:
    try:
        relative_parts = target.relative_to(root).parts
    except ValueError as error:
        raise MediaError("invalid_storage_key", detail) from error
    current = root
    for part in relative_parts:
        current /= part
        if current.is_symlink():
            raise MediaError("invalid_storage_key", detail)


def media_namespace_root(settings: Settings, namespace: str) -> Path:
    if namespace not in NAMESPACE_IMAGE_TYPES:
        raise MediaError("invalid_namespace", "媒体命名空间无效")
    media_root_path = media_root(settings)
    root = media_root_path / namespace
    _assert_no_symlink_components(media_root_path, root, "媒体命名空间无效")
    if root.exists() and not root.is_dir():
        raise MediaError("invalid_storage_key", "媒体命名空间无效")
    root.mkdir(parents=True, exist_ok=True)
    _assert_no_symlink_components(media_root_path, root, "媒体命名空间无效")
    if not root.is_dir():
        raise MediaError("invalid_storage_key", "媒体命名空间无效")
    return root


def prize_media_root(settings: Settings) -> Path:
    return media_namespace_root(settings, LOTTERY_PRIZES_NAMESPACE)


def chat_sticker_media_root(settings: Settings) -> Path:
    return media_namespace_root(settings, CHAT_STICKERS_NAMESPACE)


def temporary_media_root(settings: Settings, namespace: str = LOTTERY_PRIZES_NAMESPACE) -> Path:
    if namespace not in NAMESPACE_IMAGE_TYPES:
        raise MediaError("invalid_namespace", "媒体命名空间无效")
    media_root_path = media_root(settings)
    root = media_root_path / ".tmp"
    if namespace != LOTTERY_PRIZES_NAMESPACE:
        root = root / namespace
    _assert_no_symlink_components(media_root_path, root, "临时媒体目录无效")
    if root.exists() and not root.is_dir():
        raise MediaError("invalid_storage_key", "临时媒体目录无效")
    root.mkdir(parents=True, exist_ok=True)
    _assert_no_symlink_components(media_root_path, root, "临时媒体目录无效")
    if not root.is_dir():
        raise MediaError("invalid_storage_key", "临时媒体目录无效")
    return root


def _safe_storage_key(storage_key: str, namespace: str = LOTTERY_PRIZES_NAMESPACE) -> tuple[str, ...]:
    if namespace not in NAMESPACE_IMAGE_TYPES:
        raise MediaError("invalid_namespace", "媒体命名空间无效")
    if not storage_key or "\\" in storage_key or "\x00" in storage_key:
        raise MediaError("invalid_storage_key", "图片资源不存在")
    path = PurePosixPath(storage_key)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != (namespace,):
        raise MediaError("invalid_storage_key", "图片资源不存在")
    if len(path.parts) != 2 or not path.parts[1]:
        raise MediaError("invalid_storage_key", "图片资源不存在")
    return path.parts


def storage_path(
    settings: Settings,
    storage_key: str,
    *,
    namespace: str = LOTTERY_PRIZES_NAMESPACE,
) -> Path:
    parts = _safe_storage_key(storage_key, namespace)
    root = media_root(settings)
    namespace_root = root / namespace
    _assert_no_symlink_components(root, namespace_root, "图片资源不存在")
    unresolved = namespace_root / parts[1]
    if unresolved.is_symlink():
        raise MediaError("invalid_storage_key", "图片资源不存在")
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(namespace_root)
    except ValueError as error:
        raise MediaError("invalid_storage_key", "图片资源不存在") from error
    if candidate.is_symlink():
        raise MediaError("invalid_storage_key", "图片资源不存在")
    return candidate


def remove_storage_key(
    settings: Settings,
    storage_key: str | None,
    *,
    namespace: str = LOTTERY_PRIZES_NAMESPACE,
) -> bool:
    if not storage_key:
        return True
    try:
        path = storage_path(settings, storage_key, namespace=namespace)
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


def _allowed_image_types(namespace: str) -> dict[str, tuple[str, str]]:
    try:
        return NAMESPACE_IMAGE_TYPES[namespace]
    except KeyError as error:
        raise MediaError("invalid_namespace", "媒体命名空间无效") from error


def _validate_image_file_details(
    path: Path,
    extension: str,
    declared_mime: str | None,
    allowed_image_types: dict[str, tuple[str, str]],
) -> tuple[str, int, int]:
    expected_mime = allowed_image_types[extension][0]
    if declared_mime != expected_mime:
        raise MediaError("image_mime_mismatch", "图片扩展名与声明类型不一致")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = image.format or ""
                actual_mime = SUPPORTED_PILLOW_FORMATS.get(image_format)
                width, height = image.size
                image.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
    ) as error:
        raise MediaError("invalid_image", "文件不是可识别的图片") from error
    if actual_mime != expected_mime:
        raise MediaError("image_mime_mismatch", "图片真实格式与扩展名不一致")
    if width <= 0 or height <= 0:
        raise MediaError("invalid_image", "文件不是可识别的图片")
    return expected_mime, width, height


def _validate_image_file(
    path: Path,
    extension: str,
    declared_mime: str | None,
    allowed_image_types: dict[str, tuple[str, str]] = ALLOWED_IMAGE_TYPES,
) -> str:
    return _validate_image_file_details(path, extension, declared_mime, allowed_image_types)[0]


async def store_uploaded_image(
    upload: UploadFile,
    settings: Settings,
    *,
    namespace: str = LOTTERY_PRIZES_NAMESPACE,
) -> StoredMedia:
    """分块写入临时文件，校验真实格式后原子移动到随机文件名。"""

    allowed_image_types = _allowed_image_types(namespace)
    media_namespace_root(settings, namespace)
    filename = upload.filename or ""
    if "\x00" in filename:
        raise MediaError("invalid_image", "图片文件名无效")
    extension = Path(filename).suffix.lower()
    if extension not in allowed_image_types:
        supported = "JPG、PNG、WebP" if namespace == LOTTERY_PRIZES_NAMESPACE else "JPG、PNG、WebP 或 GIF"
        raise MediaError("unsupported_image_type", f"仅支持 {supported} 图片")

    temporary_root = temporary_media_root(settings, namespace)
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
        mime, width, height = _validate_image_file_details(
            temporary_path,
            extension,
            upload.content_type,
            allowed_image_types,
        )
        image_id = uuid4().hex
        stored_extension = allowed_image_types[extension][1]
        storage_key = f"{namespace}/{image_id}.{stored_extension}"
        final_path = storage_path(settings, storage_key, namespace=namespace)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.replace(final_path)
        return StoredMedia(image_id, storage_key, mime, size, final_path, width, height)
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
    namespace: str = LOTTERY_PRIZES_NAMESPACE,
    grace_seconds: int = 300,
) -> list[str]:
    """清理过期临时文件和未被数据库引用的媒体文件。"""

    root = media_root(settings)
    now = time.time()
    _allowed_image_types(namespace)
    normalized_keys: set[str] = set()
    for key in referenced_storage_keys:
        try:
            normalized_keys.add("/".join(_safe_storage_key(key, namespace)))
        except MediaError:
            logger.warning("数据库中存在非法媒体标识，跳过该引用")
    cleaned: list[str] = []
    namespace_root = root / namespace
    try:
        _assert_no_symlink_components(root, namespace_root, "媒体命名空间无效")
        temporary_root = temporary_media_root(settings, namespace)
    except MediaError:
        logger.warning("媒体扫描根目录包含符号链接，跳过本次孤儿扫描")
        return cleaned
    scan_roots = [namespace_root, temporary_root]
    for scan_root in scan_roots:
        if scan_root.is_symlink():
            logger.warning("媒体扫描根目录是符号链接，跳过该目录")
            continue
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
