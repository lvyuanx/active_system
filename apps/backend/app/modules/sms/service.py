import json
import re
import time
from typing import Any

from app.core.config import Settings
from app.core.database import transaction


SMS_RATE_LIMIT_SECONDS = 60
SMS_RATE_LIMIT_MILLISECONDS = SMS_RATE_LIMIT_SECONDS * 1000
COUNTRY_CODE = "86"
CHINA_MOBILE_PATTERN = re.compile(r"^1[3-9][0-9]{9}$")
SMS_CODE_PATTERN = re.compile(r"^[0-9]{4,8}$")


class SmsConfigurationError(Exception):
    """短信服务配置或 SDK 不可用。"""


class SmsProviderError(Exception):
    """阿里云短信接口调用失败。"""


class SmsRateLimitError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(retry_after)
        self.retry_after = retry_after


def normalize_phone(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("请输入有效的中国大陆手机号")
    value = value.strip()
    if not CHINA_MOBILE_PATTERN.fullmatch(value):
        raise ValueError("请输入有效的中国大陆手机号")
    return value


def normalize_sms_code(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("请输入 4-8 位数字验证码")
    value = value.strip()
    if not SMS_CODE_PATTERN.fullmatch(value):
        raise ValueError("请输入 4-8 位数字验证码")
    return value


def validate_sms_configuration(settings: Settings) -> None:
    if not settings.aliyun_sms_sign_name or not settings.aliyun_sms_template_code:
        raise SmsConfigurationError("短信签名和模板未配置")


def build_sms_queries(phone: str, settings: Settings) -> dict[str, Any]:
    queries: dict[str, Any] = {
        "CountryCode": COUNTRY_CODE,
        "PhoneNumber": phone,
        "SignName": settings.aliyun_sms_sign_name,
        "TemplateCode": settings.aliyun_sms_template_code,
        "TemplateParam": json.dumps(
            {
                "code": "##code##",
                "min": str(max(1, settings.aliyun_sms_valid_time // 60)),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "CodeLength": settings.aliyun_sms_code_length,
        "ValidTime": settings.aliyun_sms_valid_time,
        "DuplicatePolicy": 1,
        "Interval": SMS_RATE_LIMIT_SECONDS,
        "CodeType": 1,
        "ReturnVerifyCode": False,
    }
    if settings.aliyun_sms_scheme_name:
        queries["SchemeName"] = settings.aliyun_sms_scheme_name
    return queries


def build_check_sms_queries(phone: str, code: str, settings: Settings) -> dict[str, Any]:
    queries: dict[str, Any] = {
        "CountryCode": COUNTRY_CODE,
        "PhoneNumber": phone,
        "VerifyCode": code,
    }
    if settings.aliyun_sms_scheme_name:
        queries["SchemeName"] = settings.aliyun_sms_scheme_name
    return queries


def reserve_sms_send(phone: str, settings: Settings) -> None:
    now = time.time_ns() // 1_000_000
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT last_sent_at FROM sms_verification_sends WHERE phone = ?",
            (phone,),
        ).fetchone()
        if row:
            elapsed = max(0, now - int(row["last_sent_at"]))
            if elapsed < SMS_RATE_LIMIT_MILLISECONDS:
                remaining = SMS_RATE_LIMIT_MILLISECONDS - elapsed
                raise SmsRateLimitError((remaining + 999) // 1000)
            connection.execute(
                "UPDATE sms_verification_sends SET last_sent_at = ? WHERE phone = ?",
                (now, phone),
            )
        else:
            connection.execute(
                "INSERT INTO sms_verification_sends(phone, last_sent_at) VALUES (?, ?)",
                (phone, now),
            )


def _call_aliyun(
    action: str,
    queries: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_openapi.client import Client as OpenApiClient
        from alibabacloud_tea_util import models as util_models
    except ImportError as error:
        raise SmsConfigurationError("阿里云短信 SDK 未安装") from error

    try:
        credential = CredentialClient()
        config = open_api_models.Config(credential=credential)
        config.endpoint = settings.aliyun_sms_endpoint
        client = OpenApiClient(config)
        params = open_api_models.Params(
            action=action,
            version="2017-05-25",
            protocol="HTTPS",
            method="POST",
            auth_type="AK",
            style="RPC",
            pathname="/",
            req_body_type="json",
            body_type="json",
        )
        request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(queries)
        )
        response = client.call_api(params, request, util_models.RuntimeOptions())
    except SmsConfigurationError:
        raise
    except Exception as error:
        raise SmsProviderError("阿里云短信请求失败") from error

    body = response.get("body") if isinstance(response, dict) else None
    if not isinstance(body, dict) or body.get("Code") != "OK" or body.get("Success") is False:
        raise SmsProviderError("阿里云短信返回失败")
    return body


def _send_via_aliyun(phone: str, settings: Settings) -> None:
    _call_aliyun("SendSmsVerifyCode", build_sms_queries(phone, settings), settings)


def _check_via_aliyun(phone: str, code: str, settings: Settings) -> bool:
    body = _call_aliyun("CheckSmsVerifyCode", build_check_sms_queries(phone, code, settings), settings)
    model = body.get("Model")
    if not isinstance(model, dict):
        raise SmsProviderError("阿里云短信核验响应异常")
    result = model.get("VerifyResult")
    if result == "PASS":
        return True
    if result == "UNKNOWN":
        return False
    raise SmsProviderError("阿里云短信核验结果异常")


def send_sms_code(phone: str, settings: Settings) -> None:
    validate_sms_configuration(settings)
    reserve_sms_send(phone, settings)
    _send_via_aliyun(phone, settings)


def check_sms_code(phone: str, code: str, settings: Settings) -> bool:
    validate_sms_configuration(settings)
    return _check_via_aliyun(phone, code, settings)
