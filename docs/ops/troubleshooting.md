# 常见故障排查

## 后端无法启动

1. 检查 `.env` 是否已恢复。
2. 检查 MySQL、Redis 是否可连接。
3. 运行：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
python database_setup.py --check
uvicorn main:app --reload --port 8050
```

## 小程序无法支付

1. 确认后端和小程序 `.env` 已恢复。
2. 确认微信虚拟支付道具映射和现网环境一致。
3. 查看后端订单表 `payment_orders.extra_payload` 是否记录 `openId` 和 `virtualProductId`。
4. 查看 `callback_payload` 中的查单结果和错误。

## ASR 文字稿异常

1. 确认 `ASR_PROVIDER=funasr_onnx` 或当前配置符合预期。
2. 确认模型缓存目录存在：`civil-interview-backend/storage/modelscope_cache/`。
3. 运行相关测试：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest tests/test_funasr_asr.py
```

## 题库年份或套题检索异常

1. 查看题目 JSON 或数据库 `questions.keywords._meta.year`、`examDate`、`suiteName`。
2. 查看 `data/question-bank/inventory.json` 找到原始源文档。
3. 重新运行题库导入或同步脚本前，先备份当前题库资产和数据库。
