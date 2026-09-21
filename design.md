# 考生端设计规范：轻快练习工作台

状态：2026-09-19，用户确认核心考生页范围，并选择“更年轻、活泼”。

## 目的与边界

这是已有产品的功能界面，不是营销落地页。首页帮助开始练习；准备页确认媒体和规则；考场突出题本、倒计时和录音；结果页分开原文与点评。管理员页面、付款流程、权限逻辑、题库分数与江苏 5+15 规则不因视觉改版改变。文字作答入口保持关闭。

## 已锁定的视觉系统

- 结构：Workbench 的功能工作台变体，左侧阅读、右侧录音控制；窄屏上下排列。现有导航结构沿用，不为了样式变更增加导航层级。顶部导航采用已有的品牌／入口／账户三段式，微信保留原生底栏；考场使用 C4 底部操作栏，不新增营销页脚。
- 主题：现有品牌蓝的年轻化变体，明亮、友好、轻快、可专注。首次 Hallmark 改版，未发现历史风格记录。
- 颜色：纸面 `#F7F9FD`，内容面 `#FDFEFE`，主文字 `#203047`，次文字 `#596A80`，边界 `#DBE3EE`，操作蓝 `#326BE5`，蓝浅底 `#EDF3FF`；青绿 `#147D74` / `#EAF8F3` 用于录音与完成；暖色 `#A94B2B` / `#FFF1E8` 用于提示。颜色按用途命名，禁止临时堆叠渐变、光晕和多层卡片。
- 字体：中文正文优先 PingFang SC / Microsoft YaHei；标题使用同一中文系统字族的 700 字重，正文 400。为中文可读性与国内加载稳定性，明确不用西文营销字体配对或外部字体 CDN。Pencil 使用可用的 Noto Sans SC 对照排版。
- 字阶：标题 32/24/20px，正文 16px，辅助信息 14px；微信按 2rpx≈1px 换算，正文 28–32rpx。长题干行高 1.8，完整阅读优先，不用截断隐藏关键答案。
- 小屏下限：2rpx≈1px 只适用于375px宽视口。2026-09-21起，考生端小字至少14逻辑px、主要触控至少44逻辑px；不以28rpx/88rpx代替跨宽度硬下限。
- 间距：4/8/12/16/24/32/48px。内容面圆角 12px、主按钮 12px、状态签圆角 999px。只有真正的功能区才使用卡片。
- 图标：Ant Design Icons，本项目已使用同一图标家族。精选麦克风、录像、题本、计时、目标、记录、复盘、上传、重试等语义图标；微信使用本地图标文件。图标旁保留操作文字，不使用 emoji 代替图标。
- 动效：120ms 按下反馈、220ms 题目/区域进入、后台状态轻量淡入；每页不超过三种动效。只动 transform/opacity，尊重 prefers-reduced-motion，不延迟作答和换题。

## 文件范围

修改：

- civil-interview-frontend/src/views/Home/HomePage.vue
- civil-interview-frontend/src/views/Exam/ExamPrepare.vue
- civil-interview-frontend/src/components/exam/StandardExamRoom.vue
- civil-interview-frontend/src/components/exam/FullExamRoom.vue
- civil-interview-frontend/src/views/Result/ResultPage.vue
- civil-interview-miniprogram/src/pages/home/index.vue
- civil-interview-miniprogram/src/pages/exam/prepare.vue
- civil-interview-miniprogram/src/pages/exam/room.vue
- civil-interview-miniprogram/src/pages/result/index.vue
- 两端录音操作栏及后台任务状态组件。

新增：两端 learner 专用样式、微信图标组件、本地精选图标及授权说明、可编辑 Pencil 设计稿与预览。无删除文件。

## 状态与验收

1. 主操作点击后立即反馈；停止本机录音的短等待单独冻结，上传、转写、点评不锁住下一题。
2. 未取得有效评分时显示待点评，不伪造 0 分。后台状态准确区分本机暂存／上传／转写／点评／失败。
3. 上一题回调不能更新下一题输入；结果更新不抢走正在查看的题目。
4. 长题干、中文按钮、320/375/414/768px 布局需检查；触控按钮至少 44px，键盘焦点明显。
5. .pen 保留组件、文字和布局图层；示例分数与题目明确为设计演示，不冒充线上实测成绩。
6. 运行中的客户端队列允许站内换页；刷新浏览器、清理小程序或退出账号仍会中断未完成的客户端任务。处理期间明确提醒，失败录音/原文保留供本次会话重试；不得声称已具备跨重启持久后台队列。

对比度复核：正文/内容面 13.19:1，次文字/纸面 5.25:1，按钮白字/操作蓝 4.76:1，青绿/青绿浅底 4.56:1。小字号蓝字在浅蓝底使用 `#285BC7`；警示文字改为 `#A94B2B`，避免浅色提示面的对比不足。卡片与题本分区是功能分组，不额外增加营销页结构；中文系统字体、原生微信导航按项目约束保留。

素材来源：[Ant Design Icons 官方仓库](https://github.com/ant-design/ant-design-icons)，MIT；[图标文档](https://ant.design/components/icon/)。

## 公开素材选型（2026-09-19）

按用户要求使用 AnySearch 检索 Ant Design Icons、IconPark、Lucide 及阶段进度组件。采用 Ant Design Icons，原因是与 PC 已安装组件一致、SVG 可离线随包使用、授权明确，无需额外图片 CDN 或新运行依赖。备选公开库：[IconPark](https://github.com/bytedance/IconPark)、[Lucide](https://lucide.dev/license)，本轮未引入其资源，避免混用图标风格。

两端后台状态组件使用真实的上传、转写、点评阶段，不显示估算百分比；错误按已确认上传和已有原文定位可重试步骤。Pencil 中包含独立可编辑图标路径、录音状态、处理状态与主按钮组件。修改设计稿时必须保留路径几何数据，防止只剩文字和空容器。

## 微信 UI/UX 校准（2026-09-21）

此次只更新微信核心考生页，不改PC或管理员业务。共享语义以 `civil-interview-miniprogram/src/styles/tokens.css` 为准；交互小字使用 `#285BC7`，错误 `#A52C38`，辅助文字 `#596A80`。选择弹层使用 LearnerSheet + root-portal，不放在 transform 卡片包含块内；原生底栏在模态期间按所属页计数隐藏，关闭后恢复。

首页顶部主练习入口之后紧接“全真练习 / 套餐中心”，再展示近期复盘；准备先模式/录制/真实摘要，常驻底部开始入口；题库常用条件前置、更多条件折叠；结果先真实分数与已有建议，完整原文可展开；微信登录主入口、PC已有账号次入口。没有新增虚构学习数据或一题默认规则，默认仍5题。保留既有280ms实测高度折叠，不以 scaleY 代替布局过渡；reduced/off 立即收敛。完整验证与限制见 [UI/UX 修复记录](docs/testing/miniprogram-uiux-20260921.md)。
