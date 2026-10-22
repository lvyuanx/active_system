from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    database_path: str = "./data/active_system.db"
    media_root: str = "./data/media"
    jwt_secret: str = "development-only-change-this-secret"
    jwt_expire_minutes: int = 1440
    danmaku_token_secret: str = ""
    lottery_security_code: str = ""
    superuser_username: str = "admin"
    superuser_password: str = ""
    aliyun_sms_endpoint: str = "dypnsapi.aliyuncs.com"
    aliyun_sms_sign_name: str = ""
    aliyun_sms_template_code: str = ""
    aliyun_sms_scheme_name: str = ""
    aliyun_sms_code_length: int = 6
    aliyun_sms_valid_time: int = 300
    wechat_miniapp_appid: str = ""
    wechat_miniapp_secret: str = ""
    wechat_miniapp_page: str = "pages/entry/index"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
