"""通用题库导入脚本回归测试。"""

import unittest
from pathlib import Path

from scripts.extract_docx_text import extract_docx_text
from scripts.import_question_bank import (
    activate_profile,
    build_runtime_profile,
    build_interpersonal_template_texts,
    detect_template_family,
    extract_sections,
    normalize_question_id,
    normalize_source_text,
)


class ExtractDocxTextTestCase(unittest.TestCase):
    """锁住 .docx 提取脚本的输出格式。"""

    def test_extract_docx_text_matches_existing_hunan_fixture(self):
        repo_root = Path(__file__).resolve().parents[2]
        docx_path = repo_root / "湖南-2020-通用岗.docx"
        extracted_path = repo_root / "湖南-2020-通用岗.extracted.txt"

        self.assertEqual(
            extract_docx_text(docx_path),
            extracted_path.read_text(encoding="utf-8"),
        )


class ImportQuestionBankNormalizationTestCase(unittest.TestCase):
    """锁住安徽兼容化归一规则。"""

    maxDiff = None

    def test_normalize_question_id_supports_anhui_variants(self):
        self.assertEqual(normalize_question_id("AHGWY 20201113PM 01"), "AHGWY-20201113PM-01")
        self.assertEqual(normalize_question_id("AHGWY20201114_01"), "AHGWY-20201114-01")
        self.assertEqual(normalize_question_id("AHGX20201226_01"), "AHGX-20201226-01")

    def test_normalize_source_text_repairs_inline_headers_and_chinese_section_labels(self):
        raw_text = """
题号：AHGWY20210710_04（演讲·默默的坚守·基层奉献·非乡镇岗·16分）
1.题干
环卫工人、武警官兵、科研工作者都默默坚守岗位，请以《默默的坚守》为题发表一篇演讲。
3.核心观点
观点1：默默坚守是平凡中的伟大。第四题：核心采分基准答案
版本1：标准机关高分版。
6.加分点
闭环意识突出：事事有回音、件件有着落。7.得分标准（16分·无省略）
点题扣题（4分）：紧扣主题。
10.全局统一表达仪态分（5分）
语言流畅度（2分）：流畅2分。
11.总分计算规则本题得分=得分标准得分（16分）+仪态分（5分）。
12.检索标签
安徽省考、非乡镇岗、演讲题
        """.strip()

        normalized = normalize_source_text(raw_text, "2020-2025第二批次完全版.extracted.txt")
        sections = extract_sections(normalized)

        self.assertIn("题号：AHGWY-20210710-04", normalized)
        self.assertIn("\n4. 核心采分基准答案", normalized)
        self.assertIn("着落。\n7. 得分标准", normalized)
        self.assertIn("\n11. 总分计算规则", normalized)
        self.assertIn("核心采分基准答案", sections)
        self.assertIn("得分标准", sections)
        self.assertIn("本题总分计算规则", sections)

    def test_detect_template_family_treats_anhui_new_types_as_existing_families(self):
        activate_profile("anhui")

        self.assertEqual(
            detect_template_family(
                {
                    "type": "漫画联想·读书方法+学习实践+工作运用类",
                    "question": "漫画题。请结合工作谈理解。",
                    "tags": ["安徽公务员", "漫画题"],
                    "coreKeywords": ["读书方式"],
                    "strongKeywords": ["学习实践"],
                }
            ),
            "analysis",
        )
        self.assertEqual(
            detect_template_family(
                {
                    "type": "工作落实·制度整改·省直专用",
                    "question": "领导让你负责整改任务，你怎么做？",
                    "tags": ["安徽遴选", "工作落实"],
                    "coreKeywords": ["整改"],
                    "strongKeywords": ["制度整改", "流程优化"],
                }
            ),
            "organization",
        )

    def test_build_runtime_profile_supports_future_region_import_without_new_wrapper(self):
        temp_root = Path(__file__).resolve().parent / "_profile_args"
        source_a = temp_root / "广东-2025.extracted.txt"
        source_b = temp_root / "广东-2024.extracted.txt"

        profile = build_runtime_profile(
            "guangdong",
            "广东",
            [source_a, source_b],
        )

        self.assertEqual(profile.name, "guangdong")
        self.assertEqual(profile.default_province, "广东")
        self.assertEqual(profile.question_output_dir.name, "generated_guangdong")
        self.assertEqual(profile.sample_output_dir.name, "generated_guangdong")
        self.assertEqual(profile.summary_path.name, "import_summary.txt")
        self.assertEqual(profile.source_priority[source_a.name], 2)
        self.assertEqual(profile.source_priority[source_b.name], 1)

        original_profile = activate_profile("hunan")
        try:
            active = activate_profile(profile)
            self.assertEqual(active.name, "guangdong")
            self.assertEqual(active.default_province, "广东")
        finally:
            activate_profile(original_profile)

    def test_interpersonal_mid_templates_cover_responsibility_and_followup(self):
        question_data = {
            "type": "人际沟通·责任担当",
            "province": "安徽",
            "question": "你协助一位同事工作，但因你的失误导致同事被领导批评，你怎么办？",
            "dimensions": [
                {"name": "主动担责", "score": 10},
                {"name": "工作补救", "score": 8},
                {"name": "反思提升", "score": 6},
            ],
            "coreKeywords": ["失误", "担责", "认错", "补救"],
            "strongKeywords": ["同事", "领导", "团队"],
            "weakKeywords": [],
            "scoringCriteria": ["主动担责", "工作补救", "反思提升"],
            "deductionRules": [],
            "tags": ["人际沟通"],
        }

        variants = [text for text, _, _ in build_interpersonal_template_texts(question_data, "mid")]
        joined = "\n".join(variants)

        self.assertIn("同事", joined)
        self.assertIn("责任", joined)
        self.assertTrue(any(token in joined for token in ("补上", "补救", "跟进", "改进")))
        self.assertNotIn("参与对象", joined)

    def test_interpersonal_mid_templates_can_point_back_to_frontline_work_style(self):
        question_data = {
            "type": "人际沟通·同事劝导",
            "province": "安徽",
            "question": "小李总喜欢在朋友圈“做调研”，在微信群里“下基层”，你作为同事怎么劝他？",
            "dimensions": [
                {"name": "沟通态度与语气", "score": 5},
                {"name": "基层作风重要性论述", "score": 7},
                {"name": "引导建议与同事互助", "score": 4},
            ],
            "coreKeywords": ["朋友圈", "微信群", "基层", "劝导"],
            "strongKeywords": ["一线", "入户", "同事"],
            "weakKeywords": [],
            "scoringCriteria": ["沟通态度", "基层作风", "引导建议"],
            "deductionRules": [],
            "tags": ["人际沟通", "基层作风"],
        }

        variants = [text for text, _, _ in build_interpersonal_template_texts(question_data, "mid")]
        joined = "\n".join(variants)

        self.assertIn("同事", joined)
        self.assertTrue(any(token in joined for token in ("一线", "基层", "走一走", "入户")))
        self.assertTrue(any(token in joined for token in ("跟进", "一起", "方法", "作风")))


if __name__ == "__main__":
    unittest.main()
