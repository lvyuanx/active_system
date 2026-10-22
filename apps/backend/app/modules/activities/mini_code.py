from __future__ import annotations

from dataclasses import dataclass
import json
from threading import Lock
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.core.config import Settings


WECHAT_API_BASE = "https://api.weixin.qq.com"
TOKEN_PATH = "/cgi-bin/token"
CODE_PATH = "/wxa/getwxacode"
REQUEST_TIMEOUT_SECONDS = 10
TOKEN_REFRESH_MARGIN_SECONDS = 60


class MiniProgramCodeError(RuntimeError):
    """微信小程序码接口调用失败。"""

    def __init__(self, message: str, errcode: int | None = None) -> None:
        super().__init__(message)
        self.errcode = errcode


class MiniProgramCodeConfigurationError(MiniProgramCodeError):
    """微信小程序码生成所需配置缺失。"""


@dataclass(frozen=True)
class AccessTokenEntry:
    value: str
    expires_at: float


_token_cache: dict[str, AccessTokenEntry] = {}
_token_cache_lock = Lock()


def _read_response(request: Request) -> bytes:
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read()
    except HTTPError as error:
        try:
            detail = error.read().decode("utf-8", errors="replace")
        except OSError:
            detail = ""
        raise MiniProgramCodeError(f"微信接口 HTTP {error.code}: {detail[:200]}") from error
    except URLError as error:
        raise MiniProgramCodeError(f"无法连接微信接口: {error.reason}") from error
    except OSError as error:
        raise MiniProgramCodeError(f"调用微信接口失败: {error}") from error


def _parse_json(body: bytes, operation: str) -> dict[str, object]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MiniProgramCodeError(f"微信{operation}返回了无法解析的响应") from error
    if not isinstance(payload, dict):
        raise MiniProgramCodeError(f"微信{operation}返回了无效响应")
    errcode = payload.get("errcode")
    if isinstance(errcode, int) and errcode != 0:
        errmsg = payload.get("errmsg")
        detail = errmsg if isinstance(errmsg, str) and errmsg else "未知错误"
        raise MiniProgramCodeError(f"微信{operation}失败: {detail}", errcode=errcode)
    return payload


def _get_access_token(settings: Settings, force_refresh: bool = False) -> str:
    appid = settings.wechat_miniapp_appid.strip()
    secret = settings.wechat_miniapp_secret.strip()
    if not appid or not secret:
        raise MiniProgramCodeConfigurationError(
            "未配置 WECHAT_MINIAPP_APPID 或 WECHAT_MINIAPP_SECRET"
        )

    now = time.monotonic()
    with _token_cache_lock:
        cached = _token_cache.get(appid)
        if not force_refresh and cached and cached.expires_at > now:
            return cached.value

    query = urlencode({"grant_type": "client_credential", "appid": appid, "secret": secret})
    request = Request(f"{WECHAT_API_BASE}{TOKEN_PATH}?{query}", method="GET")
    payload = _parse_json(_read_response(request), "access_token")
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not isinstance(access_token, str) or not access_token:
        raise MiniProgramCodeError("微信 access_token 响应缺少 access_token")
    if not isinstance(expires_in, int) or expires_in <= 0:
        raise MiniProgramCodeError("微信 access_token 响应缺少有效 expires_in")

    entry = AccessTokenEntry(
        value=access_token,
        expires_at=time.monotonic() + max(1, expires_in - TOKEN_REFRESH_MARGIN_SECONDS),
    )
    with _token_cache_lock:
        _token_cache[appid] = entry
    return access_token


def _clear_access_token(appid: str, value: str) -> None:
    with _token_cache_lock:
        cached = _token_cache.get(appid)
        if cached and cached.value == value:
            _token_cache.pop(appid, None)


def _request_mini_code(access_token: str, page: str, activity_id: str) -> bytes:
    path = f"{page}?activity_id={quote(activity_id, safe='')}"
    request = Request(
        f"{WECHAT_API_BASE}{CODE_PATH}?{urlencode({'access_token': access_token})}",
        data=json.dumps({"path": path, "width": 430}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    body = _read_response(request)
    if body.lstrip().startswith(b"{"):
        _parse_json(body, "小程序码")
        raise MiniProgramCodeError("微信小程序码接口返回了空响应")
    if not body:
        raise MiniProgramCodeError("微信小程序码接口返回空图片")
    return body


def generate_mini_program_code(activity_id: str, settings: Settings) -> bytes:
    page = settings.wechat_miniapp_page.strip().lstrip("/")
    if not page or "?" in page or "#" in page:
        raise MiniProgramCodeConfigurationError(
            "WECHAT_MINIAPP_PAGE 必须是合法的小程序页面路径且不能携带参数"
        )

    appid = settings.wechat_miniapp_appid.strip()
    access_token = _get_access_token(settings)
    try:
        return _request_mini_code(access_token, page, activity_id)
    except MiniProgramCodeError as error:
        if error.errcode not in {40001, 40014, 42001}:
            raise
        _clear_access_token(appid, access_token)
        refreshed_token = _get_access_token(settings, force_refresh=True)
        return _request_mini_code(refreshed_token, page, activity_id)
