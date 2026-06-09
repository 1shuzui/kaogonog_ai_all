# 文档总索引

这份索引是后续人工和 AI 继续维护项目时的第一入口。旧文档已保留在 `docs/archive/`，但一线判断优先看下面这些主题文档。

## 项目理解

| 文档 | 用途 |
| --- | --- |
| [项目地图](overview/project-map.md) | 快速理解后端、PC、小程序、题库资产和脚本边界。 |
| [数据库内容与字段说明](data/数据库内容与字段说明.md) | 核对 MySQL 表、JSON 字段、缓存键和维护风险。 |
| [题库分类口径](data/question-classification.md) | 区分考试体系、地区、岗位、题型分类和能力维度。 |
| [题库资产索引](../data/question-bank/README.md) | 查看题库源文档外置路径、模板和校验方式。 |

## 运行维护

| 文档 | 用途 |
| --- | --- |
| [本地开发与运行](ops/local-development.md) | 后端、PC、小程序本地启动和构建命令。 |
| [部署与同步手册](ops/deployment-runbook.md) | 同步服务器、构建前检查、部署后验证。 |
| [管理员权益管理](ops/admin-entitlement-management.md) | PC 管理员补发、扣减、查流水和误操作纠正流程。 |
| [密钥与本地配置恢复](ops/secrets-and-local-config.md) | 从 `/home/quyu/doc_kaogong/doc_secret` 恢复 `.env` 和证书。 |
| [清理候选清单](ops/cleanup-candidates.md) | 记录可重建大目录和后续可删除候选，不直接删除。 |
| [外部归档索引](ops/archive-index.md) | 查看迁出文件分类、归档根目录和恢复原则。 |

## 测试与决策

| 文档 | 用途 |
| --- | --- |
| [测试与报告说明](testing/testing-and-reports.md) | 回归、ASR、题库抽样、库存报告保留规则。 |
| [整理决策 ADR](decisions/ADR-001-local-project-organization.md) | 记录本次项目整理的核心取舍。 |
| [题库源文档外置 ADR](decisions/ADR-002-externalize-question-source-assets.md) | 记录为什么源 Word/抽取文本不再放 Git。 |
| [敏感配置外置 ADR](decisions/ADR-003-externalize-secrets.md) | 记录为什么真实密钥迁出仓库。 |
| [管理员权益调整 ADR](decisions/ADR-004-admin-entitlement-adjustments.md) | 记录人工权益和微信支付订单分离、反向调整保留审计的决策。 |

## 旧文档

旧文档在 [archive](archive/README.md)。它们保留历史背景，但可能包含过期技术口径，例如旧 ASR、旧评分维度或旧部署方式。
