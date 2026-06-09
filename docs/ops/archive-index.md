# 归档索引

- 外部归档根目录：`/home/quyu/doc_kaogong`
- 迁移文件数：`146`
- 校验清单：`/home/quyu/doc_kaogong/manifests/migration-moved-checksums.tsv`

## 分类统计

- `guidance`：15 个文件
- `old-report`：87 个文件
- `question-bank-report`：1 个文件
- `question-bank-source`：14 个文件
- `root-duplicate`：19 个文件
- `secret`：9 个文件
- `secret-backup`：1 个文件

## 主要归档位置

- 敏感配置与证书：`/home/quyu/doc_kaogong/doc_secret/`
- 题库源文档：`/home/quyu/doc_kaogong/question-bank/`
- 修改指导资料：`/home/quyu/doc_kaogong/guidance/`
- 旧报告：`/home/quyu/doc_kaogong/reports/archive/`
- 根目录重复/散落资料：`/home/quyu/doc_kaogong/root-duplicates/`

## 恢复原则

- 需要恢复单个文件时，先按 `migration-moved-checksums.tsv` 校验 hash，再复制回原路径。
- 敏感文件不要提交到 Git；恢复后仍应保持被 `.gitignore` 覆盖。

## 明细文件

- 迁移计划：`/home/quyu/doc_kaogong/manifests/migration-plan.json`
- 实际移动结果：`/home/quyu/doc_kaogong/manifests/migration-moved.json`
- hash 校验表：`/home/quyu/doc_kaogong/manifests/migration-moved-checksums.tsv`
- 整理前 Git 状态：`/home/quyu/doc_kaogong/preflight/git-status-before.txt`
- 整理前源码脏改动备份：`/home/quyu/doc_kaogong/preflight/source-dirty-diff-before.patch`
