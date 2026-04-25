# 公务员面试练习平台 - 前端

Vue 3 + Vite + Ant Design Vue 移动端面试练习应用

## 环境要求

- **Node.js** 18+
- **npm** 9+

## 快速启动

### 1. 克隆并安装依赖

```bash
git clone https://github.com/hyzcjlu/civil-interview-frontend.git
cd civil-interview-frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3001

### 3. 构建生产版本

```bash
npm run build
```

## 环境配置

- `.env.development` — 开发环境（API 代理到 localhost:8050）
- `.env.production` — 生产环境

## 配套后端

后端仓库：https://github.com/hyzcjlu/civil-interview-backend.git

需要先启动后端服务（端口 8050），前端通过 Vite 代理转发 `/api` 请求。

## 技术栈

- **框架**: Vue 3 + Composition API
- **构建**: Vite
- **UI**: Ant Design Vue
- **图表**: ECharts
- **路由**: Vue Router
- **状态**: Pinia
