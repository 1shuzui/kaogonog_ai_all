# 公考面试AI测评 uni-app 小程序端

这是现有 `civil-interview-frontend` 的并行小程序前端，基于 uni-app + Vue 3 构建。网页端目录保持不变，小程序端默认复用 `civil-interview-backend` 的业务 API。

## 开发

```bash
cd civil-interview-miniprogram
npm install
cp .env.example .env
npm run dev:mp-weixin
```

将 `unpackage/dist/dev/mp-weixin` 导入微信开发者工具即可预览。

默认 API 地址为 `http://127.0.0.1:8050`，真机调试时请在 `.env` 中将 `VITE_API_BASE` 改成可被手机访问的后端地址，并在微信开发者工具中配置请求合法域名。

## 页面覆盖

- 登录 / 注册
- 首页数据概览
- 题库列表与题目详情
- 模考准备、录音 / 文本作答、评分结果
- 历史记录
- 定向备面与重点分析
- 专项训练
- 套餐演示与个人中心
