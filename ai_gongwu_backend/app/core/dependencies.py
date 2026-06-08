"""
这个文件集中创建 FastAPI 依赖对象；题库、评分流和存储服务通过这里注入，便于测试替换。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    """
    返回全局共享的 LLM 客户端实例。 为什么要缓存？ - 避免每个请求都重新初始化一次客户端 - 结构更清晰，后续如果要加监控、埋点、限流，也更好统一管理

    旧后端核心模块支撑配置和数据库连接，注释用于标明与主后端并存的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    return LLMClient()


@lru_cache()
def get_question_bank() -> QuestionBank:
    """
    返回加载到内存中的题库对象。 题库 JSON 不需要每次请求都重新读文件， 缓存在内存里能减少磁盘 IO，提高响应速度。

    旧后端核心模块支撑配置和数据库连接，注释用于标明与主后端并存的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    return QuestionBank(settings.QUESTION_DB_PATH)


@lru_cache()
def get_evaluation_store() -> EvaluationStore:
    """
    返回测评结果持久化服务。

    旧后端核心模块支撑配置和数据库连接，注释用于标明与主后端并存的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    return EvaluationStore(session_factory=SessionLocal)


@lru_cache()
def get_flow_service() -> InterviewFlowService:
    """
    返回业务编排服务。 这个服务会串起： 1. 题库读取 2. 媒体解析 3. LLM 调用 4. 后处理校验

    旧后端核心模块支撑配置和数据库连接，注释用于标明与主后端并存的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    return InterviewFlowService(
        llm_client=get_llm_client(),
        question_bank=get_question_bank(),
        evaluation_store=get_evaluation_store(),
    )
