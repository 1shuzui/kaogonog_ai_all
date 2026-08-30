# AI 工作上下文与变更地图

## 项目在做什么

这是一个面向公务员、事业单位、银行、医疗卫生等场景的面试练习与测评系统。它有 PC 端、小程序端和一个 FastAPI 业务后端；题库的导入、可重复生成和评分回归放在独立的资产层。

状态基线：本文以 2026-08-24 的仓库实现和已生成医疗卫生题库为准。

## 代码与数据边界

| 区域 | 主要职责 | 从这里开始读 |
| --- | --- | --- |
| civil-interview-backend | REST API、鉴权、题库同步、考试、评分、ASR、支付、权益 | main.py、app/api/v1/__init__.py、app/services/ |
| civil-interview-frontend | PC 用户端与管理员端 | src/api/、src/stores/、src/utils/targetedOptions.js |
| civil-interview-miniprogram | uni-app 小程序与管理员页 | src/api/、src/stores/、src/utils/targetedOptions.js |
| ai_gongwu_backend | DOCX/文本导入器、题库 JSON、回归样本、历史评分资产 | scripts/import_question_bank.py、assets/questions/ |
| data/question-bank | 题源清单、SHA-256、导入模板 | inventory.json、checksums.sha256、README.md |
| scripts | 题源清单更新、部署、变更检测等根级工具 | update_question_bank_manifest.py |
| docs | 当前技术知识库、运维手册、ADR | docs/README.md |
| reports | 最近保留的测试与评分回归产物 | reports/README.md |

## 两条关键数据流

### 题库链路

外部 DOCX 题源
→ 通用导入器
→ generated_* 题库 JSON 与回归样本
→ 后端启动时同步
→ Question 核心列 + keywords._meta
→ 题库、套题、定向备面 REST 接口
→ PC / 小程序。

源 DOCX 是可追溯输入，不是运行时资产。后端同步的是仓库内 generated_* JSON；源文件丢失、移动或未校验都可能使后续重建失去可重复性。

### 评分链路

题目元数据 + 考生文字稿/ASR
→ 内容评分（LLM 或离线规则）
→ 评分结果装饰
→ 内容分、仪态分、总分和满分
→ 持久化到考试答案/评分结果
→ 历史复盘与结果页。

评分中的能力维度与题型分类不是同一个概念：能力维度用于评价答题表现，题型分类用于训练和筛题。

## 变更时的最短可靠阅读路径

| 想改的内容 | 主实现 | 必须一并检查 | 最小验证 |
| --- | --- | --- | --- |
| DOCX 标签、题号、采分点解析 | ai_gongwu_backend/scripts/import_question_bank.py | 导入器测试、生成摘要、题源清单 | ai_gongwu_backend 题库测试 |
| 题库字段、资产同步、套题完整性 | civil-interview-backend/app/services/question_service.py | schemas/common.py、question_routes.py、资产测试 | 后端题库资产测试 |
| 分数、仪态分、短答收敛 | civil-interview-backend/app/services/scoring_service.py | scoring_routes.py、评分测试、ADR-005 | 评分仪态测试 |
| 医疗门户/岗位树 | targeted_routes.py | PC/小程序 targetedOptions.js、定向筛选测试 | 后端 positions 与定向测试 |
| API 请求/响应形状 | app/api/v1/routes/ 与 app/schemas/common.py | 两端 src/api/ 与 stores | FastAPI OpenAPI + 对应 pytest |
| 题源目录、校验和、批次数量 | scripts/update_question_bank_manifest.py | inventory.json、checksums.sha256、题库运行手册 | sha256sum + 清单脚本 |

## 高风险误解清单

| 不要这样理解 | 正确理解 |
| --- | --- |
| 医疗卫生面试就是 examCategory | 医疗卫生面试是 portalTags/displayPortals；当前三批真实 examCategory 是事业单位考试。 |
| province 可以替代考试体系 | province 只表示地域；真实筛选先看 examCategory，再看 examSubcategory、岗位、门户。 |
| 所有医疗题都是 95 分内容 + 5 分仪态 | 95 + 5 是典型且合法的结构；实际内容上限以 questionScore 为准。 |
| appearanceScore 出现在每道题就应逐题累加 | appearanceScoreScope=suite 时只能在套题合计时算一次。 |
| 同文件共享 suiteKey 就一定是正式卷 | 还必须题数不少于 2、题号从 1 连续、同源文件且 hasCompleteSuiteLevel 不为 false。 |
| 题干相同的生成 JSON 可以合并 | 医疗题以稳定源题 ID 为主，不能因题干相同把不同来源题覆盖。 |
| 后端 API 都是 /api/v1/* | 进程内路由由 main.py 直接挂载；外部 /api 前缀来自部署层/客户端配置。 |

## 任务开始和结束检查

开始时：

1. 查看 git status，识别并保留用户已有未提交文件；
2. 阅读与任务对应的本目录入口，再查看实现和测试；
3. 修改现有代码符号前完成项目要求的影响分析；
4. 对生成资产只改生成逻辑和输入，然后重建，不手改输出。

结束时：

1. 运行任务对应测试、格式/链接检查和 git diff --check；
2. 对题源相关变更核验清单、数量、ID、套题题号与 SHA-256；
3. 更新知识库和 ADR（若产生长期架构取舍）；
4. 运行项目变更检测，确认未触及无关模块或用户未提交页面。
