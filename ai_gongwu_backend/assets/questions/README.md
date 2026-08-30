# 题库目录说明

这个目录用于存放后端可直接加载的单题 JSON 配置。

## 目录约定

1. 一个题目一个 JSON 文件。
2. 文件名优先使用 `question_id.json`。
3. 题库加载器支持读取当前目录及其子目录中的所有 JSON。
4. 手工维护题目和脚本生成题目可以共存，但建议分目录管理。

当前目录的主要结构是：

1. 根目录下的手工题目，例如 `HN-LX-20200606-01.json`
2. `generated_hunan/`、`generated_anhui/`、`generated_jiangsu_shiye/` 等历史/地区导入输出
3. `generated_medical_general/`、`generated_shandong_medical/`、`generated_jiangsu_medical/`
   这是由统一 `scripts/import_question_bank.py` 生成的医疗卫生题库

## 单题 JSON 推荐字段

除题干、分值、维度等基础字段外，当前项目已经实际使用下面这些扩展字段：

1. `sourceDocument`
   原始题库文档名，便于回溯来源。
2. `referenceAnswer`
   该题当前采用的高分基准答案。
3. `scoreBands`
   分档配置，用于判断某个总分落在哪个分档。
4. `regressionCases`
   回归样本配置，通常至少包含高 / 中 / 低三条。
5. `tags`
   题型、场景、岗位等检索标签。

`regressionCases` 中目前常见字段包括：

1. `label`
2. `sample_path`
3. `expected_min`
4. `expected_max`
5. `llmExpectedMin`
6. `llmExpectedMax`
7. `notes`

其中：

1. `expected_min / expected_max`
   主要用于确定性回归脚本 `run_regression.py`
2. `llmExpectedMin / llmExpectedMax`
   主要用于真实大模型回归脚本 `run_llm_regression.py`
   如果存在，LLM 回归会优先使用这组区间判断通过与否

## generated_hunan 说明

`generated_hunan/` 是脚本产物，不建议手工逐个修改。

当前导入链路会：

1. 读取仓库根目录下 4 份湖南题库提取文本
2. 去重同题号重复题
3. 生成单题 JSON
4. 为每题生成 `reference_high.txt / reference_mid.txt / reference_low.txt`
5. 在 `import_summary.txt` 中记录导入数量、重复题和样本生成摘要

截至当前版本：

1. `generated_hunan/` 共 `29` 道题
2. 对应 `assets/regression_samples/generated_hunan/` 下共 `29` 个样本目录

## 医疗卫生生成目录

医疗卫生三批均为脚本产物，来源 DOCX 在仓库外归档，不能手工修改单题 JSON：

| 目录 | 当前题数 | 组套规则 | 正式套题资格 |
| --- | ---: | --- | --- |
| `generated_medical_general/` | 100 | 统一 MED-GENERAL-BATCH | 否 |
| `generated_shandong_medical/` | 259 | 每个 DOCX 一个 SD-MED-SETxxx | 是 |
| `generated_jiangsu_medical/` | 187 | 每个 DOCX 一个 JS-MED-SETxxx | 是 |

医疗题目除基础字段外必须保留真实分类、来源、套题和独立仪态分字段：

1. `examCategory=事业单位考试`、`examSubcategory`、`portalTags/displayPortals=医疗卫生面试`；
2. `sourceDocument`、`originFile`、`sourceQuestionId`、`suiteId/suiteKey`、`questionNo`；
3. `questionScore`、`appearanceScore`、`appearanceScoreMax`、`appearanceScoreSource`、`appearanceScoreScope`、`effectiveFullScore`；
4. `hasCompleteSuiteLevel`、`hasAppearanceScore`、`scoreCalculationNote`、`reviewStatus/reviewReason`。

其中 `questionScore` 是内容上限，`appearanceScore` 是正式评分项；suite 作用域的仪态分只能在整套合计时计入一次。完整规则见 [医疗卫生题库知识库](../../../docs/data/medical-question-bank.md)。

## 维护建议

1. 如果你改了导入规则、样本生成规则或题型模板，不要手改大量生成文件。
2. 优先修改 `scripts/import_question_bank.py` 中的通用逻辑或 profile，然后重新执行导入脚本。
3. 重新导入后，建议依次执行：
   - `scripts/run_regression.py`
   - `scripts/run_llm_regression.py --repeat 3`
4. 当 LLM 子集结果稳定后，再使用 `--writeback` 回写 `llmExpectedMin / llmExpectedMax`。

具体导入命令、外部题源校验和批次验收见 [题库导入、重建与验收](../../../docs/ops/question-bank-maintenance.md)。
