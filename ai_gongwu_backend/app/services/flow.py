"""业务编排服务。

如果把整个后端想象成一条流水线，这个文件就是“总调度台”。
它不关心 HTTP 细节，也不直接处理数据库，而是专门负责串联核心步骤：

1. 找到题目
2. 解析文本 / 音频 / 视频
3. 生成 Prompt 调模型
4. 对模型结果做后处理和校验

这层设计的好处是：API 层保持轻，业务逻辑更集中，也更容易测试。
"""

import json
import logging
import re
from pathlib import Path

from app.core.config import settings
from app.models.schemas import (
    EvaluationResult,
    MediaExtractionResult,
    ViolationCheckPayload,
)
from app.services.evaluation_store import EvaluationStore
from app.services.llm.client import LLMClient
from app.services.media.video_processor import process_audio, process_video
from app.services.question_bank import QuestionBank
from app.services.scoring.calculator import (
    apply_post_processing,
    build_deterministic_stage_two_payload,
    prepare_evidence_packet,
)
from app.services.scoring.prompts import (
    VIOLATION_CHECK_SYSTEM_MESSAGE,
    EVIDENCE_EXTRACTION_SYSTEM_MESSAGE,
    EVIDENCE_SCORING_SYSTEM_MESSAGE,
    build_violation_check_prompt,
    build_evidence_extraction_prompt,
    build_evidence_scoring_prompt,
)

logger = logging.getLogger(__name__)

RULE_BASED_VIOLATION_PATTERNS = {
    "abuse": (
        re.compile(r"傻[逼比bB]"),
        re.compile(r"煞笔|沙比"),
        re.compile(r"脑残|智障"),
        re.compile(r"王八蛋"),
        re.compile(r"狗东西"),
        re.compile(r"去死"),
        re.compile(r"[操草]你"),
        re.compile(r"他妈的|你妈的|妈的"),
        re.compile(r"滚蛋"),
        re.compile(r"废物"),
        re.compile(r"畜生"),
        re.compile(r"贱人"),
    ),
}


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """去重但保留原始顺序。"""

    values: list[str] = []
    seen = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return values


def _detect_rule_based_violation(text: str) -> ViolationCheckPayload | None:
    """先用本地规则拦截最明显的辱骂脏词，避免继续评分。"""

    matched_terms: list[str] = []
    matched_category = ""
    for category, patterns in RULE_BASED_VIOLATION_PATTERNS.items():
        for pattern in patterns:
            matched_terms.extend(match.group(0) for match in pattern.finditer(text))
        if matched_terms:
            matched_category = category
            break

    cleaned_terms = _dedupe_preserve_order(matched_terms)
    if not cleaned_terms:
        return None

    return ViolationCheckPayload(
        is_violation=True,
        category=matched_category,
        matched_terms=cleaned_terms[:5],
        reason="检测到明显辱骂/攻击性违规词，已终止评分。",
    )


def _normalize_violation_payload(raw_payload: dict | None) -> ViolationCheckPayload:
    """把模型返回的违规检测结果整理成稳定结构。"""

    try:
        payload = ViolationCheckPayload.model_validate(raw_payload or {})
    except Exception:
        return ViolationCheckPayload()

    return payload.model_copy(
        update={
            "category": str(payload.category or "").strip(),
            "matched_terms": _dedupe_preserve_order(list(payload.matched_terms or []))[:5],
            "reason": str(payload.reason or "").strip(),
        }
    )


