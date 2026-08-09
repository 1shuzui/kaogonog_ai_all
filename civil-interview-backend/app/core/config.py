"""
后端配置中心，把根目录 `.env`、后端 `.env` 和运行环境变量整理成统一的 `settings` 对象。

本文件集中决定外部依赖的默认口径：MySQL 连接、Redis 缓存、DeepSeek/Qwen 模型、FunASR ONNX/VAD、
微信小程序虚拟支付、媒体上传限制和退款策略。根 `.env` 先加载，后端 `.env` 可以覆盖它，
这是为了本地多项目共用配置时仍能让后端单独修正敏感项。新增配置时优先放在这里，避免服务层直接读取环境变量导致本地、
服务器和测试环境行为不一致。

@param: 无；模块导入时从环境变量和 `.env` 文件读取配置。
@return: 暴露单例 `settings`，供数据库、AI、支付、缓存和路由模块读取。
@raises ImportError: `dotenv` 等配置依赖缺失时导入失败；配置值格式错误通常在调用方使用时暴露。
"""
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


def _env_float(*keys: str, default: float) -> float:
    raw = _env(*keys, default=str(default))
    try:
        return float(raw)
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
    """
    后端运行配置对象，统一约束数据库、缓存、模型、ASR 和微信虚拟支付的环境变量口径。

    这里不用 Pydantic Settings，是为了兼容当前“根目录 `.env` + 后端 `.env` 后加载覆盖”的部署习惯。
    MySQL 可以通过 `DATABASE_URL` 显式指定，也可以由 `MYSQL_*` 拼接；兜底 SQLite 只服务本地临时运行，
    现网和后续开发仍应以 MySQL 为准。FunASR、Redis 和微信虚拟支付配置集中在这里，避免服务层各自读环境变量，
    导致本地、服务器和测试口径漂移。

    @param: 无；字段在类定义时从环境变量或 `.env` 文件读取。
    @return: 可实例化的配置对象；模块底部的 `settings` 是全项目共享单例。
    @raises: 类定义阶段不主动抛出业务异常；依赖缺失、环境变量格式异常会在导入或调用时暴露。
    """
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
    # 统一使用外部模型完成点评；本地参考答案评分只作为明确开启的离线调试选项。
    local_reference_scoring: bool = _env_bool("LOCAL_REFERENCE_SCORING", default=False)
    qwen_api_key: str = _env("QWEN_API_KEY", "DASHSCOPE_API_KEY", default=llm_api_key)
    qwen_base_url: str = _env("QWEN_BASE_URL", default=llm_base_url)
    qwen_model: str = _env("QWEN_MODEL", default=llm_model)
    qwen_asr_model: str = _env("QWEN_ASR_MODEL", default=llm_asr_model)
    llm_timeout_seconds: int = _env_int("LLM_TIMEOUT_SECONDS", default=25)
    redis_url: str = _env("REDIS_URL", default="")
    redis_cache_ttl_questions: int = _env_int("REDIS_CACHE_TTL_QUESTIONS", default=3600)
    redis_cache_ttl_llm: int = _env_int("REDIS_CACHE_TTL_LLM", default=86400)
    redis_cache_ttl_transcript: int = _env_int("REDIS_CACHE_TTL_TRANSCRIPT", default=3600)

    asr_provider: str = _env("ASR_PROVIDER", default="funasr_onnx")
    asr_device: str = _env("ASR_DEVICE", default="cpu")
    asr_intra_op_num_threads: int = _env_int("ASR_INTRA_OP_NUM_THREADS", default=4)
    asr_max_segment_seconds: float = _env_float("ASR_MAX_SEGMENT_SECONDS", default=30.0)
    asr_segment_padding_ms: int = _env_int("ASR_SEGMENT_PADDING_MS", default=120)
    funasr_model_name: str = _env(
        "FUNASR_MODEL_NAME",
        default="damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-onnx",
    )
    funasr_vad_model_name: str = _env(
        "FUNASR_VAD_MODEL_NAME",
        default="damo/speech_fsmn_vad_zh-cn-16k-common-onnx",
    )
    funasr_punc_model_name: str = _env(
        "FUNASR_PUNC_MODEL_NAME",
        default="damo/punc_ct-transformer_zh-cn-common-vocab272727-onnx",
    )
    funasr_model_revision: str = _env("FUNASR_MODEL_REVISION", default="v2.0.4")
    funasr_vad_model_revision: str = _env("FUNASR_VAD_MODEL_REVISION", default="v2.0.4")
    funasr_punc_model_revision: str = _env("FUNASR_PUNC_MODEL_REVISION", default="v2.0.4")
    funasr_quantize: bool = _env_bool("FUNASR_QUANTIZE", default=True)
    funasr_vad_max_end_sil_ms: int = _env_int("FUNASR_VAD_MAX_END_SIL_MS", default=800)
    funasr_enable_punc: bool = _env_bool("FUNASR_ENABLE_PUNC", default=True)
    modelscope_cache: str = _env("MODELSCOPE_CACHE", default=str(BACKEND_ROOT / "storage" / "modelscope_cache"))

    wechat_pay_enabled: bool = _env_bool("WECHAT_PAY_ENABLED", default=False)
    wechat_pay_scene: str = _env("WECHAT_PAY_SCENE", default="mini_program_virtual")
    wechat_pay_appid: str = _env("WECHAT_PAY_APPID", default="")
    wechat_pay_request_timeout: int = _env_int("WECHAT_PAY_REQUEST_TIMEOUT", default=10)
    wechat_miniprogram_app_secret: str = _env("WECHAT_MINIPROGRAM_APP_SECRET", "WECHAT_APP_SECRET", default="")

    wechat_virtual_pay_offer_id: str = _env("WECHAT_VIRTUAL_PAY_OFFER_ID", default="")
    wechat_virtual_pay_mode: str = _env("WECHAT_VIRTUAL_PAY_MODE", default="short_series_goods")
    wechat_virtual_pay_env: int = _env_int("WECHAT_VIRTUAL_PAY_ENV", default=0)
    wechat_virtual_pay_app_key: str = _env("WECHAT_VIRTUAL_PAY_APP_KEY", "WECHAT_VIRTUAL_PAY_PROD_APP_KEY", default="")
    wechat_virtual_pay_sandbox_app_key: str = _env(
        "WECHAT_VIRTUAL_PAY_SANDBOX_APP_KEY",
        "WECHAT_VIRTUAL_PAY_APP_KEY_SANDBOX",
        default="",
    )
    wechat_virtual_pay_product_map_json: str = _env("WECHAT_VIRTUAL_PAY_PRODUCT_MAP_JSON", default="")
    wechat_virtual_pay_product_price_map_json: str = _env("WECHAT_VIRTUAL_PAY_PRODUCT_PRICE_MAP_JSON", default="")


settings = Settings()
