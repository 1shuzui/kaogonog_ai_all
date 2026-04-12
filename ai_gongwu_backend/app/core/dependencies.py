"""依赖注入模块。

FastAPI 的 Depends 会从这里拿到“共享服务实例”。
你可以把这里理解成“对象装配中心”：
路由不负责自己 new 很多对象，而是统一从这里获取。
"""

from functools import lru_cache

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.flow import InterviewFlowService
from app.services.evaluation_store import EvaluationStore
from app.services.llm.client import LLMClient
from app.services.question_bank import QuestionBank


@lru_cache()
def get_llm_client() -> LLMClient:
    """返回全局共享的 LLM 客户端实例。

    为什么要缓存？
    - 避免每个请求都重新初始化一次客户端
    - 结构更清晰，后续如果要加监控、埋点、限流，也更好统一管理
    """

    return LLMClient()


@lru_cache()
def get_question_bank() -> QuestionBank:
    """返回加载到内存中的题库对象。

    题库 JSON 不需要每次请求都重新读文件，
    缓存在内存里能减少磁盘 IO，提高响应速度。
    """

    return QuestionBank(settings.QUESTION_DB_PATH)


@lru_cache()
def get_evaluation_store() -> EvaluationStore:
    """返回测评结果持久化服务。"""

    return EvaluationStore(session_factory=SessionLocal)


@lru_cache()
def get_flow_service() -> InterviewFlowService:
    """返回业务编排服务。

    这个服务会串起：
    1. 题库读取
    2. 媒体解析
    3. LLM 调用
    4. 后处理校验
    """

    return InterviewFlowService(
        llm_client=get_llm_client(),
        question_bank=get_question_bank(),
        evaluation_store=get_evaluation_store(),
    )
