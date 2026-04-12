"""测评结果持久化服务。"""

from typing import List

from sqlalchemy.orm import sessionmaker

from app.models.entities import EvaluationRecord
from app.models.schemas import EvaluationRecordDetail, EvaluationRecordSummary, EvaluationResult


class EvaluationStore:
    """负责把测评结果写入数据库，并提供简单查询能力。"""

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
        visual_observation: str | None,
        prompt_text: str,
        llm_provider: str,
        llm_model_name: str,
        raw_llm_content: str,
        raw_llm_payload: dict,
        final_result: EvaluationResult,
    ) -> EvaluationResult:
        """写入一条测评记录，并把 record_id / evaluated_at 回填到结果中。"""

        with self.session_factory() as session:
            record = EvaluationRecord(
                question_id=question_id,
                question_type=question_type,
                source=source,
                source_filename=source_filename,
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
        """按时间倒序返回最近测评记录。"""

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
        """返回单条测评记录详情。"""

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
