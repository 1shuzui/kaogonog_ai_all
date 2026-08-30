# AI 项目知识库入口

本目录是本项目的 AI 与人工协作入口。它不替代源代码、测试或 FastAPI 自动文档；它的作用是先给出稳定的系统边界、术语和查阅顺序，避免在大仓库中把不同考试体系、不同分值口径或不同前后端接口混为一谈。

## 先读什么

| 当前任务 | 首先阅读 | 然后核对 |
| --- | --- | --- |
| 熟悉项目、定位代码 | [项目上下文](project-context.md) | [项目地图](../overview/project-map.md) |
| 新增或修复题库 | [医疗卫生题库知识库](../data/medical-question-bank.md) | [题库维护运行手册](../ops/question-bank-maintenance.md) |
| 修改题目、套题或同步行为 | [题库与套题接口](../api/question-bank-and-suites.md) | [题库分类口径](../data/question-classification.md) |
| 修改评分、仪态分或结果页 | [评分接口与分值契约](../api/scoring.md) | [ADR-005](../decisions/ADR-005-medical-question-bank-and-appearance-score.md) |
| 修改定向备面、门户或岗位筛选 | [定向备面接口](../api/targeted-training.md) | 后端 positions 路由与两端兜底分类树 |
| 排查部署、题库资料或测试 | [本地开发](../ops/local-development.md) 与 [测试说明](../testing/testing-and-reports.md) | [题库资产索引](../../data/question-bank/README.md) |

## 不可违反的项目事实

1. 医疗卫生是展示门户和岗位方向，不自动等同于真实考试体系。当前三批医疗卫生资产的真实主分类都是 **事业单位考试**。
2. 题库运行资产是仓库内 JSON；原始 DOC/DOCX 仅保存在仓库外的题源归档中，不能移动桌面原件，也不能提交进 Git。
3. 后端没有为题库元数据新增关系表或实体列。来源、套题、门户、岗位和仪态分等扩展字段统一保存在 **questions.keywords._meta**，并由题库服务透传。
4. 对有仪态分的题目，内容分和仪态分必须分开处理。**95 + 5 = 100 是合法结构，不是分值冲突。** 但不能假设所有题目内容分都是 95；应读取题目的 **questionScore** 与 **effectiveFullScore**。
5. **appearanceScoreScope=suite** 时，仪态分只计入整套一次；任何汇总端都不得把每道题上携带的同一仪态分重复相加。
6. 通用医疗卫生 100 题共享一个批次键以便追溯，但 **hasCompleteSuiteLevel=false**，不得展示为一张 100 题的正式全真套卷。
7. 生成目录只能由导入脚本重建，不能手改单个 JSON；修改导入器、评分服务、题库服务或分类树时，必须同时阅读相应契约文档和测试。

## 事实来源优先级

出现文档、实现和运行结果不一致时，按以下优先级判断并修正文档：

1. 受测试覆盖的当前源代码和 FastAPI 自动 OpenAPI；
2. 已生成题库 JSON、导入摘要和受版本控制的清单；
3. 当前回归报告与测试用例；
4. 本目录及 docs 下的一线文档；
5. docs/archive 下的历史材料。

不要把历史文档、文件名、单一岗位词或前端展示名称当作分类真相。

## 维护规则

- 文档里出现的 API 路径以 FastAPI 进程内路径为准。生产环境是否带 **/api** 前缀由网关和前端基址决定，不要把代理前缀误写成后端路由前缀。
- 文档出现新的字段、端点、profile、题源批次或测试命令时，同步更新 [文档总索引](../README.md) 和下方的自动检查范围。
- 重大、长期有效的架构取舍写入 **docs/decisions/**；临时排障过程写入报告或 issue，不要塞进 ADR。
- 提交前运行 **.venv/bin/python scripts/validate_project_docs.py**；它会检查知识库文件、关键术语和本地 Markdown 链接。
