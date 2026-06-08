"""
这个文件保存旧后端评测结果；它给回归测试和人工排查留出可追踪的记录层。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from typing import List

from sqlalchemy.orm import sessionmaker

from app.models.entities import EvaluationRecord
from app.models.schemas import EvaluationRecordDetail, EvaluationRecordSummary, EvaluationResult


class EvaluationStore:
    """
    负责把测评结果写入数据库，并提供简单查询能力。

    旧后端服务仍承担回归和迁移参考价值，注释用于说明双轨维护期间的兼容原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def save_evaluation(
        self,
        *,
        question_id: str,
        question_type: str,
        source: str,
        source_filename: str | None,
        transcript: str,
        duration_seconds: float | None,
        visual_observation: str | None,
        prompt_text: str,
        llm_provider: str,
        llm_model_name: str,
        raw_llm_content: str,
        raw_llm_payload: dict,
        final_result: EvaluationResult,
    ) -> EvaluationResult:
        """
        写入一条测评记录，并把 record_id / evaluated_at 回填到结果中。

        旧后端服务仍承担回归和迁移参考价值，注释用于说明双轨维护期间的兼容原因。

        @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
        @param question_type: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
        @param source: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param source_filename: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
        @param transcript: 语音转写后的答题文本；评分链路依赖它，但不得把低置信 ASR 当成标准答案。
        @param duration_seconds: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param visual_observation: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param prompt_text: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param llm_provider: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param llm_model_name: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param raw_llm_content: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param raw_llm_payload: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param final_result: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """

        with self.session_factory() as session:
            record = EvaluationRecord(
                question_id=question_id,
                question_type=question_type,
                source=source,
                source_filename=source_filename,
                duration_seconds=duration_seconds,
                total_score=final_result.total_score,
                transcript=transcript,
                visual_observation=visual_observation,
                llm_provider=llm_provider,
                llm_model_name=llm_model_name,
                prompt_text=prompt_text,
                raw_llm_content=raw_llm_content,
                raw_llm_payload=raw_llm_payload,
                final_payload={},
                validation_issue_count=len(final_result.validation_notes),
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            enriched_result = final_result.model_copy(
                update={
                    "record_id": record.id,
                    "evaluated_at": record.created_at,
                }
            )
            record.final_payload = enriched_result.model_dump(mode="json")
            session.commit()
            return enriched_result

    def list_recent_records(self, limit: int = 20) -> List[EvaluationRecordSummary]:
        """
        按时间倒序返回最近测评记录。

        旧后端服务仍承担回归和迁移参考价值，注释用于说明双轨维护期间的兼容原因。

        @param limit: 调用方给定的数量上限；用于控制题库抽样或列表返回的成本。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """

        with self.session_factory() as session:
            records = (
                session.query(EvaluationRecord)
                .order_by(EvaluationRecord.id.desc())
                .limit(limit)
                .all()
            )
            return [
                EvaluationRecordSummary(
                    id=record.id,
                    question_id=record.question_id,
                    question_type=record.question_type,
                    source=record.source,
                    source_filename=record.source_filename,
                    total_score=record.total_score,
                    validation_issue_count=record.validation_issue_count,
                    created_at=record.created_at,
                )
                for record in records
            ]

    def get_record_detail(self, record_id: int) -> EvaluationRecordDetail | None:
        """
        返回单条测评记录详情。

        旧后端服务仍承担回归和迁移参考价值，注释用于说明双轨维护期间的兼容原因。

        @param record_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """

        with self.session_factory() as session:
            record = session.get(EvaluationRecord, record_id)
            if record is None:
                return None

            final_result = EvaluationResult.model_validate(record.final_payload)
            return EvaluationRecordDetail(
                id=record.id,
                question_id=record.question_id,
                question_type=record.question_type,
                source=record.source,
                source_filename=record.source_filename,
                duration_seconds=record.duration_seconds,
                total_score=record.total_score,
                transcript=record.transcript,
                visual_observation=record.visual_observation,
                llm_provider=record.llm_provider,
                llm_model_name=record.llm_model_name,
                prompt_text=record.prompt_text,
                raw_llm_content=record.raw_llm_content,
                raw_llm_payload=record.raw_llm_payload,
                final_result=final_result,
                validation_issue_count=record.validation_issue_count,
                created_at=record.created_at,
            )
