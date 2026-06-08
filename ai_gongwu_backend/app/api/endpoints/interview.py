"""
这个旧后端面试接口文件仍用于回归和迁移对照；它把题目查询、媒体上传和评分入口放在一起，方便比较新旧链路差异。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.dependencies import get_evaluation_store, get_flow_service, get_question_bank
from app.models.schemas import (
    EvaluationAPIResponse,
    EvaluationRecordDetail,
    EvaluationRecordSummary,
    QuestionDetail,
    QuestionSummary,
)
from app.services.evaluation_store import EvaluationStore
from app.services.flow import InterviewFlowService
from app.services.question_bank import QuestionBank, QuestionNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/questions",
    summary="查看当前可用题目列表",
    response_model=list[QuestionSummary],
)
async def list_questions(
    question_bank: QuestionBank = Depends(get_question_bank),
) -> Any:
    """
    返回当前题库中的题目摘要。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param question_bank: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    questions = await run_in_threadpool(question_bank.list_questions)
    return [
        QuestionSummary(
            id=question.id,
            type=question.type,
            province=question.province,
            question=question.question,
            full_score=question.fullScore,
            dimension_count=len(question.dimensions),
            score_band_count=len(question.scoreBands),
            regression_case_count=len(question.regressionCases),
        )
        for question in questions
    ]


@router.get(
    "/questions/{question_id}",
    summary="查看单道题目的完整配置",
    response_model=QuestionDetail,
)
async def get_question_detail(
    question_id: str,
    question_bank: QuestionBank = Depends(get_question_bank),
) -> Any:
    """
    返回单题详情，便于前端或回归工具查看配置。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param question_bank: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """

    try:
        question = await run_in_threadpool(question_bank.get_question, question_id)
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return QuestionDetail(
        id=question.id,
        type=question.type,
        province=question.province,
        full_score=question.fullScore,
        question=question.question,
        dimensions=question.dimensions,
        core_keywords=question.coreKeywords,
        strong_keywords=question.strongKeywords,
        weak_keywords=question.weakKeywords,
        bonus_keywords=question.bonusKeywords,
        penalty_keywords=question.penaltyKeywords,
        scoring_criteria=question.scoringCriteria,
        deduction_rules=question.deductionRules,
        source_document=question.sourceDocument,
        reference_answer=question.referenceAnswer,
        tags=question.tags,
        score_bands=question.scoreBands,
        regression_cases=question.regressionCases,
    )


@router.post(
    "/evaluate",
    summary="多模态面试作答测评接口",
    response_model=EvaluationAPIResponse,
)
async def evaluate_interview_submission(
    question_id: str = Form(..., description="目标测评题目的唯一标识符"),
    media_file: UploadFile = File(..., description="考生作答的音视频文件"),
    flow_service: InterviewFlowService = Depends(get_flow_service),
) -> Any:
    """
    评估音频或视频作答文件。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param media_file: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param flow_service: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException, RuntimeError, ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """

    temp_path = None
    safe_filename = media_file.filename or "unknown"

    try:
        # 第一步：先检查文件后缀是否合法。
        flow_service.validate_media_suffix(safe_filename)

        # 第二步：把上传文件保存到临时文件中。
        # 为什么要落盘？
        # 因为 ffmpeg / Whisper / OpenCV 这类工具通常更适合直接处理本地文件路径。
        file_suffix = Path(safe_filename).suffix.lower()
        fd, temp_path = tempfile.mkstemp(suffix=file_suffix)
        with os.fdopen(fd, "wb") as buffer:
            shutil.copyfileobj(media_file.file, buffer)

        # 第三步：把真正耗时的工作放进线程池，避免阻塞 FastAPI 事件循环。
        result = await run_in_threadpool(
            flow_service.process_and_evaluate,
            question_id,
            temp_path,
            safe_filename,
        )
        return EvaluationAPIResponse(data=result)
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("处理多模态测评请求时发生异常")
        raise HTTPException(status_code=500, detail="服务器内部处理异常。") from exc
    finally:
        # 无论成功还是失败，都尽量清理临时文件，避免垃圾文件越积越多。
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                logger.warning("临时文件清理失败: %s", temp_path)


@router.post(
    "/evaluate/text",
    summary="纯文本面试作答测评接口",
    response_model=EvaluationAPIResponse,
)
async def evaluate_text_submission(
    question_id: str = Form(..., description="目标测评题目的唯一标识符"),
    text_file: UploadFile = File(..., description="考生作答的纯文本文件 (.txt)"),
    flow_service: InterviewFlowService = Depends(get_flow_service),
) -> Any:
    """
    评估纯文本作答。 这个接口是“旁路接口”，优势是： - 不依赖音视频解析 - 便于快速调 Prompt 和评分逻辑 - 便于在弱机器环境做验证

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param text_file: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param flow_service: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException, RuntimeError, ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """

    filename = (text_file.filename or "").lower()
    if not filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="当前接口仅接受 .txt 格式的纯文本文件。")

    try:
        # utf-8-sig 同时兼容普通 UTF-8 和带 BOM 的 UTF-8 文件。
        content_bytes = await text_file.read()
        text_content = content_bytes.decode("utf-8-sig").strip()
        if not text_content:
            raise HTTPException(status_code=400, detail="文本内容为空，无法进行评估。")

        # 评分主逻辑仍然走 service 层，而不是写在路由里。
        result = await run_in_threadpool(
            flow_service.evaluate_text_only,
            question_id,
            text_content,
            text_file.filename,
        )
        return EvaluationAPIResponse(data=result)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文本编码解析失败，请确保文件为 UTF-8 编码。") from exc
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("处理文本测评请求时发生异常")
        raise HTTPException(status_code=500, detail="内部评分引擎异常。") from exc


@router.get(
    "/records",
    summary="查看最近测评记录",
    response_model=list[EvaluationRecordSummary],
)
async def list_evaluation_records(
    limit: int = 20,
    evaluation_store: EvaluationStore = Depends(get_evaluation_store),
) -> Any:
    """
    按时间倒序查看最近测评记录。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param limit: 调用方给定的数量上限；用于控制题库抽样或列表返回的成本。
    @param evaluation_store: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    normalized_limit = max(1, min(limit, 100))
    return await run_in_threadpool(
        evaluation_store.list_recent_records,
        normalized_limit,
    )


@router.get(
    "/records/{record_id}",
    summary="查看单条测评记录详情",
    response_model=EvaluationRecordDetail,
)
async def get_evaluation_record_detail(
    record_id: int,
    evaluation_store: EvaluationStore = Depends(get_evaluation_store),
) -> Any:
    """
    返回单条测评记录的完整详情。

    该公共函数处在模块对外边界，注释记录调用约束，避免调用方依赖内部实现细节。

    @param record_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
    @param evaluation_store: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """

    record = await run_in_threadpool(
        evaluation_store.get_record_detail,
        record_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail=f"测评记录不存在: {record_id}")
    return record
