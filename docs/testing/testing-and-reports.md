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

## 报告归档

外部归档清单：

- `/home/quyu/doc_kaogong/reports/archive/`
- `/home/quyu/doc_kaogong/manifests/migration-moved-checksums.tsv`

恢复旧报告时，先按 hash 校验，再复制回 `reports/` 对应目录。
