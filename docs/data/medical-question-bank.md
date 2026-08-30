# 医疗卫生题库知识库

## 范围与当前验收基线

本文件记录三批医疗卫生面试题的来源、导入、分类、套题和分值规则。它是题库变更时的领域事实入口；字段级 REST 输出见 [题库与套题接口](../api/question-bank-and-suites.md)，评分返回见 [评分接口与仪态分契约](../api/scoring.md)。

| Profile | 外部源文件 | 已生成题目 | 文件级套题 | 正式全真套题 |
| --- | ---: | ---: | --- | --- |
| medical_general | 1 | 100 | 一个统一批次键 | 否 |
| shandong_medical | 137 | 259 | 每个 DOCX 一个套题 | 是 |
| jiangsu_medical | 70 个实际文件 | 187 | 每个 DOCX 一个套题 | 是 |

江苏资料编号理论上覆盖 71 套，但 **江苏新套03** 不存在。它是清单中明确记录的缺失输入，不是解析失败；因此没有 JS-MED-SET003。

## 题源与可追溯性

原始文件均在仓库外，运行资产和题源不可混淆：

| 内容 | 位置 | Git 策略 |
| --- | --- | --- |
| 通用医疗卫生源 DOCX | /home/quyu/doc_kaogong/question-bank/source/medical_general | 不提交 |
| 山东医疗卫生源 DOCX | /home/quyu/doc_kaogong/question-bank/source/shandong_medical | 不提交 |
| 江苏医疗卫生源 DOCX | /home/quyu/doc_kaogong/question-bank/source/jiangsu_medical | 不提交 |
| 源目录、原桌面路径、大小与 SHA-256 | data/question-bank/inventory.json | 提交 |
| 外部题源 SHA-256 清单 | data/question-bank/checksums.sha256 | 提交 |
| 可运行题库 JSON | ai_gongwu_backend/assets/questions/generated_*_medical | 提交 |
| 回归样本 | ai_gongwu_backend/assets/regression_samples/generated_*_medical | 提交 |

原桌面资料是用户原件。归档过程只能复制，绝不能移动或删除原件。需要核验归档时运行：

~~~bash
cd /home/quyu/kaogong_ai
sha256sum -c data/question-bank/checksums.sha256 --ignore-missing
~~~

清单中的 **sourceBatches** 是批次验收事实：医疗通用 1/100，山东 137/259，江苏 70 实际文件/187 题，且江苏清单显式记录缺失项。

## Profile 与分类契约

所有医疗题具有下列不变分类：

| 字段 | medical_general | shandong_medical | jiangsu_medical |
| --- | --- | --- | --- |
| province | 全国 → 后端 national | 山东 → shandong | 江苏 → jiangsu |
| examCategory | 事业单位考试 | 事业单位考试 | 事业单位考试 |
| examSubcategory | 通用医疗卫生题库 | 山东省 | 江苏省 |
| portalTags / displayPortals | 医疗卫生面试 | 医疗卫生面试 | 医疗卫生面试 |
| positionTags | 至少 medical | 至少 medical | 至少 medical |
| interviewFormat | 医疗卫生结构化面试 | 医疗卫生结构化面试 | 医疗卫生结构化面试 |
| hasCompleteSuiteLevel | false | true | true |

医疗卫生面试只是门户标签和岗位方向，不能把 **examCategory** 改成医疗卫生面试。分类语义的完整约束见 [题库分类口径](question-classification.md)。

题型定位被归一到以下标准训练分类：

- 综合分析；
- 组织管理；
- 应急应变；
- 人际沟通；
- 情景模拟；
- 岗位认知。

这六类用于专项训练，不等于评分时的能力维度。

## 稳定 ID 与套题关系

| 批次 | stable ID | suiteId / suiteKey | sourceQuestionId |
| --- | --- | --- | --- |
| 通用 100 题 | 优先沿用源显式 ID，例如 YL-综合-059 | MED-GENERAL-BATCH | 保留源 ID 以便追溯 |
| 山东 | SD-MED-SET001-01 形式 | SD-MED-SET001 形式 | 保留源题号/原题 ID |
| 江苏 | JS-MED-SET001-01 形式 | JS-MED-SET001 形式 | 保留源题号/原题 ID |

山东和江苏同一 **originFile** 的题目必须：

1. 共享一个 suiteId/suiteKey；
2. 题号从 1 连续；
3. 使用同一个源文档；
4. 以该文件为唯一组套边界，而不是按题干相似度或题型重组。

通用 100 题也保留文件级批次键以满足追溯和导入一致性，但因 **hasCompleteSuiteLevel=false** 不得出现在 /exam/full-suites 中。

已覆盖的江苏特殊布局包括第 39 套（3 题）和第 45 套（2 题）：导入器按题目序号重组重复题干区块，而不是把卷首汇总行误当作题目。

## DOCX 解析规则

