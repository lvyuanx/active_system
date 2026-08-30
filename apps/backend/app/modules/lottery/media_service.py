"""抽奖奖品图片与活动/奖品绑定的服务。"""

from dataclasses import dataclass
import logging
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.database import transaction
from app.modules.files.service import (
    MediaError,
    StoredMedia,
    remove_storage_key,
    scan_orphan_files,
    storage_path,
    store_uploaded_image,
)

from .models import LotteryConfigError, LotteryPrizeImageResponse
from .repository import prize_image_url


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrizeImageFile:
    image_id: str
    mime: str
    path: Path


def _prize_row(settings: Settings, activity_id: str, prize_id: int):
    with transaction(settings) as connection:
        return connection.execute(
            "SELECT prize_id, image_id, image_storage_key, image_mime, image_size "
            "FROM lottery_prizes WHERE activity_id = ? AND prize_id = ?",
            (activity_id, prize_id),
        ).fetchone()


def _require_prize(settings: Settings, activity_id: str, prize_id: int):
    row = _prize_row(settings, activity_id, prize_id)
    if not row:
        raise LotteryConfigError("invalid_prize", "奖品不存在或不属于当前活动")
    return row


def _image_response(activity_id: str, prize_id: int, stored: StoredMedia) -> LotteryPrizeImageResponse:
    return LotteryPrizeImageResponse(
        image_url=prize_image_url(activity_id, prize_id, stored.image_id),
        image_id=stored.image_id,
        mime=stored.mime,
        size=stored.size,
    )


async def replace_prize_image(
    activity_id: str,
    prize_id: int,
    upload: UploadFile,
    settings: Settings,
) -> LotteryPrizeImageResponse:
    _require_prize(settings, activity_id, prize_id)
    stored = await store_uploaded_image(upload, settings)
    old_storage_key: str | None = None
    try:
        with transaction(settings) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT image_storage_key FROM lottery_prizes "
                "WHERE activity_id = ? AND prize_id = ?",
                (activity_id, prize_id),
            ).fetchone()
            if not row:
                raise LotteryConfigError("invalid_prize", "奖品不存在或不属于当前活动")
            old_storage_key = row["image_storage_key"]
            connection.execute(
                "UPDATE lottery_prizes SET image_id = ?, image_storage_key = ?, image_mime = ?, image_size = ? "
                "WHERE activity_id = ? AND prize_id = ?",
                (
                    stored.image_id,
                    stored.storage_key,
                    stored.mime,
                    stored.size,
                    activity_id,
                    prize_id,
                ),
            )
    except Exception:
        remove_storage_key(settings, stored.storage_key)
        raise
    if old_storage_key:
        remove_storage_key(settings, str(old_storage_key))
    scan_lottery_media(settings)
    return _image_response(activity_id, prize_id, stored)


def remove_prize_image(
    activity_id: str,
    prize_id: int,
    settings: Settings,
) -> LotteryPrizeImageResponse:
    old_storage_key: str | None = None
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT image_storage_key FROM lottery_prizes WHERE activity_id = ? AND prize_id = ?",
            (activity_id, prize_id),
        ).fetchone()
        if not row:
            raise LotteryConfigError("invalid_prize", "奖品不存在或不属于当前活动")
        old_storage_key = row["image_storage_key"]
        connection.execute(
            "UPDATE lottery_prizes SET image_id = NULL, image_storage_key = NULL, "
            "image_mime = NULL, image_size = NULL WHERE activity_id = ? AND prize_id = ?",
            (activity_id, prize_id),
        )
    if old_storage_key:
        remove_storage_key(settings, str(old_storage_key))
    scan_lottery_media(settings)
    return LotteryPrizeImageResponse(image_url=None)


def get_prize_image_file(
    activity_id: str,
    prize_id: int,
    requested_image_id: str | None,
    settings: Settings,
) -> PrizeImageFile:
    row = _require_prize(settings, activity_id, prize_id)
    image_id = str(row["image_id"]) if row["image_id"] else None
    if not image_id or (requested_image_id and requested_image_id != image_id):
        raise LotteryConfigError("image_not_found", "图片不存在")
    storage_key = row["image_storage_key"]
    mime = row["image_mime"]
    if not storage_key or not mime:
        raise LotteryConfigError("image_not_found", "图片不存在")
    try:
        path = storage_path(settings, str(storage_key))
    except MediaError as error:
        logger.warning("奖品图片存储标识无效")
        raise LotteryConfigError("image_not_found", "图片不存在") from error
    if not path.is_file() or path.is_symlink():
        raise LotteryConfigError("image_not_found", "图片不存在")
    return PrizeImageFile(image_id, str(mime), path)


def cleanup_lottery_media_keys(settings: Settings, storage_keys: set[str] | list[str]) -> None:
    for storage_key in storage_keys:
        remove_storage_key(settings, storage_key)
    scan_lottery_media(settings)


def scan_lottery_media(settings: Settings, *, grace_seconds: int = 300) -> list[str]:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT image_storage_key FROM lottery_prizes WHERE image_storage_key IS NOT NULL"
        ).fetchall()
    references = {str(row["image_storage_key"]) for row in rows}
    return scan_orphan_files(settings, references, grace_seconds=grace_seconds)
