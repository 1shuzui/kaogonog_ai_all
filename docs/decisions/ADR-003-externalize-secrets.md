# ADR-003: 真实密钥和本地配置迁出仓库目录

## Status
Accepted

## Date
2026-06-09

## Context

仓库中存在 `.env`、微信支付证书、公钥和数据库备份等敏感文件。虽然它们已被 `.gitignore` 覆盖，但放在项目目录里仍容易被误读、误传或误打包。

## Decision

- 真实 `.env`、`*.pem`、`*.p12`、`pub_key.pem` 和数据库备份迁到 `/home/quyu/doc_kaogong/doc_secret/`。
- 仓库不保留真实内容，也不保留软链。
- 用 `docs/ops/secrets-and-local-config.md` 记录恢复路径和复制命令。

## Consequences

- 仓库更安全，误提交风险更低。
- 本地运行前需要先恢复配置。
- 文档不得包含密钥值，只能记录路径和恢复步骤。
