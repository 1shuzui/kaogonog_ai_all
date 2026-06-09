# ADR-002: 题库源文档外置归档

## Status
Accepted

## Date
2026-06-09

## Context

题库原始 Word/doc、抽取文本和 normalized 文本体积较大，且主要用于导入追溯，不是运行时直接读取的资产。运行链路依赖的是 `ai_gongwu_backend/assets/questions/` 中的 JSON 题库资产。

## Decision

- 将题库源文档迁到 `/home/quyu/doc_kaogong/question-bank/`。
- 仓库内保留 `data/question-bank/inventory.json` 和 `checksums.sha256`。
- 导入模板继续留在仓库的 `data/question-bank/templates/`。

## Consequences

- Git 仓库减少大文件和重复文本。
- 需要追溯原文时按索引恢复。
- 新增题库源文档默认不入 Git，先进入外部归档并更新索引。
