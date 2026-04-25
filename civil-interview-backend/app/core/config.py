"""Central configuration loaded from .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(BACKEND_ENV_FILE, override=True)


def _env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def _env_int(*keys: str, default: int) -> int:
    raw = _env(*keys, default=str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_bool(*keys: str, default: bool) -> bool:
    raw = _env(*keys, default="true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class Settings:
    secret_key: str = _env("SECRET_KEY", default="civil-demo-secret")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
    allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")
    database_url: str = _env("DATABASE_URL", default="sqlite:///./civil_interview.db")

    wechat_pay_enabled: bool = _env_bool("WECHAT_PAY_ENABLED", default=False)
    wechat_pay_mock_mode: bool = _env_bool("WECHAT_PAY_MOCK_MODE", default=True)
    wechat_pay_scene: str = _env("WECHAT_PAY_SCENE", default="mini_program")
    wechat_pay_appid: str = _env("WECHAT_PAY_APPID", default="wx_mock_miniprogram_appid")
    wechat_pay_mchid: str = _env("WECHAT_PAY_MCHID", default="1900000001")
    wechat_pay_notify_url: str = _env("WECHAT_PAY_NOTIFY_URL", default="https://mock.example.com/payment/callback/wechat")
    wechat_pay_api_v3_key: str = _env("WECHAT_PAY_API_V3_KEY", default="MOCK_API_V3_KEY_REPLACE_ME")
    wechat_pay_serial_no: str = _env("WECHAT_PAY_SERIAL_NO", default="MOCK_SERIAL_NO_REPLACE_ME")
    wechat_pay_private_key_path: str = _env("WECHAT_PAY_PRIVATE_KEY_PATH", default="certs/mock_apiclient_key.pem")
    wechat_pay_platform_cert_path: str = _env("WECHAT_PAY_PLATFORM_CERT_PATH", default="certs/mock_wechatpay_platform.pem")
    wechat_pay_api_base: str = _env("WECHAT_PAY_API_BASE", default="https://api.mch.weixin.qq.com")
    wechat_pay_request_timeout: int = _env_int("WECHAT_PAY_REQUEST_TIMEOUT", default=10)


settings = Settings()
