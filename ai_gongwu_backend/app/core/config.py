"""全局配置模块。

这个文件非常重要，建议先理解它：
1. 所有“可变”的配置都尽量放在这里，而不是散落在业务代码中。
2. 这里使用 pydantic-settings 读取环境变量，方便你后续接入 .env。
3. 统一配置后，后面要切换模型、改路径、调阈值都会轻松很多。
"""

from functools import lru_cache
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """系统配置对象。

    BaseSettings 的特点是：
    - 先读取类里的默认值
    - 如果环境变量里有同名配置，就自动覆盖默认值
    - 所以非常适合做“开发默认值 + 生产环境覆盖”
    """

    # =========================
    # 基础项目信息
    # =========================
    PROJECT_NAME: str = "公考面试AI测评系统"
    VERSION: str = "1.1.0"
    QUESTION_DB_PATH: str = "assets/questions"
    DATABASE_URL: str = "sqlite:///storage/ai_gongwu.db"

    # =========================
    # 大模型相关配置
    # =========================
    LLM_PROVIDER: str = "QWEN"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL_NAME: str = "qwen3-coder-plus"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 3
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    LLM_FORCE_JSON_RESPONSE: bool = True

    # =========================
    # 语音识别 / 视觉分析相关配置
    # =========================
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_CPU_THREADS: int = 4
    WHISPER_LANGUAGE: str = "zh"
    ENABLE_VISUAL_ANALYSIS: bool = True

    # =========================
    # 评分规则相关配置
    # =========================
    MIN_VALID_WORDS: int = 15
    MIN_WORDS_PENALTY_RATIO: float = 0.2
    SCORE_TOLERANCE: float = 2.0
    MAX_RATIONALE_CHARS: int = 400

    # =========================
    # 支持的媒体格式
    # =========================
    SUPPORTED_VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".avi", ".mov", ".mkv", ".webm")
    SUPPORTED_AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".m4a")

    # 读取 .env 文件。
    # extra="ignore" 表示 .env 中多出来的字段不会报错，适合开发期。
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        """返回后端项目根目录。

        当前文件路径是 app/core/config.py，
        parents[2] 刚好回到 ai_gongwu_backend 目录。
        """

        return BACKEND_ROOT

    def resolve_path(self, value: str | Path) -> Path:
        """把传入路径解析成真正可用的绝对路径。

        这样做的好处是：无论你是从项目根目录启动，还是从 backend 目录启动，
        相对路径都尽量能被正确识别，减少“本地能跑、换个目录就报错”的问题。
        """

        candidate = Path(value)
        if candidate.is_absolute():
            # 如果本来就是绝对路径，就直接返回。
            return candidate

        rooted_candidate = self.project_root / candidate
        if rooted_candidate.exists():
            # 优先尝试相对于 ai_gongwu_backend 根目录解析。
            return rooted_candidate

        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            # 如果上面的路径不存在，再尝试相对于当前工作目录解析。
            return cwd_candidate

        # 如果都没命中，默认仍然返回“相对于后端根目录”的结果，
        # 这样调用方后续报错时路径更稳定，也更容易排查。
        return rooted_candidate


@lru_cache()
def get_settings() -> Settings:
    """返回全局唯一的 Settings 实例。

    lru_cache 的作用是缓存第一次创建出来的对象，
    避免每次 import 或调用时都重新读取环境变量。
    """

    return Settings()


settings = get_settings()