class InterviewFlowService:
    """统筹媒体解析、模型评分和确定性校验的核心服务。"""

    def __init__(
        self,
        llm_client: LLMClient,
        question_bank: QuestionBank,
        evaluation_store: EvaluationStore,
    ):
        self.llm_client = llm_client
        self.question_bank = question_bank
        self.evaluation_store = evaluation_store

    def validate_media_suffix(self, filename: str) -> None:
        """检查上传文件后缀是否在支持列表中。"""

        suffix = Path(filename).suffix.lower()
        supported_extensions = (
            set(settings.SUPPORTED_VIDEO_EXTENSIONS)
            | set(settings.SUPPORTED_AUDIO_EXTENSIONS)
        )
        if suffix not in supported_extensions:
            supported = ", ".join(sorted(supported_extensions))
            raise ValueError(f"不支持的媒体格式: {suffix or '无后缀'}。支持格式: {supported}")

    def _build_violation_blocked_result(
        self,
        *,
        question,
        extraction_result: MediaExtractionResult,
        violation_payload: ViolationCheckPayload,
        detection_note: str,
    ) -> EvaluationResult:
        """构造“命中违规，直接终止评分”的统一结果。"""

        matched_terms = _dedupe_preserve_order(list(violation_payload.matched_terms or []))
        base_reason = (
            violation_payload.reason.strip()
            if violation_payload.reason.strip()
            else "检测到违规词/红线表达，已终止评分。"
        )
        reason = (
            base_reason
            if "已终止评分" in base_reason
            else f"{base_reason.rstrip('。')}，已终止评分。"
        )
        validation_notes = [detection_note]
        if matched_terms:
            validation_notes.append(f"命中的违规词/表达：{'、'.join(matched_terms)}")

        return EvaluationResult(
            question_id=question.id,
            question_type=question.type,
            transcript=extraction_result.transcript,
            source=extraction_result.source,
            source_filename=extraction_result.source_filename,
            visual_observation=extraction_result.visual_observation,
            rationale=reason,
            total_score=0.0,
            violation_detected=True,
            violation_category=violation_payload.category,
            violation_reason=reason,
            violation_terms=matched_terms,
            validation_notes=validation_notes,
        )

    def _extract_from_media(self, file_path: str) -> MediaExtractionResult:
        """根据文件后缀选择合适的解析路径。

        视频走：提取音频 + ASR + 视觉分析
        音频走：直接 ASR
        """
        suffix = Path(file_path).suffix.lower()
        if suffix in settings.SUPPORTED_VIDEO_EXTENSIONS:
            return process_video(file_path)
        if suffix in settings.SUPPORTED_AUDIO_EXTENSIONS:
            return process_audio(file_path)
        raise ValueError(f"不支持的媒体格式: {suffix or '无后缀'}")

    def _execute_evaluation_core(
        self,
        question_id: str,
        extraction_result: MediaExtractionResult,
        *,
        persist: bool = True,
    ) -> EvaluationResult:
        """执行评分主流程。

        这里是整个系统最核心的“内容评分链路”：
        1. 根据题目 ID 拿到题目定义
        2. 第一阶段抽取证据
        3. 第二阶段仅基于证据评分
        4. 用确定性规则修正和校验模型输出
        """

        question = self.question_bank.get_question(question_id)
        violation_prompt = ""
        violation_raw_content = ""
        violation_raw_payload: dict = {}
        violation_result_payload: dict = {}
        stage_zero_notes: list[str] = []

        if self.llm_client.client is not None:
            violation_prompt = build_violation_check_prompt(
                question=question,
                answer_text=extraction_result.transcript,
                visual_observation=extraction_result.visual_observation,
            )
            violation_generation = self.llm_client.generate(
                violation_prompt,
                system_message=VIOLATION_CHECK_SYSTEM_MESSAGE,
            )
            if violation_generation is not None:
                violation_raw_content = violation_generation.raw_content
                violation_raw_payload = violation_generation.parsed_payload
                violation_payload = _normalize_violation_payload(violation_generation.parsed_payload)
                violation_result_payload = violation_payload.model_dump(mode="json")
                if violation_payload.is_violation:
                    final_result = self._build_violation_blocked_result(
                        question=question,
                        extraction_result=extraction_result,
                        violation_payload=violation_payload,
                        detection_note="阶段 0 模型检测命中违规表达，已终止评分。",
                    )
                    if not persist:
                        return final_result

                    return self.evaluation_store.save_evaluation(
                        question_id=question.id,
                        question_type=question.type,
                        source=extraction_result.source,
                        source_filename=extraction_result.source_filename,
                        transcript=extraction_result.transcript,
                        visual_observation=extraction_result.visual_observation,
                        prompt_text=json.dumps(
                            {
                                "stage_zero_prompt": violation_prompt,
                                "stage_zero_blocked": True,
                            },
                            ensure_ascii=False,
                        ),
                        llm_provider=self.llm_client.provider,
                        llm_model_name=self.llm_client.model_name,
                        raw_llm_content=json.dumps(
                            {
                                "stage_zero_raw": violation_raw_content,
                            },
                            ensure_ascii=False,
                        ),
                        raw_llm_payload={
                            "stage_zero": violation_result_payload,
                            "stage_zero_raw": violation_raw_payload,
                            "stage_zero_blocked": True,
                        },
                        final_result=final_result,
                    )
            else:
                logger.warning("阶段 0 违规检测失败，当前请求已按 fail-open 策略继续评分。")
                stage_zero_notes.append("阶段 0 违规检测失败，已放行继续评分。")
                violation_result_payload = {
                    "is_violation": False,
                    "category": "",
                    "matched_terms": [],
                    "reason": "",
                    "status": "failed_open",
                    "error": "llm_generation_failed",
                }
                violation_raw_payload = dict(violation_result_payload)
        else:
            violation_result_payload = {
                "status": "skipped",
                "reason": "llm_unavailable",
            }

        if self.llm_client.client is None:
            logger.info("LLM 未初始化，当前题目将回退到确定性证据评分。question_id=%s", question_id)
            return self._execute_deterministic_fallback(
                question_id=question_id,
                question=question,
                extraction_result=extraction_result,
                persist=persist,
                fallback_reason="LLM 客户端未初始化，已回退到确定性证据评分。",
                violation_prompt=violation_prompt,
                violation_raw_content=violation_raw_content,
                violation_result_payload=violation_result_payload,
                violation_raw_payload=violation_raw_payload,
                violation_notes=stage_zero_notes,
            )

        evidence_prompt = build_evidence_extraction_prompt(
            question=question,
            answer_text=extraction_result.transcript,
            visual_observation=extraction_result.visual_observation,
        )
        evidence_generation = self.llm_client.generate(
            evidence_prompt,
            system_message=EVIDENCE_EXTRACTION_SYSTEM_MESSAGE,
        )
        if evidence_generation is None:
            logger.warning("第一阶段证据抽取失败，已回退到规则型证据整理。")
            evidence_packet, evidence_notes = prepare_evidence_packet(
                raw_llm_result={},
                transcript=extraction_result.transcript,
                question=question,
            )
            evidence_notes = [*stage_zero_notes, *evidence_notes]
            evidence_notes.insert(0, "第一阶段证据抽取失败，已回退到规则型证据整理。")
            evidence_raw_content = ""
            evidence_raw_payload = {}
        else:
            evidence_packet, evidence_notes = prepare_evidence_packet(
                raw_llm_result=evidence_generation.parsed_payload,
                transcript=extraction_result.transcript,
                question=question,
            )
            evidence_notes = [*stage_zero_notes, *evidence_notes]
            evidence_raw_content = evidence_generation.raw_content
            evidence_raw_payload = evidence_generation.parsed_payload

        scoring_prompt = build_evidence_scoring_prompt(
            question=question,
            evidence_packet=evidence_packet,
        )
        scoring_generation = self.llm_client.generate(
            scoring_prompt,
            system_message=EVIDENCE_SCORING_SYSTEM_MESSAGE,
        )
        if scoring_generation is None:
            logger.warning("第二阶段证据评分失败，已回退到确定性证据评分。question_id=%s", question_id)
            return self._execute_deterministic_fallback(
                question_id=question_id,
                question=question,
                extraction_result=extraction_result,
                persist=persist,
                evidence_packet=evidence_packet,
                evidence_notes=evidence_notes,
                fallback_reason="第二阶段证据评分失败，已回退到确定性证据评分。",
                evidence_prompt=evidence_prompt,
                scoring_prompt=scoring_prompt,
                evidence_raw_content=evidence_raw_content,
                evidence_raw_payload=evidence_raw_payload,
                violation_prompt=violation_prompt,
                violation_raw_content=violation_raw_content,
                violation_result_payload=violation_result_payload,
                violation_raw_payload=violation_raw_payload,
                violation_notes=stage_zero_notes,
            )

        final_result = apply_post_processing(
            raw_llm_result=scoring_generation.parsed_payload,
            transcript=extraction_result.transcript,
            question=question,
            evidence_packet=evidence_packet,
            visual_observation=extraction_result.visual_observation,
            extra_validation_notes=evidence_notes,
        )
        final_result = final_result.model_copy(
            update={
                "source": extraction_result.source,
                "source_filename": extraction_result.source_filename,
            }
        )

        if not persist:
            return final_result

        return self.evaluation_store.save_evaluation(
            question_id=question.id,
            question_type=question.type,
            source=extraction_result.source,
            source_filename=extraction_result.source_filename,
            transcript=extraction_result.transcript,
            visual_observation=extraction_result.visual_observation,
            prompt_text=json.dumps(
                {
                    "stage_zero_prompt": violation_prompt,
                    "stage_one_prompt": evidence_prompt,
                    "stage_two_prompt": scoring_prompt,
                },
                ensure_ascii=False,
            ),
            llm_provider=self.llm_client.provider,
            llm_model_name=self.llm_client.model_name,
            raw_llm_content=json.dumps(
                {
                    "stage_zero_raw": violation_raw_content,
                    "stage_one_raw": evidence_raw_content,
                    "stage_two_raw": scoring_generation.raw_content,
                },
                ensure_ascii=False,
            ),
            raw_llm_payload={
                "stage_zero": violation_result_payload,
                "stage_zero_raw": violation_raw_payload,
                "stage_one": evidence_raw_payload,
                "validated_evidence": evidence_packet.model_dump(mode="json"),
                "stage_two": scoring_generation.parsed_payload,
            },
            final_result=final_result,
        )

    def _execute_deterministic_fallback(
        self,
        *,
        question_id: str,
        question,
        extraction_result: MediaExtractionResult,
        persist: bool,
        fallback_reason: str,
        evidence_packet=None,
        evidence_notes: list[str] | None = None,
        evidence_prompt: str = "",
        scoring_prompt: str = "",
        evidence_raw_content: str = "",
        evidence_raw_payload: dict | None = None,
        violation_prompt: str = "",
        violation_raw_content: str = "",
        violation_result_payload: dict | None = None,
        violation_raw_payload: dict | None = None,
        violation_notes: list[str] | None = None,
    ) -> EvaluationResult:
        """无模型或模型失败时的确定性评分兜底。"""

        if evidence_packet is None:
            evidence_packet, evidence_notes = prepare_evidence_packet(
                raw_llm_result={},
                transcript=extraction_result.transcript,
                question=question,
            )
        evidence_notes = [*(violation_notes or []), *(evidence_notes or [])]
        evidence_notes.insert(0, fallback_reason)

        deterministic_payload = build_deterministic_stage_two_payload(
            transcript=extraction_result.transcript,
            question=question,
            evidence_packet=evidence_packet,
        )
        final_result = apply_post_processing(
            raw_llm_result=deterministic_payload,
            transcript=extraction_result.transcript,
            question=question,
            evidence_packet=evidence_packet,
            visual_observation=extraction_result.visual_observation,
            extra_validation_notes=evidence_notes,
        )
        final_result = final_result.model_copy(
            update={
                "source": extraction_result.source,
                "source_filename": extraction_result.source_filename,
            }
        )

        if not persist:
            return final_result

        return self.evaluation_store.save_evaluation(
            question_id=question.id,
            question_type=question.type,
            source=extraction_result.source,
            source_filename=extraction_result.source_filename,
            transcript=extraction_result.transcript,
            visual_observation=extraction_result.visual_observation,
            prompt_text=json.dumps(
                {
                    "stage_zero_prompt": violation_prompt,
                    "stage_one_prompt": evidence_prompt,
                    "stage_two_prompt": scoring_prompt,
                    "deterministic_fallback": True,
                },
                ensure_ascii=False,
            ),
            llm_provider=self.llm_client.provider,
            llm_model_name=self.llm_client.model_name,
            raw_llm_content=json.dumps(
                {
                    "stage_zero_raw": violation_raw_content,
                    "stage_one_raw": evidence_raw_content,
                    "stage_two_raw": "",
                    "deterministic_stage_two": deterministic_payload,
                },
                ensure_ascii=False,
            ),
            raw_llm_payload={
                "stage_zero": violation_result_payload or {},
                "stage_zero_raw": violation_raw_payload or {},
                "stage_one": evidence_raw_payload or {},
                "validated_evidence": evidence_packet.model_dump(mode="json"),
                "stage_two": deterministic_payload,
                "deterministic_fallback": True,
            },
            final_result=final_result,
        )

    def process_and_evaluate(
        self,
        question_id: str,
        file_path: str,
        source_filename: str | None = None,
        *,
        persist: bool = True,
    ) -> EvaluationResult:
        """处理音频/视频类提交。"""

        # 先把媒体转成统一结构。
        extraction_result = self._extract_from_media(file_path).model_copy(
            update={"source_filename": source_filename}
        )
        if not extraction_result.transcript.strip():
            raise ValueError("未能从媒体文件中提取到有效语音内容。")
        return self._execute_evaluation_core(
            question_id,
            extraction_result,
            persist=persist,
        )

    def evaluate_text_only(
        self,
        question_id: str,
        text_content: str,
        source_filename: str | None = None,
        *,
        persist: bool = True,
    ) -> EvaluationResult:
        """处理纯文本提交通道。

        这个接口很适合：
        - 快速调试评分逻辑
        - 对比不同 Prompt 效果
        - 不依赖 Whisper / ffmpeg 的轻量测试
        """

        logger.info("启动纯文本测评旁路, question_id=%s, 文本长度=%s", question_id, len(text_content))
        if not text_content.strip():
            raise ValueError("文本内容为空，无法进行评估。")

        return self._execute_evaluation_core(
            question_id=question_id,
            extraction_result=MediaExtractionResult(
                transcript=text_content.strip(),
                source="text",
                source_filename=source_filename,
                visual_observation=None,
            ),
            persist=persist,
        )
