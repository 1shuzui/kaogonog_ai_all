# 文档总索引

这份索引是后续人工和 AI 继续维护项目时的第一入口。旧文档已保留在 `docs/archive/`，但一线判断优先看下面这些主题文档。字段、接口和运行结论以当前源代码、测试与 FastAPI OpenAPI 为准；文档负责提供稳定查阅路径和跨模块边界。

## AI 快速入口

| 文档 | 用途 |
| --- | --- |
| [AI 项目知识库入口](ai/README.md) | 按任务选择正确的实现、测试和运行文档，先建立事实边界。 |
| [AI 工作上下文与变更地图](ai/project-context.md) | 理解三端、题库资产层、数据流、易错口径与变更检查。 |
| [API 契约总览](api/README.md) | 查看路由地图、URL 前缀边界、鉴权和高优先级契约。 |

## 项目理解

| 文档 | 用途 |
| --- | --- |
| [项目地图](overview/project-map.md) | 快速理解后端、PC、小程序、题库资产和脚本边界。 |
| [数据库内容与字段说明](data/数据库内容与字段说明.md) | 核对 MySQL 表、JSON 字段、缓存键和维护风险。 |
| [题库分类口径](data/question-classification.md) | 区分考试体系、地区、岗位、题型分类和能力维度。 |
| [医疗卫生题库知识库](data/medical-question-bank.md) | 三批医疗题源、文件级套题、稳定 ID、默认仪态分与验收事实。 |
| [题库资产索引](../data/question-bank/README.md) | 查看题库源文档外置路径、模板和校验方式。 |

## 接口与数据契约

| 文档 | 用途 |
| --- | --- |
| [题库、元数据与全真套题接口](api/question-bank-and-suites.md) | 题目查询、生成资产到数据库、完整套题资格和接口响应。 |
| [评分接口与仪态分契约](api/scoring.md) | 内容分、默认/实际仪态分、题目/套题作用域与避免重复加分。 |
| [定向备面、门户与岗位筛选接口](api/targeted-training.md) | positions 分类树、门户标签、岗位筛选、重点分析和抽题。 |

## 运行维护

| 文档 | 用途 |
| --- | --- |
| [本地开发与运行](ops/local-development.md) | 后端、PC、小程序本地启动和构建命令。 |
| [部署与同步手册](ops/deployment-runbook.md) | 同步服务器、构建前检查、部署后验证。 |
| [管理员权益管理](ops/admin-entitlement-management.md) | PC 管理员补发、扣减、查流水和误操作纠正流程。 |
| [密码重置与验证码通道](ops/password-reset-delivery.md) | 管理员核验/签发流程，以及国内短信和邮件服务的官方接入边界。 |
| [密钥与本地配置恢复](ops/secrets-and-local-config.md) | 从 `/home/quyu/doc_kaogong/doc_secret` 恢复 `.env` 和证书。 |
| [清理候选清单](ops/cleanup-candidates.md) | 记录可重建大目录和后续可删除候选，不直接删除。 |
| [外部归档索引](ops/archive-index.md) | 查看迁出文件分类、归档根目录和恢复原则。 |
| [题库导入、重建与验收](ops/question-bank-maintenance.md) | 可重复导入、清单更新、哈希验证、生成资产和回归步骤。 |

## 测试与决策

| 文档 | 用途 |
| --- | --- |
| [测试与报告说明](testing/testing-and-reports.md) | 回归、ASR、题库抽样、库存报告保留规则。 |
| [整理决策 ADR](decisions/ADR-001-local-project-organization.md) | 记录本次项目整理的核心取舍。 |
| [题库源文档外置 ADR](decisions/ADR-002-externalize-question-source-assets.md) | 记录为什么源 Word/抽取文本不再放 Git。 |
| [敏感配置外置 ADR](decisions/ADR-003-externalize-secrets.md) | 记录为什么真实密钥迁出仓库。 |
| [管理员权益调整 ADR](decisions/ADR-004-admin-entitlement-adjustments.md) | 记录人工权益和微信支付订单分离、反向调整保留审计的决策。 |
| [医疗题库与仪态分 ADR](decisions/ADR-005-medical-question-bank-and-appearance-score.md) | 记录文件级组套、JSON 元数据、默认仪态分和实际分替换决策。 |

## 旧文档

旧文档在 [archive](archive/README.md)。它们保留历史背景，但可能包含过期技术口径，例如旧 ASR、旧评分维度或旧部署方式。
