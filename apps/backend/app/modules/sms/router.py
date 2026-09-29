from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.config import Settings, get_settings
from app.modules.activities.router import get_activity
from app.modules.sms.service import (
    SMS_RATE_LIMIT_SECONDS,
    SmsConfigurationError,
    SmsProviderError,
    SmsRateLimitError,
    check_sms_code,
    normalize_phone,
    normalize_sms_code,
    send_sms_code,
)


router = APIRouter(prefix="/activities", tags=["sms"])


class SmsCodeRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: object) -> str:
        return normalize_phone(value)


class SmsCodeVerifyRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)
    code: str = Field(min_length=4, max_length=8)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: object) -> str:
        return normalize_phone(value)

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, value: object) -> str:
        return normalize_sms_code(value)


class SmsCodeResponse(BaseModel):
    message: str = "验证码发送成功"
    expires_in: int
    retry_after: int = SMS_RATE_LIMIT_SECONDS


class SmsCodeVerifyResponse(BaseModel):
    verified: bool
    message: str


@router.post("/{activity_id}/auth/sms-code", response_model=SmsCodeResponse)
def send_activity_sms_code(
    activity_id: str,
    payload: SmsCodeRequest,
    settings: Settings = Depends(get_settings),
) -> SmsCodeResponse:
    get_activity(activity_id, settings)
    try:
        send_sms_code(payload.phone, settings)
    except SmsRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"验证码发送过于频繁，请在 {error.retry_after} 秒后重试",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except SmsConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="短信服务未配置",
        ) from error
    except SmsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="短信发送失败，请稍后重试",
        ) from error
    return SmsCodeResponse(expires_in=settings.aliyun_sms_valid_time)


@router.post(
    "/{activity_id}/auth/sms-code/verify",
    response_model=SmsCodeVerifyResponse,
)
def verify_activity_sms_code(
    activity_id: str,
    payload: SmsCodeVerifyRequest,
    settings: Settings = Depends(get_settings),
) -> SmsCodeVerifyResponse:
    get_activity(activity_id, settings)
    try:
        verified = check_sms_code(payload.phone, payload.code, settings)
    except SmsConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="短信服务未配置",
        ) from error
    except SmsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="短信核验失败，请稍后重试",
        ) from error
    return SmsCodeVerifyResponse(
        verified=verified,
        message="验证码校验成功" if verified else "验证码错误或已失效",
    )
