"""湖南题库导入脚本关键回归测试。"""

import json
import re
import unittest
from pathlib import Path

from scripts.import_hunan_question_bank import (
    build_dimensions,
    build_reference_samples,
    build_tags,
    detect_template_family,
    infer_target_group,
    parse_scored_items,
    resolve_full_score,
)


class ImportHunanQuestionBankTestCase(unittest.TestCase):
    """锁住导入解析、字段清洗和模板生成里最容易回退的点。"""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        base_dir = Path(__file__).resolve().parents[1] / "assets" / "questions" / "generated_hunan"
        cls.analysis_question = json.loads((base_dir / "HN-20200816-01.json").read_text(encoding="utf-8"))
        cls.organization_question = json.loads((base_dir / "HN-20200816-02.json").read_text(encoding="utf-8"))
        cls.organization_slogan_question = json.loads((base_dir / "HN-20200919-03.json").read_text(encoding="utf-8"))
        cls.interpersonal_question = json.loads((base_dir / "HN-20200919-JY-02.json").read_text(encoding="utf-8"))
        cls.mixed_scene_question = json.loads((base_dir / "HN-20200919-JY-03.json").read_text(encoding="utf-8"))
        cls.scene_question = json.loads((base_dir / "HN-20200920-XZ-03.json").read_text(encoding="utf-8"))
        cls.word_scene_question = json.loads((base_dir / "HN-20200920-01.json").read_text(encoding="utf-8"))
        cls.speech_scene_question = json.loads((base_dir / "HN-20200921-XZ-03.json").read_text(encoding="utf-8"))
        cls.clean_type_question_1 = json.loads((base_dir / "HN-20200920-XZ-01.json").read_text(encoding="utf-8"))
        cls.clean_type_question_2 = json.loads((base_dir / "HN-20200920-XZ-03.json").read_text(encoding="utf-8"))
        cls.dimension_question_1 = json.loads((base_dir / "HN-20200816-02.json").read_text(encoding="utf-8"))
        cls.dimension_question_2 = json.loads((base_dir / "CS-20201212-01.json").read_text(encoding="utf-8"))
        cls.dirty_tags_question = json.loads((base_dir / "HN-20200816-03.json").read_text(encoding="utf-8"))
        cls.full_score_conflict_question_1 = json.loads((base_dir / "HN-20200919-03.json").read_text(encoding="utf-8"))
        cls.full_score_conflict_question_2 = json.loads((base_dir / "HN-20200920-JY-03.json").read_text(encoding="utf-8"))

    def assert_dimension_names_clean(self, question: dict) -> None:
        for dimension in question["dimensions"]:
            name = dimension["name"]
            self.assertFalse(name.startswith("："), name)
            self.assertIsNone(re.search(r"\d+$", name), name)

    def test_parse_scored_items_keeps_titled_items_grouped(self):
        section_text = (
            "政治站位（12分）：深刻把握政策方向；"
            "内涵解读（10分）：准确阐释核心要求；"
            "结合实际（9分）：紧扣长沙发展实际。"
        )
        items = parse_scored_items(section_text)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], "政治站位（12分）：深刻把握政策方向")
        self.assertTrue(items[1].startswith("内涵解读（10分）："))
        self.assertIn("结合实际（9分）：", items[2])

    def test_build_dimensions_uses_bracket_suffix_for_true_duplicates(self):
        criteria = [
            "语言表达（4分）：庄重规范、表达流畅。",
            "语言表达（3分）：自然清楚、便于理解。",
        ]
        dimensions = build_dimensions(criteria)
        names = [item["name"] for item in dimensions]
        self.assertEqual(len(names), 2)
        for name in names:
            self.assertTrue(name.startswith("语言表达（"), name)
            self.assertTrue(name.endswith("）"), name)
            self.assertIsNone(re.search(r"\d+$", name), name)

    def test_build_tags_strips_meta_noise(self):
        tags = build_tags("乡镇岗 现场模拟 餐饮经营 题库说明 适配场景：湖南省考乡镇岗")
        self.assertEqual(tags, ["乡镇岗", "现场模拟", "餐饮经营"])

    def test_build_tags_filters_word_noise_and_rebuilds_from_context(self):
        tags = build_tags(
            "MERGEFORMAT SimSun GB2312",
            question_type="人际沟通·工作协调+责任担当类（适配湖南省税务系统补录岗位）",
            keyword_groups=[["工作协调", "责任担当"], ["税务岗位"]],
        )
        self.assertTrue(tags)
        self.assertNotIn("MERGEFORMAT", tags)
        self.assertIn("人际沟通", tags)

    def test_resolve_full_score_prefers_question_and_scoring_consensus_over_dirty_ai_value(self):
        dimensions = build_dimensions(
            [
                "语言表达（9分）：贴合家庭沟通场景。",
                "安全回应（7分）：回应父母顾虑。",
                "职业价值（5分）：说明岗位意义。",
                "沟通逻辑（5分）：层次清楚。",
                "创新思维（4分）：有具体安抚举措。",
            ]
        )
        score = resolve_full_score(
            question_text="请现场模拟如何说服父母。（30分）",
            header_description="现场模拟+亲情沟通+职业认知，赋分30分",
            scoring_section_text="语言表达（9分）……创新思维（4分）……总分30分。",
            ai_text="适用省份：湖南；满分：35分；本题得分 = 得分标准得分（30分）；",
            dimensions=dimensions,
        )
        self.assertEqual(score, 30.0)

    def test_detect_template_family_prefers_interpersonal_for_non_scene_persuasion(self):
        self.assertEqual(detect_template_family(self.interpersonal_question), "interpersonal")

    def test_detect_template_family_prefers_scene_for_explicit_scene_prompt(self):
        self.assertEqual(detect_template_family(self.mixed_scene_question), "scene")

    def test_detect_template_family_prefers_scene_for_speech_prompt(self):
        self.assertEqual(detect_template_family(self.speech_scene_question), "scene")

    def test_infer_target_group_prefers_operator_over_role_tags(self):
        self.assertEqual(infer_target_group(self.scene_question), "餐饮经营者")

    def test_dirty_type_fields_are_cleaned_in_generated_questions(self):
        forbidden = ("组合1：", "选择理由：", "核心沟通逻辑", "题库说明")
        for question in (self.clean_type_question_1, self.clean_type_question_2):
            self.assertNotIn("\n", question["type"])
            for marker in forbidden:
                self.assertNotIn(marker, question["type"])

    def test_generated_dimensions_are_cleaned(self):
        for question in (
            self.analysis_question,
            self.organization_question,
            self.dimension_question_2,
            self.word_scene_question,
        ):
            self.assert_dimension_names_clean(question)

    def test_generated_tags_no_longer_contain_meta_fragments(self):
        forbidden = ("题库说明", "适配场景", "AI智能评分", "核心特色", "使用规范", "结构化数据", "支持自动核算总分")
        for tag in self.scene_question["tags"]:
            for marker in forbidden:
                self.assertNotIn(marker, tag)

    def test_generated_dirty_tags_are_pruned(self):
        self.assertLessEqual(len(self.dirty_tags_question["tags"]), 8)
        forbidden = ("MERGEFORMAT", "SimSun", "GB2312", "Version", "Regular")
        for tag in self.dirty_tags_question["tags"]:
            for marker in forbidden:
                self.assertNotIn(marker, tag)

    def test_empty_generated_tags_are_rebuilt_from_type_and_keywords(self):
        for question in (self.interpersonal_question, self.mixed_scene_question):
            self.assertTrue(question["tags"])
            self.assertLessEqual(len(question["tags"]), 8)

    def test_generated_full_score_prefers_real_question_score_when_ai_metadata_conflicts(self):
        for question in (self.full_score_conflict_question_1, self.full_score_conflict_question_2):
            self.assertEqual(question["fullScore"], 30.0)
            self.assertAlmostEqual(
                sum(dimension["score"] for dimension in question["dimensions"]),
                question["fullScore"],
                places=1,
            )

    def test_interpersonal_low_sample_is_no_longer_scene_like_empty_talk(self):
        samples, _ = build_reference_samples(self.interpersonal_question)
        self.assertTrue(samples["low"].strategy.startswith("template_interpersonal_low"))
        self.assertNotIn("各位相关对象", samples["low"].text)
        self.assertTrue(any(marker in samples["low"].text for marker in ("继续", "听", "解释", "沟通")))

    def test_analysis_mid_sample_keeps_role_context(self):
        samples, _ = build_reference_samples(self.analysis_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_analysis_mid"))
        self.assertTrue(any(marker in samples["mid"].text for marker in ("税务", "税务工作", "岗位")))

    def test_organization_mid_sample_for_slogan_question_keeps_theme_line(self):
        samples, _ = build_reference_samples(self.organization_slogan_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_organization_mid"))
        self.assertIn("“", samples["mid"].text)
        self.assertTrue(any(marker in samples["mid"].text for marker in ("宣传口径", "主题句", "宣传语")))
        self.assertTrue(any(marker in samples["mid"].text for marker in ("立意", "出发点", "以学促干", "岗位赋能")))

    def test_scene_mid_sample_keeps_business_context(self):
        samples, _ = build_reference_samples(self.scene_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_scene_mid"))
        self.assertIn("餐饮经营者", samples["mid"].text)
        self.assertNotIn("基层干部", samples["mid"].text)

    def test_explicit_scene_prompt_uses_scene_template(self):
        samples, _ = build_reference_samples(self.mixed_scene_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_scene_mid"))
        self.assertIn("社区居民", samples["mid"].text)
        self.assertTrue(any(marker in samples["mid"].text for marker in ("各位", "大家好", "宣讲")))

    def test_scene_word_expression_sample_is_not_generic_greeting(self):
        samples, _ = build_reference_samples(self.word_scene_question)
        self.assertTrue(samples["mid"].strategy.startswith("template_scene_mid"))
        self.assertFalse(samples["mid"].text.startswith("各位"))
        self.assertNotIn("大家好", samples["mid"].text[:20])
        self.assertTrue(any(marker in samples["mid"].text for marker in ("词语", "主题", "价值导向", "岗位")))

    def test_scene_word_expression_low_sample_mentions_prompt_terms_without_repeat_loop(self):
        samples, _ = build_reference_samples(self.word_scene_question)
        self.assertTrue(samples["low"].strategy.startswith("template_scene_low"))
        self.assertTrue(any(marker in samples["low"].text for marker in ("青年", "奋斗", "幸福", "担当", "时代", "理想", "人生")))
        self.assertLessEqual(samples["low"].text.count("这类表达题关键还是要"), 1)

    def test_scene_speech_low_sample_has_no_placeholder_topic(self):
        samples, _ = build_reference_samples(self.speech_scene_question)
        self.assertTrue(samples["low"].strategy.startswith("template_scene_low"))
        self.assertNotIn("相关内容相关内容", samples["low"].text)
        self.assertIn("各位考官", samples["low"].text)


if __name__ == "__main__":
    unittest.main()
