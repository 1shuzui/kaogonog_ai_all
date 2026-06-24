"""
这个测试文件守住 `test_import_question_bank` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import unittest
from pathlib import Path

from scripts.extract_docx_text import extract_docx_text
from scripts.import_question_bank import (
    activate_profile,
    build_classification_metadata,
    build_runtime_profile,
    build_interpersonal_template_texts,
    clean_section_body,
    detect_template_family,
    extract_sections,
    normalize_question_id,
    normalize_source_text,
    parse_question_block,
    parse_scored_items,
    resolve_question_province,
)


class ExtractDocxTextTestCase(unittest.TestCase):
    """
    锁住 .docx 提取脚本的输出格式。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def test_extract_docx_text_matches_existing_hunan_fixture(self):
        """
        test_extract_docx_text_matches_existing_hunan_fixture 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        repo_root = Path(__file__).resolve().parents[2]
        docx_path = repo_root / "湖南-2020-通用岗.docx"
        extracted_path = repo_root / "湖南-2020-通用岗.extracted.txt"

        self.assertEqual(
            extract_docx_text(docx_path),
            extracted_path.read_text(encoding="utf-8"),
        )


class ImportQuestionBankNormalizationTestCase(unittest.TestCase):
    """
    锁住安徽兼容化归一规则。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    maxDiff = None

    def test_normalize_question_id_supports_anhui_variants(self):
        """
        test_normalize_question_id_supports_anhui_variants 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.assertEqual(normalize_question_id("AHGWY 20201113PM 01"), "AHGWY-20201113PM-01")
        self.assertEqual(normalize_question_id("AHGWY20201114_01"), "AHGWY-20201114-01")
        self.assertEqual(normalize_question_id("AHGX20201226_01"), "AHGX-20201226-01")

    def test_normalize_source_text_repairs_inline_headers_and_chinese_section_labels(self):
        """
        test_normalize_source_text_repairs_inline_headers_and_chinese_section_labels 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
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

    def test_extract_sections_removes_heading_colon_from_question_body(self):
        """
        test_extract_sections_removes_heading_colon_from_question_body 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        sections = extract_sections(
            """
