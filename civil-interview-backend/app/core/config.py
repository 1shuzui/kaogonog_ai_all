"""Central configuration loaded from .env"""
import os
from pathlib import Path
from urllib.parse import quote_plus

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


def _build_mysql_database_url() -> str:
    host = _env("MYSQL_HOST", default="").strip()
    user = _env("MYSQL_USER", default="").strip()
    password = _env("MYSQL_PASSWORD", default="")
    database = _env("MYSQL_DATABASE", default="").strip()
    if not all((host, user, database)):
        return ""

    port = _env_int("MYSQL_PORT", default=3306)
    charset = _env("MYSQL_CHARSET", default="utf8mb4").strip() or "utf8mb4"

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"

    return (
        f"mysql+pymysql://{auth}@{host}:{port}/{quote_plus(database)}"
        f"?charset={quote_plus(charset)}"
    )


class Settings:
    backend_root: Path = BACKEND_ROOT
    secret_key: str = _env("SECRET_KEY", default="civil-demo-secret")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
    allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")
    database_url: str = _env(
        "DATABASE_URL",
        default=_build_mysql_database_url() or "sqlite:///./civil_interview.db",
    )
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
    asr_provider: str = _env("ASR_PROVIDER", default="whisper")
    asr_device: str = _env("ASR_DEVICE", default="cpu")
    whisper_model_size: str = _env("WHISPER_MODEL_SIZE", default="base")
    whisper_cpu_threads: int = _env_int("WHISPER_CPU_THREADS", default=4)
    whisper_language: str = _env("WHISPER_LANGUAGE", default="zh")

    password_reset_code_ttl_minutes: int = _env_int("PASSWORD_RESET_CODE_TTL_MINUTES", default=10)
    password_reset_code_debug_response: bool = _env_bool("PASSWORD_RESET_CODE_DEBUG_RESPONSE", default=True)
    sms_provider: str = _env("SMS_PROVIDER", default="")
    sms_access_key_id: str = _env("SMS_ACCESS_KEY_ID", default="")
    sms_access_key_secret: str = _env("SMS_ACCESS_KEY_SECRET", default="")
    sms_sign_name: str = _env("SMS_SIGN_NAME", default="")
    sms_template_code: str = _env("SMS_TEMPLATE_CODE", default="")

    wechat_pay_enabled: bool = _env_bool("WECHAT_PAY_ENABLED", default=False)
    wechat_pay_mock_mode: bool = _env_bool("WECHAT_PAY_MOCK_MODE", default=True)
    wechat_pay_scene: str = _env("WECHAT_PAY_SCENE", default="mini_program")
    wechat_pay_appid: str = _env("WECHAT_PAY_APPID", "WECHAT_MINIPROGRAM_APPID", default="wxa31c6e32dfa4b178")
    wechat_pay_mchid: str = _env("WECHAT_PAY_MCHID", default="1744784195")
    wechat_pay_notify_url: str = _env("WECHAT_PAY_NOTIFY_URL", default="https://xzqianmianyuzhoukeji.com/api/payment/callback/wechat")
    wechat_pay_refund_notify_url: str = _env("WECHAT_PAY_REFUND_NOTIFY_URL", default="")
    wechat_pay_api_v3_key: str = _env("WECHAT_PAY_API_V3_KEY", default="MOCK_API_V3_KEY_REPLACE_ME")
    wechat_pay_serial_no: str = _env("WECHAT_PAY_SERIAL_NO", default="MOCK_SERIAL_NO_REPLACE_ME")
    wechat_pay_private_key_path: str = _env("WECHAT_PAY_PRIVATE_KEY_PATH", default="certs/mock_apiclient_key.pem")
    wechat_pay_platform_cert_path: str = _env("WECHAT_PAY_PLATFORM_CERT_PATH", default="certs/mock_wechatpay_platform.pem")
    wechat_pay_platform_serial_no: str = _env("WECHAT_PAY_PLATFORM_SERIAL_NO", default="")
    wechat_pay_public_key_path: str = _env("WECHAT_PAY_PUBLIC_KEY_PATH", default="")
    wechat_pay_public_key_id: str = _env("WECHAT_PAY_PUBLIC_KEY_ID", default="")
    wechat_pay_api_base: str = _env("WECHAT_PAY_API_BASE", default="https://api.mch.weixin.qq.com")
    wechat_pay_request_timeout: int = _env_int("WECHAT_PAY_REQUEST_TIMEOUT", default=10)
    wechat_miniprogram_app_secret: str = _env("WECHAT_MINIPROGRAM_APP_SECRET", "WECHAT_PAY_APP_SECRET", default="")
    wechat_miniprogram_api_base: str = _env("WECHAT_MINIPROGRAM_API_BASE", default="https://api.weixin.qq.com")
    wechat_pay_strict_appid_check: bool = _env_bool("WECHAT_PAY_STRICT_APPID_CHECK", default=True)
    wechat_pay_shipping_upload_enabled: bool = _env_bool("WECHAT_PAY_SHIPPING_UPLOAD_ENABLED", default=False)
    wechat_pay_shipping_item_desc: str = _env("WECHAT_PAY_SHIPPING_ITEM_DESC", default="公考面试AI测评服务")

    app_env: str = _env("APP_ENV", default="production")
    log_level: str = _env("LOG_LEVEL", default="INFO")
    log_format: str = _env("LOG_FORMAT", default="json")
    log_file: str = _env("LOG_FILE", default="")
    log_max_bytes: int = _env_int("LOG_MAX_BYTES", default=10 * 1024 * 1024)
    log_backup_count: int = _env_int("LOG_BACKUP_COUNT", default=10)
    log_retention_days: int = _env_int("LOG_RETENTION_DAYS", default=30)
    log_access_enabled: bool = _env_bool("LOG_ACCESS_ENABLED", default=True)


settings = Settings()
