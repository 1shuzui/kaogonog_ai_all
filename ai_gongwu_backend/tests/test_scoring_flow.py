"""
这个测试文件守住 `test_scoring_flow` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import importlib
import sys
import types
import unittest

from app.models.schemas import EvidenceExtractionPayload, LLMGenerationResult, QuestionDefinition
from app.services.scoring.prompts import (
    build_answer_revision_prompt,
    build_evidence_scoring_prompt,
    build_violation_check_prompt,
)


# 当前测试环境未安装 sqlalchemy，这里在导入 flow 前注入最小桩模块，
# 避免与本轮无关的持久化依赖阻塞流程逻辑测试。
stub_evaluation_store_module = types.ModuleType("app.services.evaluation_store")


class _StubImportedEvaluationStore:
    pass


stub_evaluation_store_module.EvaluationStore = _StubImportedEvaluationStore
_ORIGINAL_EVALUATION_STORE_MODULE = sys.modules.get("app.services.evaluation_store")
sys.modules["app.services.evaluation_store"] = stub_evaluation_store_module

from app.services.flow import InterviewFlowService


class StubQuestionBank:
    """
    最小题库桩，返回固定题目。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def __init__(self, question: QuestionDefinition):
        self.question = question

    def get_question(self, question_id: str) -> QuestionDefinition:
        """
        get_question 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        return self.question


class StubEvaluationStore:
    """
    测试里不落库，只保留接口形状。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def save_evaluation(self, **kwargs):
        """
        save_evaluation 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param **kwargs: 调用方传入的业务上下文；保留原接口形态以兼容现有路由、脚本或测试。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        return kwargs["final_result"]


class StubLLMClient:
    """
    可编排返回结果的大模型桩。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def __init__(self, responses=None, *, enabled: bool = True):
        self.provider = "TEST"
        self.model_name = "stub-model"
        self.client = object() if enabled else None
        self.responses = list(responses or [])
        self.calls: list[dict[str, str]] = []

    def generate(self, prompt: str, system_message: str | None = None):
        """
        generate 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param prompt: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param system_message: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.calls.append(
            {
                "prompt": prompt,
                "system_message": system_message or "",
            }
        )
        if not self.responses:
            return None
        return self.responses.pop(0)


class ScoringFlowViolationTestCase(unittest.TestCase):
    """
    锁住阶段 0 违规检测的关键行为。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def setUp(self):
        """
        setUp 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.question = QuestionDefinition(
            id="AH-TEST-001",
            type="综合分析",
            province="安徽",
            fullScore=10,
            question="请结合实际谈谈你的理解。",
            dimensions=[
                {"name": "现象解读", "score": 5},
                {"name": "对策建议", "score": 5},
            ],
            scoringCriteria=["现象解读（5分）", "对策建议（5分）"],
        )

    def _build_non_violation_response(
        self,
        reason: str = "未发现需要终止评分的明确违规表达",
    ) -> LLMGenerationResult:
        return LLMGenerationResult(
            raw_content=(
                '{"is_violation": false, "category": "", "matched_terms": [], '
                f'"reason": "{reason}"}}'
            ),
            parsed_payload={
                "is_violation": False,
                "category": "",
                "matched_terms": [],
                "reason": reason,
            },
        )

    def _build_violation_response(
        self,
        *,
        category: str,
        matched_terms: list[str],
        reason: str,
    ) -> LLMGenerationResult:
        return LLMGenerationResult(
            raw_content=str(
                {
                    "is_violation": True,
                    "category": category,
                    "matched_terms": matched_terms,
                    "reason": reason,
                }
            ),
            parsed_payload={
                "is_violation": True,
                "category": category,
                "matched_terms": matched_terms,
                "reason": reason,
            },
        )

    def _build_evidence_response(self) -> LLMGenerationResult:
        return LLMGenerationResult(
            raw_content=(
                '{"evidence_items": [{"id": "E1", "dimension_hint": "现象解读", '
                '"claim": "指出资源利用方式可优化", "evidence_text": "要把废物利用变成资源循环", '
                '"evidence_type": "quote", "stance": "positive"}, '
                '{"id": "E2", "dimension_hint": "对策建议", '
                '"claim": "强调要坚持合规底线", "evidence_text": "肯定不能走后门", '
                '"evidence_type": "quote", "stance": "positive"}], '
                '"coverage_notes": ["覆盖问题判断和措施建议"], "summary": "证据完整"}'
            ),
            parsed_payload={
                "evidence_items": [
                    {
                        "id": "E1",
                        "dimension_hint": "现象解读",
                        "claim": "指出资源利用方式可优化",
                        "evidence_text": "要把废物利用变成资源循环",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                    {
                        "id": "E2",
                        "dimension_hint": "对策建议",
                        "claim": "强调要坚持合规底线",
                        "evidence_text": "肯定不能走后门",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                ],
                "coverage_notes": ["覆盖问题判断和措施建议"],
                "summary": "证据完整",
            },
        )

    def _build_scoring_response(self, total_score: float = 6.5) -> LLMGenerationResult:
        return LLMGenerationResult(
            raw_content=(
                '{"dimension_scores": {"现象解读": 3.5, "对策建议": 3.0}, '
                '"deduction_items": [], "bonus_items": [], '
                f'"rationale": "证据支撑较完整。", "total_score": {total_score}}}'
            ),
            parsed_payload={
                "dimension_scores": {
                    "现象解读": 3.5,
                    "对策建议": 3.0,
                },
                "deduction_items": [],
                "bonus_items": [],
                "rationale": "证据支撑较完整。",
                "total_score": total_score,
            },
        )

    def _build_revision_response(
        self,
        suggestion: str = "建议压缩空泛铺垫，先亮明观点，再补一层具体措施和岗位化落点。",
    ) -> LLMGenerationResult:
        return LLMGenerationResult(
            raw_content=f'{{"answer_revision_suggestion": "{suggestion}"}}',
            parsed_payload={"answer_revision_suggestion": suggestion},
        )

    def test_violation_prompt_mentions_context_rules_examples_and_json_contract(self):
        """
        test_violation_prompt_mentions_context_rules_examples_and_json_contract 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        prompt = build_violation_check_prompt(
            self.question,
            "要坚持废物利用，肯定不能走后门。",
        )

        self.assertIn("不能因为单个高风险词面命中就直接判违规", prompt)
        self.assertIn("废物利用", prompt)
        self.assertIn("不能走后门", prompt)
        self.assertIn("这类演讲题不用一开始铺得太满", prompt)
        self.assertIn('"is_violation"', prompt)
        self.assertIn('"matched_terms"', prompt)

    def test_explicit_abuse_is_blocked_by_stage_zero_llm(self):
        """
        test_explicit_abuse_is_blocked_by_stage_zero_llm 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        llm_client = StubLLMClient(
            responses=[
                self._build_violation_response(
                    category="abuse",
                    matched_terms=["你就是个废物"],
                    reason="出现了明确的人身攻击表达。",
                )
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="你就是个废物，根本不配坐在这里。",
            persist=False,
        )

        self.assertTrue(result.violation_detected)
        self.assertEqual(result.total_score, 0.0)
        self.assertEqual(result.violation_category, "abuse")
        self.assertEqual(result.violation_terms, ["你就是个废物"])
        self.assertEqual(len(llm_client.calls), 1)

    def test_explicit_integrity_violation_returns_phrases_and_blocks_following_stages(self):
        """
        test_explicit_integrity_violation_returns_phrases_and_blocks_following_stages 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        llm_client = StubLLMClient(
            responses=[
                self._build_violation_response(
                    category="integrity_red_line",
                    matched_terms=["给领导塞红包更快", "走后门更省事"],
                    reason="存在明确鼓吹行贿受贿和走后门的表达。",
                )
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="我觉得给领导塞红包更快，走后门更省事。",
            persist=False,
        )

        self.assertTrue(result.violation_detected)
        self.assertEqual(result.total_score, 0.0)
        self.assertEqual(result.violation_category, "integrity_red_line")
        self.assertEqual(result.violation_terms, ["给领导塞红包更快", "走后门更省事"])
        self.assertNotIn("红包", result.violation_terms)
        self.assertTrue(any(len(term) > 2 for term in result.violation_terms))
        self.assertEqual(len(llm_client.calls), 1)

    def test_safe_context_terms_do_not_trigger_violation_and_flow_continues(self):
        """
        test_safe_context_terms_do_not_trigger_violation_and_flow_continues 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        llm_client = StubLLMClient(
            responses=[
                self._build_non_violation_response(),
                self._build_evidence_response(),
                self._build_scoring_response(),
                self._build_revision_response(),
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content=(
                "要坚持废物利用，肯定不能走后门。"
                "这类演讲题不用一开始铺得太满，后面把责任和措施补齐就行。"
            ),
            persist=False,
        )

        self.assertFalse(result.violation_detected)
        self.assertGreater(result.total_score, 0.0)
        self.assertEqual(result.violation_terms, [])
        self.assertTrue(result.answer_revision_suggestion)
        self.assertEqual(len(llm_client.calls), 4)

    def test_stage_zero_failure_fails_open_and_continues_to_normal_scoring(self):
        """
        test_stage_zero_failure_fails_open_and_continues_to_normal_scoring 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        llm_client = StubLLMClient(
            responses=[
                None,
                self._build_evidence_response(),
                self._build_scoring_response(),
                self._build_revision_response(),
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="要坚持废物利用，也要讲清楚基本措施。",
            persist=False,
        )

        self.assertFalse(result.violation_detected)
        self.assertGreater(result.total_score, 0.0)
        self.assertEqual(len(llm_client.calls), 4)
        self.assertTrue(
            any("阶段 0 违规检测失败，已放行继续评分。" in note for note in result.validation_notes)
        )

    def test_answer_revision_prompt_contains_scoring_and_speech_rate_context(self):
        """
        test_answer_revision_prompt_contains_scoring_and_speech_rate_context 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        prompt = build_answer_revision_prompt(
            self.question,
            self._mock_final_result_for_prompt(),
        )

        self.assertIn('"speech_rate_level": "偏快"', prompt)
        self.assertIn('"deduction_details"', prompt)
        self.assertIn('"answer_revision_suggestion"', prompt)

    def test_answer_revision_generation_failure_does_not_break_main_flow(self):
        """
        test_answer_revision_generation_failure_does_not_break_main_flow 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        llm_client = StubLLMClient(
            responses=[
                self._build_non_violation_response(),
                self._build_evidence_response(),
                self._build_scoring_response(),
                None,
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="要把废物利用变成资源循环，肯定不能走后门，还要把措施讲得更具体。",
            persist=False,
        )

        self.assertGreater(result.total_score, 0.0)
        self.assertEqual(result.answer_revision_suggestion, "")
        self.assertTrue(any("答案改动建议生成失败，已跳过" in note for note in result.validation_notes))

    def _mock_final_result_for_prompt(self):
        from app.models.schemas import EvaluationResult

        return EvaluationResult(
            question_id=self.question.id,
            question_type=self.question.type,
            transcript="这是一段测试作答文本。",
            source="video",
            source_filename="demo.mp4",
            duration_seconds=30.0,
            dimension_scores={"现象解读": 3.5, "对策建议": 3.0},
            deduction_details=["分析还不够深入"],
            bonus_details=["结构较完整"],
            evidence_quotes=["这是一段测试作答文本"],
            rationale="整体结构尚可，但细节不够具体。",
            total_score=6.5,
            speech_rate_chars_per_minute=360.0,
            speech_rate_level="偏快",
            speech_rate_advice="建议适当放慢语速，给关键词和层次留出停顿，避免信息堆叠过快。",
        )

    def test_interpersonal_scoring_prompt_mentions_basic_pass_guardrail(self):
        """
        test_interpersonal_scoring_prompt_mentions_basic_pass_guardrail 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        interpersonal_question = QuestionDefinition(
            id="AH-TEST-IP-001",
            type="人际沟通",
            province="安徽",
            fullScore=20,
            question="同事因为误会对你有意见，你怎么沟通？",
            dimensions=[
                {"name": "沟通态度", "score": 6},
                {"name": "解释澄清", "score": 7},
                {"name": "后续跟进", "score": 7},
            ],
            scoringCriteria=["沟通态度（6分）", "解释澄清（7分）", "后续跟进（7分）"],
            deductionRules=[],
        )

        prompt = build_evidence_scoring_prompt(
            interpersonal_question,
            EvidenceExtractionPayload(),
        )

        self.assertIn("人际题额外判档提醒", prompt)
        self.assertIn("态度得体", prompt)
        self.assertIn("基本合格", prompt)
        self.assertIn("不是直接打成 0 分", prompt)


if __name__ == "__main__":
    unittest.main()

if _ORIGINAL_EVALUATION_STORE_MODULE is not None:
    sys.modules["app.services.evaluation_store"] = _ORIGINAL_EVALUATION_STORE_MODULE
else:
    sys.modules.pop("app.services.evaluation_store", None)
importlib.invalidate_caches()
