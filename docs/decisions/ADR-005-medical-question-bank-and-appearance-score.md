# ADR-005: 医疗卫生题库采用文件级套题与独立仪态分

## Status

Accepted

## Date

2026-08-24

## Context

项目新增三批医疗卫生面试 DOCX：通用 100 题、山东 137 个文件/259 题、江苏 70 个实际文件/187 题。源文档混合了裸题头、重复分栏、共享总分规则、套题级仪态分和不同采分点写法。

已有系统把题库扩展字段放在 Question.keywords 的 JSON 元数据中，没有独立套题表；既有全真模拟依赖稳定的 suiteKey、题号和来源信息。旧的分值推断逻辑容易把内容分与仪态分混为“总分不一致”，并可能把 95 内容分 + 5 仪态分错误标记为待确认。

## Decision

1. 三批医疗题都使用真实考试体系 **事业单位考试**；**医疗卫生面试** 仅作为 portalTags/displayPortals 和岗位展示入口。
2. 题源按文件强制组套：山东、江苏每个 DOCX 一个 suiteId/suiteKey；通用 100 题保留单一批次键，但显式设 **hasCompleteSuiteLevel=false**。
3. 不新增关系型表或数据库列。题源、套题、门户、岗位和仪态字段保留在生成 JSON，并同步到 **questions.keywords._meta**。
4. 评分字段分离内容分与仪态分：
   - questionScore 是内容上限；
   - appearanceScore 与 appearanceScoreMax 是仪态项；
   - effectiveFullScore 是题目有效满分；
   - appearanceScoreSource 区分 source_explicit、profile_default、actual；
   - appearanceScoreScope 区分 question、suite。
5. 当前没有可执行仪态评分器时，医疗 profile 使用默认 5 分。默认分是有效评分项，不进入解析失败、分值冲突或待确认清单。
6. 当以后写入真实仪态分时，真实分替换默认分，不能再次加分；套题级仪态分在整套总分中只计算一次。
7. 正式套题列表只展示至少两题、题号从 1 连续、同一文件级套题键且 hasCompleteSuiteLevel 不为 false 的集合。

## Alternatives considered

### 把医疗卫生面试设为唯一 examCategory

未采用。医疗卫生是跨地区、跨招录入口的展示维度；将它取代事业单位考试会破坏真实题源筛选、全真套题和已有统计口径。

### 把 95 + 5 视作数据冲突或默认仪态分记为 0

未采用。仪态分是用户确认的正式评分组成，0 分会系统性低估总分；标成冲突会让正确题源进入人工待确认队列，污染质量信号。

### 将仪态分只作为页面展示，不进入评分结果

未采用。这样题目满分、评分详情和套题合计会使用不同口径，无法解释最终成绩，也无法安全替换未来真实仪态分。

### 为套题、仪态分新增关系表与数据库列

暂未采用。现有题库数据和同步机制已以 JSON 元数据为扩展边界，新增关系模型会带来迁移、历史数据回填和跨端兼容成本。若未来需要跨套题复杂查询、独立审核工作流或多次仪态记录，再以新的 ADR 评估数据库演进。

### 按题干相似度自动合并医疗题

未采用。相同题干可能属于不同省份、源文件、题号、套题和分值规则；稳定来源 ID 比文本相似度更可靠。

## Consequences

### Positive

- 题源、题号和套题可完整追溯；
- 医疗门户与真实考试分类可以同时服务用户；
- 内容分、默认仪态分和未来真实仪态分有清晰替换关系；
- 无需破坏已有数据库结构或旧题库；
- 通用 100 题不会被误包装成正式 100 题试卷。

### Costs and risks

- 消费端需要理解 question 与 suite 两种仪态作用域；
- 生成 JSON 与 keywords._meta 的字段需要保持一致；
- 不能从 fullScore 是否为 100 推断题目合法性；
- 后续真正接入仪态模型时，必须走 actual 替换路径并补充更严格的审计与公平性评估。

## Verification

决策由以下测试和检查守护：

- ai_gongwu_backend/tests/test_medical_question_bank.py；
- civil-interview-backend/tests/test_medical_question_bank_assets.py；
- civil-interview-backend/tests/test_scoring_appearance_score.py；
- 题源 SHA-256 校验和 inventory sourceBatches；
- /exam/full-suites 的完整套题资格规则；
- 题库、评分和文档检查的回归命令。

## Follow-up triggers

满足任一条件时，应新增 ADR 或修订本决策：

1. 引入可执行、可审计的真实仪态评分模型；
2. 需要对套题进行跨表检索、独立审核或版本历史管理；
3. 出现第三种仪态作用域或不同的多题分值结构；
4. 将医疗卫生入口扩展到非事业单位真实考试体系。
