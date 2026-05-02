"""Central configuration loaded from .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(PROJECT_ENV_FILE, override=False)
load_dotenv(BACKEND_ENV_FILE, override=True)

DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"
QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_DEFAULT_MODEL = "qwen-plus"


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


def _has_env(*keys: str) -> bool:
    return any(os.getenv(key) not in (None, "") for key in keys)


def _infer_llm_provider() -> str:
    configured = _env("LLM_PROVIDER", default="").strip().lower()
    if configured:
        return configured
    if _has_env("LLM_API_KEY", "DEEPSEEK_API_KEY"):
        return "deepseek"
    if _has_env("QWEN_API_KEY", "DASHSCOPE_API_KEY"):
        return "qwen"
    return "deepseek"


def _default_llm_base_url(provider: str) -> str:
    return QWEN_DEFAULT_BASE_URL if provider == "qwen" else DEEPSEEK_DEFAULT_BASE_URL


def _default_llm_model(provider: str) -> str:
    return QWEN_DEFAULT_MODEL if provider == "qwen" else DEEPSEEK_DEFAULT_MODEL


class Settings:
    secret_key: str = _env("SECRET_KEY", default="civil-demo-secret")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
    allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")
    database_url: str = _env("DATABASE_URL", default="sqlite:///./civil_interview.db")
    llm_provider: str = _infer_llm_provider()
    llm_api_key: str = _env("LLM_API_KEY", "DEEPSEEK_API_KEY", "QWEN_API_KEY", "DASHSCOPE_API_KEY", default="")
    llm_base_url: str = _env(
        "LLM_BASE_URL",
        "DEEPSEEK_BASE_URL",
        "QWEN_BASE_URL",
        default=_default_llm_base_url(llm_provider),
    )
    llm_model: str = _env("LLM_MODEL", "DEEPSEEK_MODEL", "QWEN_MODEL", default=_default_llm_model(llm_provider))
    llm_asr_model: str = _env("LLM_ASR_MODEL", "QWEN_ASR_MODEL", default="")
    qwen_api_key: str = _env("QWEN_API_KEY", "DASHSCOPE_API_KEY", default=llm_api_key)
    qwen_base_url: str = _env("QWEN_BASE_URL", default=llm_base_url)
    qwen_model: str = _env("QWEN_MODEL", default=llm_model)
    qwen_asr_model: str = _env("QWEN_ASR_MODEL", default=llm_asr_model)
    llm_timeout_seconds: int = _env_int("LLM_TIMEOUT_SECONDS", default=25)

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
