# 项目地图

## 模块边界

| 路径 | 角色 | 维护重点 |
| --- | --- | --- |
| `civil-interview-backend/` | 主业务后端 | 用户、题库、考试、评分、ASR、支付、权益、反馈、定向备面。 |
| `civil-interview-frontend/` | PC 网页端/管理端 | 管理员工作台、用户权益调整、题库、定向配置、支付退款、用户分析、网页练习。 |
| `civil-interview-miniprogram/` | 微信小程序端 | 首页浏览、练习考试、套餐中心、我的、微信虚拟支付。 |
| `ai_gongwu_backend/` | 题库和评分资产层 | 题库 JSON、导入脚本、评分回归样本、历史评分工具。 |
| `scripts/` | 根级运维脚本 | 部署、冒烟、停止/重启服务。 |
| `data/question-bank/` | 题库资料索引 | 模板、外置源文档索引、校验文件。 |
| `reports/` | 最新报告 | 每类只保留最近关键结果，旧报告外置归档。 |
| `docs/` | 文档体系 | AI 知识库、接口契约、一线说明、运行手册、数据字典、决策记录。 |

## 当前核心链路

- 小程序和 PC 均调用 `civil-interview-backend` 的 REST API。
- 后端通过 MySQL 保存用户、题库、考试、答案、历史、订单、权益、用量和反馈。
- Redis 用于题库、LLM 评分和 ASR 转写缓存。
- ASR 使用 FunASR ONNX，本地模型缓存位于 `civil-interview-backend/storage/modelscope_cache/`。
- 题库真实套题信息主要保存在 `questions.keywords._meta`，没有拆出独立套题表。
- 医疗卫生题库的仪态分同样在 `_meta` 中保存；内容分、仪态分和有效满分分开返回，不能仅用 `fullScore` 猜测规则。
- FastAPI 进程内路由直接挂在根路径；生产 `/api` 前缀由网关和客户端 API 基址提供。

## PC 管理端边界

- `/admin` 是管理员工作台入口，集中承载用户权益管理、权益调整流水、余额与退款、定向入口、客服反馈和题库管理。
- 人工补发权益走 `user_subscriptions.package_code=manual_grant`，不创建 `payment_orders`，避免影响微信虚拟支付审核和退款口径。
- 人工扣减指定权益时只增加该权益 `used_minutes`，不写 `usage_records`，避免把售后处理误当成用户答题扣量。
- 管理员误操作通过新增反向调整纠正，不删除 `entitlement_adjustments` 流水。
- 小程序端不提供管理员 UI，但会读取调整后的权益余额。

## 容易混淆的口径

- 能力维度：行政思维、实务落地、逻辑结构、语言表达、综合分析、应急应变。
- 题型/训练分类：综合分析、组织管理、应急应变、人际沟通、情景模拟、岗位认知。
- 考试体系：国家公务员考试、省级公务员考试、事业单位考试、银行招考面试、医疗卫生面试、法检书记员面试。
- 特色入口可以作为展示入口，但不能覆盖真实题源主分类。

## 不建议随手移动的目录

- `ai_gongwu_backend/assets/questions/`：运行和导入依赖的题库 JSON。
- `civil-interview-backend/storage/modelscope_cache/`：FunASR 模型缓存，可重建但下载成本高。
- 三个项目的 `src/`、`app/`、`tests/`：源码结构不属于本次整理范围。

## 深入阅读

- [AI 项目知识库入口](../ai/README.md)
- [API 契约总览](../api/README.md)
- [医疗卫生题库知识库](../data/medical-question-bank.md)
- [题库导入、重建与验收](../ops/question-bank-maintenance.md)
