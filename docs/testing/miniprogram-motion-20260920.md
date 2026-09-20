# 微信考生端轻量动效实现与验收（2026-09-20）

## 范围与实际环境

基于 `civil-interview-miniprogram` 现有 uni-app Vue 3 多页工程，参考用户提供的 SAVO 录屏交互，不复用其品牌、金融数据或加载等待。22 个考生页面接入统一反馈；5 个管理员页面不改。PC、后端、支付、登录授权、题源分类、录音提交与评分口径保持不变。

- 主工程 Vue 3.4.21、Pinia 2.1.7、Vite 5.2.8、DCloud `3.0.0-alpha-5000820260430001`（编译器输出 5.08），保留已有锁文件；未增加运行时依赖。
- 微信 WebView；没有启用 Skyline/worklet、GlassEasel 或浏览器 DOM 动效库。开发者工具实测基础库 3.17.2，iPhone 12/13 模拟布局 390×844 逻辑 px，底部安全区 34px。
- 工程 `project.config.json` 没有锁定最低基础库版本；本机私有配置选择 3.17.2。自定义 tabBar/getTabBar 本身要求基础库 2.6.2 起，这不是对整个应用最低兼容版本的承诺；发布前仍需核对微信后台最低版本设置。
- 检查了 `D:\前端素材积累\mini-program\uni-app` 的 Wot Design Uni **1.14.0** 实装源码。该试用工程 DCloud 为 `3.0.0-5020620260917001`，与主工程不同。参考其分层选择底板方式，主项目继续使用现有 Vue/原生组件，不引入整套库、Sass 或升级编译链。

## 实现与真实路径

| 区域 | 路径（均相对小程序目录） | 处理 |
| --- | --- | --- |
| 参数与开关 | `src/motion/tokens.json`、`policy.mjs`、`useMotion.js` | 标准/减弱/关闭；保存在本机，入口在“我的 → 考试设置 → 界面动效”。 |
| 胶囊导航 | `src/custom-tab-bar/`、`scripts/native-tab-bar.mjs`、`src/pages.json` | 原生 WXML/WXSS/JS/JSON，自定义 tabBar，仍用 switchTab；5 个路由来自同一 pages.json。 |
| 选择器 | `src/components/MotionSegmented.vue` | 等宽独立底板 transform，文字即时选中；首页趋势、错题收藏、准备页录制方式、动效设置复用。 |
| 展开收起 | `src/components/MotionPresence.vue`、`src/motion/presence.mjs` | 保留离场节点，退出时不可点击，编号丢弃旧完成回调；首页折叠区域、LightSelector 弹层复用。 |
| 滚动摘要 | `src/components/MotionSummary.vue`、`src/motion/useScrollSummary.js` | 首页 hero、结果页分数摘要；页面原生 onPageScroll 显式注册，整页滚动阈值切换。 |
| 局部装饰 | `src/components/MotionAccent.vue` | 首页话筒、训练页图标；页面显示、栏目激活、节点可见三条件控制；离屏暂停，卸载断开观察器。 |
| 全部考生页 | `src/styles/motion.css`、`src/pages/`（不含 admin） | 统一留白、边线、卡片、按钮按压和动效配置；保留各页业务结构。 |
| 构建守卫 | `scripts/validate-motion-assets.mjs` | 校验原生导航资源、路由一致、22 页根样式和真实 onPageScroll 编译标志，防止“编译通过但微信不显示”。 |

考生页清单：home/index、login/index、login/reset、jiangsu/job、bank/index、bank/detail、exam/prepare、exam/room、result/index、history/index、favorites/index、billing/orders、subscription/index、account/security、legal/index、support/index、targeted/index、targeted/focus、training/index、training/dimension、pricing/index、profile/index。

## 参数、生命周期与降级

- 按压 120ms，缩放 0.98；局部进入 200ms / 离场 140ms；分段底板 280ms；摘要 180ms；装饰循环 3600ms。
- 缓动 `cubic-bezier(0.22, 1, 0.36, 1)`；进入位移 6 **逻辑 px**。排版仍可用 rpx，测量、滚动、安全区与导航高度统一按逻辑 px，不混算。
- 导航高 60px、悬浮间距 12px、内容额外留白 20px。内容底部预留 `60 + 12 + 20 + safeBottom`；胶囊只占自己的点击区域，不放透明全屏遮罩。
- 跨 tab 不保留前页组件实例、不等待动画再跳转。当前页可有短选中反馈，新页面第一份可见底栏直接按实际路由落位；**不保证跨页面底板连续滑动**，不模拟从第 0 项滑入。未启用背景模糊，使用不依赖模糊的浅色底与细阴影。
- 导航队列区分实际路由、最新目标和请求编号，串行处理，A→B→A 保留最后的 A，失败按实际页面恢复；重复生命周期同步不重复导航。
- 摘要测量大卡片的文档位置，顶栏高 48px、回切区间 20px。只在状态改变时更新视图，不把每帧 scrollTop 写入 setData。较旧的测量回调不能覆盖新滚动事件；后台处理提示增减、结果变化、页面恢复、窗口变化都会重新校准。
- 顶栏位于现有系统导航栏下面，没有新增自定义状态栏，不占微信胶囊区域。考场是 scroll-view，保留原有题本/计时布局，不强套整页滚动摘要。
- 减弱模式取消位移、缩放和循环，关闭模式立即呈现最终态。观察器不可用时装饰静止。加载不隐藏导航、不人为延迟数据，不复现录屏中的空白等待。
- 准备页套卷请求增加最新请求编号：旧响应/旧错误不覆盖当前筛选、列表和 loading；退出页面使旧响应失效。

