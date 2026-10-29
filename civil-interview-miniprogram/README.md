# 公考面试AI测评 uni-app 小程序端

这是现有 `civil-interview-frontend` 的并行小程序前端，基于 uni-app + Vue 3 构建。网页端目录保持不变，小程序端默认复用 `civil-interview-backend` 的业务 API。

## 开发（本机）

```bash
cd civil-interview-miniprogram
npm install
cp .env.example .env
npm run dev:mp-weixin
```

将 `unpackage/dist/dev/mp-weixin` 导入微信开发者工具即可预览。

默认小程序开发 API 地址为 `https://xzqianmianyuzhoukeji.com/api`。  
如需临时切换到其他后端，请改 `VITE_API_BASE_MP_WEIXIN` 为可访问地址，例如：

```env
VITE_API_BASE_MP_WEIXIN=https://xzqianmianyuzhoukeji.com/api
```

开发构建（development）：

```bash
npm run build:mp-weixin:dev
```

然后把 `dist/build/mp-weixin` 导入微信开发者工具。不要导入 `civil-interview-miniprogram` 源码目录，否则微信工具会提示根目录找不到 `app.json`。

## 生产构建（服务器）

生产构建会读取 `.env.production`：

```bash
npm run build:mp-weixin:prod
```

生产构建产物目录固定为：

```text
dist/build/mp-weixin-prod
```

当前默认小程序生产 API：

```env
VITE_API_BASE_MP_WEIXIN=https://xzqianmianyuzhoukeji.com/api
```

微信构建统一输出ES2018语法，并在构建末尾解析所有JavaScript产物；原生导航文件也经过转换。保持微信 `es6=false`，不通过切换开发者工具转译开关掩盖上传错误。错误复现、修复和预览验证见[本轮交付记录](../docs/implementation/wechat-upload-compatibility-20261026.md)。

## 微信小程序配置要点

1. 小程序端请求地址必须是完整 URL（不能只写 `/api`）。
2. 真机调试/线上版要求 `https`，并在小程序后台配置 request 合法域名。
3. 开发者工具本地调试可临时关闭 URL 校验（本项目 `project.config.json` 已 `urlCheck: false`），但这不等于真机可用。
4. 若要临时覆盖 API 地址（不改代码），可在控制台执行：

```js
uni.setStorageSync('civil_runtime_api_base', 'http://可访问地址:8050')
```

重启小程序后生效。

## 按需注入与用时注入

已按微信官方文档启用按需注入配置：

```json
"lazyCodeLoading": "requiredComponents"
```

说明：
- 该配置可减少启动注入代码量，优化启动速度和内存占用。
- 若要继续用「用时注入」，需要为重量级自定义组件配置占位组件（placeholder），让组件在真正渲染时再注入。

## 页面覆盖

- 登录 / 注册
- 首页数据概览
- 题库列表与题目详情
- 模考准备、录音 / 文本作答、评分结果
- 历史记录
- 定向备面与方向弱点分析，默认新题练习，可切换低分重练
- 专项训练
- 套餐演示与个人中心