题号：AHGWY-20201113PM-03
1.题干：市里要将废弃工厂改造成居民文化体验中心，谈谈你的创意方案。
2.题型定位：组织管理题
            """.strip()
        )

        self.assertEqual(clean_section_body("：\n社区书刊窗口"), "社区书刊窗口")
        self.assertEqual(
            sections["题干"],
            "市里要将废弃工厂改造成居民文化体验中心，谈谈你的创意方案。",
        )

    def test_jiangsu_variants_parse_core_scoring_and_plain_score_items(self):
        """
        test_jiangsu_variants_parse_core_scoring_and_plain_score_items 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_profile = activate_profile("hunan")
        try:
            activate_profile("jiangsu_shiye")
            raw_text = """
题号：JS-SAMPLE-20260101-01（综合分析+基层治理类，赋分24分）
1. 题干：请结合基层工作，谈谈如何做好民情日记的传承与发展。
2. 题型定位：综合分析题，适用省份：江苏。
3. 核心观点：守正创新，闭环办理。
4.核心采分
基准答案各位考官，民情日记连接群众诉求和基层治理效能。要坚持群众路线，既传承走访入户的好作风，也用数字化手段推动诉求闭环办理。
5. 多角度同义表述库：民情日记、群众路线、基层治理
6. 加分点：闭环办理、数字赋能
7. 得分标准：核心认知与政治站位8分，要求立场正确；传承内涵与破弊举措10分，要求举措具体；语言表达4分，要求逻辑清楚；创新思维2分。总分24分。
8. 扣分标准：内容空泛扣4分。
9. AI评分结构化数据：核心识别词：民情日记、群众路线；强关联识别词：闭环办理、数字赋能；题型信息：综合分析，适用省份：江苏，满分：24分。
10. 全局统一表达仪态分：满分5分。
11. 总分计算规则：本题得分=得分标准得分（24分）。
12. 检索标签：江苏事业单位、基层治理
            """.strip()

            normalized = normalize_source_text(raw_text, "2017-2025江苏事业单位真题题库.extracted.txt")
            parsed = parse_question_block(normalized, Path("2017-2025江苏事业单位真题题库.extracted.txt")).data

            self.assertEqual(parsed["province"], "江苏")
            self.assertEqual(parsed["fullScore"], 24.0)
            self.assertEqual(parsed["question"], "请结合基层工作，谈谈如何做好民情日记的传承与发展。")
            self.assertEqual(parsed["examCategory"], "事业单位考试")
            self.assertEqual(parsed["questionTypeCategory"], "综合分析")
            self.assertEqual(parsed.get("positionType", ""), "")
            self.assertEqual(parsed.get("portalTags", []), [])
            self.assertEqual(parsed["reviewStatus"], "需人工复核")
            self.assertIn("缺少真实中文套题名", parsed["reviewReason"])
            self.assertTrue(parsed["referenceAnswer"].startswith("各位考官"))
            self.assertEqual(
                [item["name"] for item in parsed["dimensions"]],
                ["核心认知与政治站位", "传承内涵与破弊举措", "语言表达", "创新思维"],
            )
        finally:
            activate_profile(original_profile)

    def test_classification_keeps_real_source_separate_from_display_portals(self):
        """
        test_classification_keeps_real_source_separate_from_display_portals 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_profile = activate_profile("hunan")
        try:
            activate_profile("jiangsu_shiye")
            jiangsu_medical = build_classification_metadata(
                source_document="2017-2025江苏事业单位真题题库.docx",
                province="江苏",
                suite_name="2025年7月5日江苏省连云港市连云区事业单位面试题",
                source_title_raw="2025年7月5日江苏省连云港市连云区事业单位面试题",
                position="护理岗",
                batch="",
                question_type="岗位认知·医疗服务",
                question_text="医院窗口服务中有群众投诉，你作为护理岗工作人员怎么办？",
                question_no=1,
                question_score=25,
                suite_key="JS-LYG-LYQ20250705",
            )

            self.assertEqual(jiangsu_medical["examCategory"], "事业单位考试")
            self.assertEqual(jiangsu_medical["examSubcategory"], "江苏省")
            self.assertIn("医疗卫生面试", jiangsu_medical["portalTags"])
            self.assertNotEqual(jiangsu_medical["examCategory"], "医疗卫生面试")

            activate_profile("anhui")
            anhui = build_classification_metadata(
                source_document="2020-2025第二批次完全版.docx",
                province="安徽",
                suite_name="2025年5月17日安徽省公务员面试题",
                source_title_raw="2025年5月17日安徽省公务员面试题",
                position="综合管理类",
                batch="",
                question_type="综合分析",
                question_text="请结合基层治理谈看法，材料中提到B类事项清单。",
                question_no=1,
                question_score=25,
                suite_key="AHGWY-20250517",
            )

            self.assertEqual(anhui["examCategory"], "省级公务员考试")
            self.assertEqual(anhui["examSubcategory"], "安徽省")
            self.assertNotIn("江苏", anhui.get("positionType", ""))
            self.assertNotIn("B类", anhui.get("positionType", ""))

            activate_profile("hunan")
            hunan_prison = build_classification_metadata(
                source_document="湖南-监狱-2020.docx",
                province="湖南",
                suite_name="2020年9月19日湖南省考省直监狱岗位面试题",
                source_title_raw="2020年9月19日湖南省考省直监狱岗位面试题",
                position="省直监狱岗位",
                batch="监狱岗",
                question_type="应急应变",
                question_text="监狱管理中遇到突发情况，你会如何处置？",
                question_no=1,
                question_score=25,
                suite_key="HN-20200919-JY",
            )

            self.assertEqual(hunan_prison["examCategory"], "省级公务员考试")
            self.assertEqual(hunan_prison["examSubcategory"], "湖南省")
            self.assertEqual(hunan_prison["system"], "监狱系统")
            self.assertNotIn("法检书记员面试", hunan_prison["portalTags"])
        finally:
            activate_profile(original_profile)

    def test_jiangsu_profile_normalizes_city_area_to_province(self):
        """
        test_jiangsu_profile_normalizes_city_area_to_province 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_profile = activate_profile("hunan")
        try:
            activate_profile("jiangsu_shiye")

            self.assertEqual(resolve_question_province("江苏泰州"), "江苏")
            self.assertEqual(resolve_question_province("泰州"), "江苏")
        finally:
            activate_profile(original_profile)

    def test_parse_scored_items_supports_old_jiangsu_band_only_fallback_source(self):
        """
        test_parse_scored_items_supports_old_jiangsu_band_only_fallback_source 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        items = parse_scored_items(
            "分项细则：政治站位服务理念6分、流程逻辑框架7分、"
            "资源整合落地7分、语言表达感染力6分、亮点创新3分、综合印象2分。"
        )

        self.assertEqual(len(items), 6)
        self.assertEqual(items[0], "政治站位服务理念（6分）：")
        self.assertEqual(items[-1], "综合印象（2分）：")

    def test_detect_template_family_treats_anhui_new_types_as_existing_families(self):
        """
        test_detect_template_family_treats_anhui_new_types_as_existing_families 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
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
        """
        test_build_runtime_profile_supports_future_region_import_without_new_wrapper 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
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
        """
        test_interpersonal_mid_templates_cover_responsibility_and_followup 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
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
        """
        test_interpersonal_mid_templates_can_point_back_to_frontline_work_style 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
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
