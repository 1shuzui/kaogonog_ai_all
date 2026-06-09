# 本地开发与运行

## 前置步骤

真实 `.env` 和支付证书已经移出仓库。需要本地运行时，先按 [密钥与本地配置恢复](secrets-and-local-config.md) 复制回原路径。

## 后端

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8050
```

常用检查：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
pytest
python database_setup.py --check
```

## PC 前端

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm install
npm run dev
```

构建：

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build
```

## 小程序

```bash
cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm install
npm run dev:mp-weixin
```

生产构建：

```bash
cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm run build:mp-weixin:prod
```

## 常见本地问题

- 后端启动报缺少数据库或 Redis 配置：先恢复 `civil-interview-backend/.env`。
- 微信虚拟支付无法调起：确认小程序端 `.env`、后端 `.env`、支付证书和微信现网配置均已恢复。
- FunASR 首次转写慢：模型可能需要下载或读取 `civil-interview-backend/storage/modelscope_cache/`。
- 小程序构建后体积变化：`dist/` 是构建产物，按需重建，不作为源码修改依据。
