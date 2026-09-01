from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LotteryConfigError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


class LotteryDrawError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


class LotteryAwardInput(BaseModel):
    award_id: int | None = Field(default=None, ge=0)
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("奖项名称不能为空")
        return value


class LotteryPrizeInput(BaseModel):
    prize_id: int | None = Field(default=None, ge=0)
    award_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=100000)
    sort_order: int = Field(default=0, ge=0)
    is_enabled: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("奖品名称不能为空")
        return value


class LotteryEntryUpdate(BaseModel):
    is_blacklisted: bool = False
    is_whitelisted: bool = False

    @model_validator(mode="after")
    def validate_flags(self) -> "LotteryEntryUpdate":
        if self.is_blacklisted and self.is_whitelisted:
            raise ValueError("同一用户不能同时加入黑名单和白名单")
        return self


class LotterySecurityCodeRequest(BaseModel):
    security_code: str = Field(min_length=1, max_length=200)


class LotterySecurityCodeResponse(BaseModel):
    verified: bool = True


class LotteryConfigUpdate(BaseModel):
    no_repeat_across_prizes: bool | None = None
    rolling_name_count: int | None = Field(default=None, ge=1, le=20)
    awards: list[LotteryAwardInput] | None = None
    prizes: list[LotteryPrizeInput] | None = None

    @model_validator(mode="after")
    def reject_duplicates(self) -> "LotteryConfigUpdate":
        if self.awards is not None:
            names = [award.name.casefold() for award in self.awards]
            if len(names) != len(set(names)):
                raise ValueError("奖项名称不能重复")
        if self.prizes is not None:
            names = [prize.name.casefold() for prize in self.prizes]
            if len(names) != len(set(names)):
                raise ValueError("奖品名称不能重复")
        return self


class LotteryAward(BaseModel):
    award_id: int
    name: str
    sort_order: int


class LotteryPrize(BaseModel):
    prize_id: int
    award_id: int
    name: str
    quantity: int
    remaining_quantity: int
    sort_order: int
    is_enabled: bool
    image_url: str | None = None


class LotteryPrizeImageResponse(BaseModel):
    image_url: str | None
    image_id: str | None = None
    mime: str | None = None
    size: int | None = None


class LotteryEntry(BaseModel):
    activity_user_id: int
    username: str
    phone: str
    is_active: bool
    is_blacklisted: bool
    is_whitelisted: bool


LotteryEntryStatus = Literal["all", "eligible", "blacklisted", "whitelisted", "inactive"]


class LotteryEntrySummary(BaseModel):
    total: int = Field(ge=0)
    eligible: int = Field(ge=0)
    blacklisted: int = Field(ge=0)
    whitelisted: int = Field(ge=0)
    inactive: int = Field(ge=0)


class LotteryEntryPage(BaseModel):
    prize_id: int
    items: list[LotteryEntry]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    has_more: bool
    summary: LotteryEntrySummary


class LotteryEntryUpdateResponse(BaseModel):
    prize_id: int
    entry: LotteryEntry
    summary: LotteryEntrySummary


class LotteryConfigResponse(BaseModel):
    activity_id: str
    no_repeat_across_prizes: bool
    rolling_name_count: int
    awards: list[LotteryAward]
    prizes: list[LotteryPrize]
    updated_at: datetime


class LotteryDrawAdmin(BaseModel):
    draw_id: int
    activity_id: str
    award_id: int
    prize_id: int
    award_name: str
    prize_name: str
    draw_number: int
    remaining_quantity: int
    prize_image_url: str | None = None
    winner: dict[str, object]
    drawn_at: datetime


class LotteryDrawPublic(BaseModel):
    draw_id: int
    activity_id: str
    award_id: int
    prize_id: int
    award_name: str
    prize_name: str
    draw_number: int
    remaining_quantity: int
    prize_image_url: str | None = None
    winner: dict[str, object]
    drawn_at: datetime


class LotteryRoundParticipant(BaseModel):
    activity_user_id: int = Field(ge=1)
    username: str = Field(min_length=1, max_length=100)
    avatar_id: int = Field(ge=1, le=20)


class LotteryRoundPublic(BaseModel):
    round_id: str = Field(min_length=1, max_length=100)
    award_id: int = Field(ge=1)
    award_name: str = Field(min_length=1, max_length=100)
    prize_id: int = Field(ge=1)
    prize_name: str = Field(min_length=1, max_length=200)
    phase: Literal["rolling", "stopping"] = "rolling"
    participants: list[LotteryRoundParticipant]
    started_at: datetime


class LotteryHistoryPage(BaseModel):
    items: list[LotteryDrawAdmin]
    has_more: bool


@dataclass(frozen=True)
class LotteryDrawOutcome:
    draw: LotteryDrawAdmin
    public_draw: LotteryDrawPublic
    roll_names: list[str]
    idempotent: bool
