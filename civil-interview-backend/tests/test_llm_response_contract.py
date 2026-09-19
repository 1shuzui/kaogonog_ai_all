"""Cover the production failure: thinking exhausts the budget before JSON output."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core import ai
from app.services.two_stage_scoring import build_evidence_based_scoring_prompt, validate_evidence, validate_scoring_result


def response(content, finish_reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content, reasoning_content="not answer JSON"),
        finish_reason=finish_reason,
    )])


class LlmResponseContractTests(unittest.TestCase):
    def test_deepseek_requests_json_without_thinking_and_recovers_truncation(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            response("", "length"), response(json.dumps({"evidence": {"present": []}})),
        ]
        with patch.object(ai, "get_client", return_value=client), patch.object(
            ai.settings, "llm_provider", "deepseek"
        ), patch.object(ai.time, "sleep"):
            result = ai.call_llm_api("Return JSON evidence", max_tokens=2000)
        first, second = client.chat.completions.create.call_args_list
        self.assertEqual(first.kwargs["extra_body"], {"thinking": {"type": "disabled"}})
        self.assertEqual(first.kwargs["response_format"], {"type": "json_object"})
        self.assertGreater(second.kwargs["max_tokens"], first.kwargs["max_tokens"])
        self.assertIn("evidence", result)

    def test_other_provider_does_not_receive_deepseek_options(self):
        client = Mock()
        client.chat.completions.create.return_value = response('{"ok":true}')
        with patch.object(ai, "get_client", return_value=client), patch.object(ai.settings, "llm_provider", "qwen"):
            self.assertEqual(ai.call_llm_api("Output JSON"), {"ok": True})
        self.assertNotIn("thinking", client.chat.completions.create.call_args.kwargs.get("extra_body", {}))

    def test_malformed_evidence_cannot_crash_or_invent_quotes(self):
        self.assertEqual(validate_evidence(None, "考生答案"), {"present": [], "absent": [], "penalty": [], "bonus": []})
        clean = validate_evidence({"present": [None, "bad", {"quote": "考生答案"}], "penalty": None, "bonus": 1}, "考生答案")
        self.assertEqual(len(clean["present"]), 1)
        self.assertEqual(clean["penalty"], [])

    def test_scoring_prompt_includes_answer_and_reference(self):
        prompt = build_evidence_based_scoring_prompt({}, {"transcript": "已保存的原始回答", "referenceAnswer": "题库参考答案"})
        self.assertIn("已保存的原始回答", prompt)
        self.assertIn("题库参考答案", prompt)

    def test_numeric_strings_are_accepted_and_nonfinite_scores_rejected(self):
        _, _, result = validate_scoring_result({"dimension_scores": {"实务落地": "12", "逻辑结构": "NaN"}}, {}, {"实务落地": 20, "逻辑结构": 15})
        self.assertEqual(result["dimension_scores"], {"实务落地": 12.0})
        self.assertEqual(result["total_score"], 12.0)
