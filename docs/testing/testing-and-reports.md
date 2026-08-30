# 测试与报告说明

## 保留策略

`reports/` 只保留每类最近 3 份关键结果；旧报告已迁到 `/home/quyu/doc_kaogong/reports/archive/`。

当前一线报告：

- `reports/asr/`：ASR 基准报告。
- `reports/question_sampling/`：题库评分抽样报告。
- `reports/regression/`：评分回归报告。
- `reports/question_inventory.*`：题库库存报告。

## 常用测试命令

```bash
# 后端单元测试
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest

# FunASR 相关测试
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest tests/test_funasr_asr.py tests/test_asr_cache.py

# PC 构建
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build

# 小程序生产构建
cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm run build:mp-weixin:prod
```

## 题库与文档验收

医疗卫生题库、导入器、套题或仪态分变更后，除常规后端测试外至少执行：

```bash
cd /home/quyu/kaogong_ai
sha256sum -c data/question-bank/checksums.sha256 --ignore-missing
PYTHONPATH=ai_gongwu_backend .venv/bin/python -m pytest -q \
  ai_gongwu_backend/tests/test_medical_question_bank.py

cd civil-interview-backend
pytest -q tests/test_medical_question_bank_assets.py \
  tests/test_scoring_appearance_score.py

cd /home/quyu/kaogong_ai
.venv/bin/python scripts/validate_project_docs.py
git diff --check
```

三批题库的数量、文件级套题规则、江苏第 39/45 套和默认/实际仪态分替换均由上述测试覆盖。完整运行顺序见 [题库导入、重建与验收](../ops/question-bank-maintenance.md)。

## 报告归档

外部归档清单：

- `/home/quyu/doc_kaogong/reports/archive/`
- `/home/quyu/doc_kaogong/manifests/migration-moved-checksums.tsv`

恢复旧报告时，先按 hash 校验，再复制回 `reports/` 对应目录。
