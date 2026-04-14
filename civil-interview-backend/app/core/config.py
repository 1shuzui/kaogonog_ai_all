"""Central configuration loaded from .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"
SHARED_ENV_FILE = BACKEND_ROOT.parent / "ai_gongwu_backend" / ".env"

# Load the shared engine config first, then let backend-local overrides win.
load_dotenv(SHARED_ENV_FILE, override=False)
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


def _env_float(*keys: str, default: float) -> float:
    raw = _env(*keys, default=str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


class Settings:
    secret_key: str = _env("SECRET_KEY", default="civil-demo-secret")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
    allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")

    # LLM
    qwen_api_key: str = _env("QWEN_API_KEY", "LLM_API_KEY", default="")
    qwen_base_url: str = _env(
        "QWEN_BASE_URL",
        "LLM_BASE_URL",
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    qwen_model: str = _env("QWEN_MODEL", "LLM_MODEL_NAME", default="qwen-plus")
    qwen_asr_model: str = _env("QWEN_ASR_MODEL", "ASR_MODEL", default="")
    llm_timeout_seconds: float = _env_float("LLM_TIMEOUT_SECONDS", default=60.0)

    # Database (MySQL or SQLite fallback)
    database_url: str = _env("DATABASE_URL", default="sqlite:///./civil_interview.db")


settings = Settings()
