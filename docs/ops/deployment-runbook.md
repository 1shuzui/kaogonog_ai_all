# 部署与同步手册

## 部署前检查

```bash
cd /home/quyu/kaogong_ai
git status --short
```

确认：

- 业务源码改动是预期的。
- `.env`、`*.pem`、`*.p12` 没有出现在 Git 待提交中。
- 小程序和 PC 构建脚本可运行。

## 构建

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build

cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm run build:mp-weixin:prod
```

## 同步服务器

```bash
cd /home/quyu/kaogong_ai

# 只同步前端和小程序
bash scripts/deploy_clean_to_server.sh

# 同步后端、前端和小程序
DEPLOY_BACKEND=1 bash scripts/deploy_clean_to_server.sh
```

## 部署后验证

- 访问生产首页：https://xzqianmianyuzhoukeji.com
- 检查后端健康接口或主要 API。
- 小程序开发者工具导入 `civil-interview-miniprogram/dist/build/mp-weixin-prod`。
- 验证登录、首页浏览、专项练习、全真模拟、套餐中心、订单中心、反馈入口。

## 回滚原则

- 先确认服务器部署脚本是否保留历史产物。
- 若是前端静态资源问题，优先重新构建并同步上一版静态产物。
- 若是后端问题，先看 systemd 日志和应用日志，再决定是否恢复上一版代码。
