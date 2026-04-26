"""湖南题库导入脚本的关键回归测试。"""

import json
import unittest
from pathlib import Path

from scripts.import_hunan_question_bank import (
    build_reference_samples,
    detect_template_family,
    infer_target_group,
)


class ImportHunanQuestionBankTestCase(unittest.TestCase):
    """锁住题型识别和模板生成里最容易回退的点。"""

    @classmethod
    def setUpClass(cls):
        base_dir = Path(__file__).resolve().parents[1] / "assets" / "questions" / "generated_hunan"
        cls.interpersonal_question = json.loads(
            (base_dir / "HN-20200919-JY-02.json").read_text(encoding="utf-8")
        )
        cls.scene_question = json.loads(
            (base_dir / "HN-20200920-XZ-03.json").read_text(encoding="utf-8")
        )

    def test_detect_template_family_prefers_interpersonal_for_non_scene_persuasion(self):
        # “劝说”本身不等于现场模拟；题目未要求现场表达时，应走人际沟通模板。
        self.assertEqual(detect_template_family(self.interpersonal_question), "interpersonal")

    def test_infer_target_group_prefers_operator_over_role_tags(self):
        # 题干真实沟通对象是餐饮经营者，不能被“乡镇岗/街道干部”这类角色词覆盖。
        self.assertEqual(infer_target_group(self.scene_question), "餐饮经营者")

    def test_interpersonal_low_sample_is_no_longer_scene_like_empty_talk(self):
        # 低档样本可以弱，但不能退化成“各位……大家好”的现场发言空壳。
        samples, _ = build_reference_samples(self.interpersonal_question)
        self.assertTrue(samples["low"].strategy.startswith("template_interpersonal_low"))
        self.assertNotIn("各位相关对象", samples["low"].text)
        self.assertTrue(any(marker in samples["low"].text for marker in ("继续", "听", "解释", "沟通")))

    def test_scene_mid_sample_keeps_business_context(self):
        # 现场模拟题的中档样本要保留沟通对象和基本顾虑，不能泛化成“基层干部宣讲稿”。
        samples, _ = build_reference_samples(self.scene_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_scene_mid"))
        self.assertIn("餐饮经营者", samples["mid"].text)
        self.assertNotIn("基层干部", samples["mid"].text)


if __name__ == "__main__":
    unittest.main()