导入器是 **ai_gongwu_backend/scripts/import_question_bank.py**。它从 DOCX XML 直接读取段落，或读取 legacy .doc 的相邻 extracted 文本。可重复传入 **--source-dir**，并对目录中的 .docx、.doc 和 .extracted.txt 按稳定文件名排序。

已支持的主要格式：

| 类型 | 兼容行为 |
| --- | --- |
| 标签变体 | 归一化 题干、题型定位、核心采分基准答案、得分标准 等标签。 |
| 总分标签 | 总分计算 可作为 总分计算规则 的兼容别名。 |
| 裸题头 | 识别 山东/江苏中的 第1题、第2题 等，并生成稳定 ID。 |
| 套题汇总行 | 排除 第1题（32分）+第2题（36分）等非题目行。 |
| 题干冗余前缀 | 清理 第一题：、第1题： 等。 |
| 特殊布局 | 按题目序号合并第 39、45 套一类的分栏/重复区块。 |
| 共享分值标签 | 以作用域关联到套题或题目，不以标签次数是否等于题目数判错。 |
| 采分点写法 | 兼容 名称(8分)+名称(10分)、中文全角括号、无括号连续 名称15分名称25分 等。 |

硬失败仍然阻止不完整资产生成：题干、参考答案、采分点缺失，或某源文件题目数无法重建，都属于失败。缺少可执行仪态标准不是失败，会走 profile 默认分。

## 分数与仪态分

### 字段模型

| 字段 | 含义 |
| --- | --- |
| questionScore | 源文件中的内容分上限。 |
| appearanceScore | 当前生效仪态分；默认或实际分。 |
| appearanceScoreMax | 仪态项上限。 |
| appearanceScoreSource | source_explicit、profile_default、actual。 |
| appearanceScoreScope | question 或 suite。 |
| effectiveFullScore | 题目展示的有效满分。 |
| fullScore | 生成资产中的有效满分别名，应与 effectiveFullScore 一致。 |
| suiteTotalScore / totalScore | 套题的统一总分，尤其用于 suite 作用域。 |
| scoreCalculationNote | 人和页面可读的分数解释。 |
| hasAppearanceScore | 是否存在仪态评分项。 |

### 规则

1. 对当前三批医疗 profile，若源文档没有可执行的数字仪态规则，默认 **appearanceScore=5**、**appearanceScoreMax=5**、**appearanceScoreSource=profile_default**。
2. 如果源文档明确给出可执行仪态分，写为 **source_explicit**。
3. 出现“本题满分”“每题含仪态分”等语义时按 **question** 作用域；出现“全局统一表达仪态分”“整套试卷总分”等语义时按 **suite** 作用域；没有明确语义时，医疗 profile 默认题目级。
4. 通常的 95 内容分 + 5 仪态分是有效的 100 分结构，不能写 reviewStatus=待确认，也不能写入 reviewReason。
5. 内容上限并不总是 95。页面、接口调用方和回归脚本都必须读取字段，不能把任何医疗题硬编码为 100 分。
6. 后续接入真实仪态识别后，**actual** 分数替换默认分，不与默认 5 相加。
7. **suite** 作用域在套题汇总中只加一次。题目上的元数据用于解释来源，不表示可逐题累积的仪态预算。

完整的 API 返回与计算例子见 [评分接口与仪态分契约](../api/scoring.md)。

## 生成资产契约

每个医疗题 JSON 至少保留：

~~~text
id, type, province, fullScore, question, scoringPoints, referenceAnswer,
examCategory, examSubcategory, portalTags, displayPortals, positionTags,
positionType, interviewFormat, questionTypeCategory,
suiteId, suiteKey, suiteName, sourceDocument, originFile, sourceQuestionId,
questionNo, questionScore, appearanceScore, appearanceScoreMax,
appearanceScoreSource, appearanceScoreScope, effectiveFullScore,
hasAppearanceScore, hasCompleteSuiteLevel, scoreCalculationNote,
reviewStatus, reviewReason
~~~

生成 JSON 同时存放顶层字段和用于同步的元数据。后端会把扩展字段放到 **keywords._meta**，并在题库/套题 API 中重新透传。不要删除“看似重复”的来源字段；它们支撑生成可追溯性、数据库同步和客户端响应三个不同边界。

## 测试锚点

| 验证 | 覆盖文件 |
| --- | --- |
| 批次数量、字段、ID、套题连续性、江苏 39/45、默认分 | ai_gongwu_backend/tests/test_medical_question_bank.py |
| 真实资产同步、门户/岗位筛选、通用批次不展示为全真套题 | civil-interview-backend/tests/test_medical_question_bank_assets.py |
| 默认分不重复、actual 替换默认值 | civil-interview-backend/tests/test_scoring_appearance_score.py |

任何未来 profile、分值作用域或字段名变更，都要先更新这三类测试和本文件，再重建生成资产。