## 已执行检查

微信生产构建通过：

```bash
cd civil-interview-miniprogram
npm run build:mp-weixin:prod
```

针对性测试与已有业务回归：

```bash
node --experimental-vm-modules --test \
  civil-interview-frontend/tests/*.test.mjs \
  civil-interview-miniprogram/tests/*.test.mjs \
  civil-interview-miniprogram/tests/*.test.cjs
.venv/bin/python scripts/validate_project_docs.py
git diff --check
```

针对性测试与已有业务回归共 **76 项通过**（17 项新增、59 项既有）。新增测试覆盖：A→B→C / A→B→A / 重复点击 / 导航失败及旧回调、过渡快速反转与关闭、缺失安全区、滚动回切区间、旧布局测量、筛选请求乱序、原生 JSON 模块接入错误、漏注册 onPageScroll、丢失 WXSS 或路由漂移。完整日志与机器报告随 Windows 交付目录提供。

开发者工具 **8 组动效验收通过**：5 tab 直接进入与缓存返回，快速导航、失败注入后恢复、非 tab 返回；分段切换和标准/减弱/关闭；首页摘要临界值往返、离屏图标暂停/回到可见恢复；“我的”末项可滚到胶囊上方。失败注入仅在本机短时替换导航函数，结束恢复，不触发订单、考试提交或外部评分。

核心界面另检查了首页、准备页、江苏 5+15 阅读阶段与答题阶段四个实际渲染状态：图标入口、模式/录制方式切换、题本、计时器与录音按钮布局均可见，底部操作保持同一行。考场仅使用明确标记的本机界面样例，未启动麦克风、创建考试、提交答案或调用评分，结束恢复 store。当前预览为游客会话，**结果页受登录保护，本轮未完成已登录结果页的界面与滚动摘要验收**，没有注入令牌或绕过授权；不将既有测试当作本轮真机验证。

交付包含导航切换、分段切换、滚动摘要三个约 7.5 秒的开发者工具窗口录屏。录屏按实际捕获间隔编码，仅展示交互，不是帧率或 iOS/Android 真机性能证明。独立代码复查未发现未处理的本轮问题。

过程中修复了两个仅靠 JS 构建发现不了的问题：微信原生 require 不支持把 JSON 当模块加载；本版本 uni-app 的 onPageScroll 必须在页面 SFC 显式注册。构建守卫已覆盖二者。复制多文件产物后必须在开发者工具完整“编译”（Ctrl+B），不以热重载混合了新旧模块的状态验收。

## 人工复现与未验证范围

1. 打开交付的 `mp-weixin-prod`，完整编译，依次直达首页、定向、题库、训练、我的；快速点首页→定向→题库、首页→定向→首页，重复点当前项。选中项应始终回到实际页面。
2. 首页滚到“成绩趋势”，快速切换分段；准备页切换仅录音/录像，错题本切换分组。底板应及时转向，文字不抖动。
3. 首页向下滚过 hero 底部，再在临界值附近小幅往返；结果页有评分时同样检查。紧凑条与展开态之间应有回切区间，不频闪；回顶部可恢复。
4. 首页展开/收起趋势或薄弱分析时快速反向，定向/准备页打开和关闭筛选弹层。离场期间不要出现透明层长期挡住后续按钮。
5. “我的”分别选择减弱、关闭，再检查首页装饰、按压、摘要；回到标准。滚到底部，最后一项和导航分别可点。
6. 在 iOS、Android 微信真机分别前后台切换、横竖屏/字体变化、弱网加载、持续滚动；检查有/无底部安全区与较窄屏。

本次开发者工具结果**不代表 iOS/Android 真机验收**，没有声明恒定 60fps。真机手感、耗电、系统前后台与所有机型/字号组合仍需设备复核。录音转写/模型速度不是动效测试的结论；本次不改 `LOCAL_REFERENCE_SCORING=false`，不为控制费用减少点评质量或增加前台等待。

## 发布边界

本轮仅部署经过测试的小程序编译产物；服务器备份上一版本并核验逐文件校验和，不重启或更新 PC/后端，不动数据库。Windows 输出包含源码归档、编译目录、验证报告和操作说明，不包含真实环境变量、密钥、用户数据或第三方依赖目录。**同步服务器上的小程序产物不等于发布微信线上版本**；微信上传/审核/发布按项目原流程单独执行。

原始依据：[uni-app pages/tabBar 配置](https://uniapp.dcloud.net.cn/collocation/pages.html)、[uni-app 相交观察器](https://uniapp.dcloud.net.cn/api/ui/intersection-observer.html)、[微信 getTabBar 类型与版本说明](https://github.com/wechat-miniprogram/api-typings/blob/master/types/wx/lib.wx.component.d.ts)。同时直接核对了项目安装版本的 uni-app 编译器/运行时与素材工作区 Wot 1.14.0 源码。
