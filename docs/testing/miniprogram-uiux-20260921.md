# 微信考生端 UI/UX 修复与验收（2026-09-21）

## 基线、范围与技术路线

基线为 master `f940e4a`，开工时源码工作区干净，Windows 运行包 REVISION 一致。依据 2026-09-20 UI/UX 评估，正式修改 `civil-interview-miniprogram/src`，不把生成目录作为源码入口。

工程是普通 uni-app、Vue 3.4.21、Pinia 2.1.7、Vite 5.2.8；DCloud 锁定 `3.0.0-alpha-5000820260430001`（编译器 5.08）。微信 WebView、原生页面滚动、五个独立 tab 页及 custom-tab-bar；选择弹层内部使用 scroll-view。开发者工具本轮基础库 3.17.2；工程没有声明最低基础库，本次不据此承诺低版本兼容。

已阅读素材库整体报告，检查 Wot Design Uni 1.14.0 的 Root Portal / Popup；试用工程编译链与业务不同。既有组件能够修复，因此使用微信 root-portal + 原有 MotionPresence，H5 分支用 Teleport；未引入 Wot、Lottie 或新动画运行时，未升级依赖、启用 Skyline、改成单页或加入左右滑动切页。图标继续使用本地 Ant Design Icons 及既有 MIT 授权。

## 确认的根因与修改

### 选择弹层

- 年份弹层嵌套在带 transform 的 card 内，固定定位受包含块约束。旧版实际测量：390×753px 内容视口，遮罩仅 350×573.59px，位于 left=20、top=153.30；“完成”24×16px，加减39×35px。
- `LearnerSheet.vue` 将视觉层放到 root-portal，Vue 保留状态所有权。新遮罩为390×753px、原点(0,0)；完成按钮60×44px，加减44×44px。滚动后年份遮罩仍覆盖整个内容视口。使用显式四边定位；没有大范围删除 card transform。
- 原生 custom-tab-bar 与页面是不同层级，根层弹窗仍不能靠页面 z-index 遮住它。实际截图发现底栏浮在选择器上后，新增 `sheetNavigation.mjs`：仅在模态选择期间持有所属页的计数，隐藏底栏并阻止 select；关闭、隐藏或卸载释放，多个弹层独立计数，迟到的组件 ready 读取当前页状态。没有缓存跨页 tabBar 引用，原路由队列不变。
- 遮罩可关闭，内容区独立滚动；关闭/选项/小链接至少44px，行选项48px；安全区只由面板计算一次。MotionPresence 层级动画仅透明度，避免位移露出可点击边缘。离场节点按既有 presence 状态机清理。

### 页面与数据

| 位置 | 实现与保留项 |
| --- | --- |
| 首页 `pages/home/index.vue` | 收短标题，回访用户的近期复盘前置；江苏岗位收成紧凑可展开入口。游客有明确浏览和试用路径，避免重复空图表。多栏同时展开、持久化及原滚动摘要保留。首页文案为“自选题型与题数”，不暗示默认只有一题。 |
| 准备 `pages/exam/prepare.vue` | 默认仍5题、试用仍1题、全真仍按完整套题；模式/题量/录制优先，高级条件折叠，全真模式自动展开套卷。固定底部摘要与“进入考场”，最后提示预留可滚动空间；时间、媒体、服务和权益校验不变。 |
| 题库 `pages/bank/index.vue` | 常用条件前置，其余放“更多筛选”；用真实分类名和选项代替三级/四级自由输入。显示已应用条件、未提交关键词、清空及准确空态。年份草稿仅完成/遮罩关闭时一次应用。管理员导入、编辑、复核、删除等处理函数保留。 |
| 定向/我的 | 定向年份使用真实题库数据并明确“全题库年份、具体方向以分析为准”；分析任务和取消/失败恢复不变。“我的”选择器统一外观，保留原保存事件契约，不代替用户修改偏好。 |
| 登录 `pages/login/index.vue` | 微信登录作为主入口；PC已有账号密码、可选邀请码按需展开。协议未被自动确认，隐私授权、关联、补全、先浏览逻辑保留。 |
| 训练 `pages/training/index.vue` | emoji 替换为本地同家族图标；辅助文字14px、按钮至少44px，训练路由和成绩记录不变。 |
| 结果 `pages/result/index.vue` | 分数后展示最多3条已有模型建议，再给下一步动作；完整原文、题干、评分口径和长点评放入现有实测高度折叠。无模型依据不生成诊断。未评分保持待点评，真实0分保留；背景更新按题目ID保持阅读位置。 |

共享 `styles/tokens.css` 统一背景、主/次文字、交互蓝、错误色、边界和触控尺寸；`learner.css`、`motion.css` 和相关 scoped 样式消费这些语义。普通小字用 #596A80 / #285BC7 等高对比颜色，至少14逻辑px，不把28rpx误当成任何屏幕都为14px。保留中文系统字体、蓝白视觉和既有 full/reduced/off 模式。

### 元数据接口与旧请求隔离

新增只读 `GET /questions/filter-options`，用户已明确同意一并更新服务器。它与题库列表共用登录和权益校验；只返回年份/分类字符串、题目计数与无年份计数，不返回题干、答案、个人数据或评分。读取真实 `questions.keywords._meta`，复用年份解析和分类匹配规则；未知年份不填当前年，不造2017–2025静态列表，不改数据库或题库。

分类按父级筛选级联，年份排除自身选择；年份无题/未标注/失败有不同反馈。准备页元数据与实际抽题使用相同的生效题型和省份 fallback。沿用后端精确筛选语义，未把 `dimension` 的逗号组合擅自扩成 OR；旧接口在此组合下可能无题，这是已有抽题限制，不宣称本次修复了它。

`useQuestionFilters` 不跨账号缓存，以递增任务号隔离旧成功/错误/finally，取消只释放自己的请求。题库 store 同样用不会因 reset 归零的序号防止 ABA 覆盖；失败保留旧题目并明确标注，当前选择与已应用条件不混淆。

独立审查复现的“首次 onShow 请求 A 未回，新筛选 B 已成功但页面仍 loading”已修复：pageLoading 只负责初始化，列表与选项由各自最新任务管理。新增真实页面+Pinia组合测试证明旧 A 悬挂、后续成功或失败都不锁住 B 的分页。

结果页读取和重试也带任务归属校验，旧成功/错误/finally 不修改新任务；离页停止前端等待，保留后台答案处理。完整原文不因包含转写提示词而被误删。仍使用原评分公式、95+5及整套仪态分规则。

## 折叠、加载与动效边界

沿用上一轮 `MotionCollapse` 的真实 px 高度过渡：高度280ms、内容进入200ms/退出140ms、位移4px、箭头200ms；完成后展开恢复 auto，收起再卸载。保留快速反向、异步重测、页面隐藏、旧结束回调隔离及 reduced/off。没有新增滚动补偿器、逐帧 setData、虚假进度或强制延迟。

原位分析保持 idle/loading/success/error/timeout/cancelled、10s慢提示与30s截止；“停止等待”仅停止前端等待，不承诺终止服务器任务。等待中仅去重分析按钮，正常非模态导航保持可用。扫描与装饰循环继续按页面/视口可见性暂停。

## 已执行验证

```bash
node --experimental-vm-modules --test \
  civil-interview-frontend/tests/*.test.mjs \
  civil-interview-miniprogram/tests/*.test.mjs \
  civil-interview-miniprogram/tests/*.test.cjs
cd civil-interview-backend
../.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_question_filter_options.py \
  tests/test_question_service_jiangsu.py tests/test_question_service_anhui.py \
  tests/test_medical_question_bank_assets.py \
  tests/test_acceptance_practice_flow.py::test_random_inherits_exact_bank_filters_without_empty_result_fallback
cd ../civil-interview-miniprogram
npm run build:mp-weixin:prod
cd ..
.venv/bin/python scripts/validate_project_docs.py
git diff --check
```

客户端最终回归183项通过、0失败/跳过；后端元数据28项及相关题库8项，共36项通过。测试覆盖游客/普通考生/管理员界面分支、登录协议、真实筛选值、元数据取消和失败、题库请求竞态、结果原文和切题、后台提交、计时、旧响应隔离、导航快速反向、折叠和动效开关。元数据授权401/403和无答案字段泄露在 API 专测覆盖。

生产构建成功，校验47个JSON、4套考生主题、16个独立图标。文档和diff检查通过。项目没有独立 lint/typecheck 脚本，不虚构这些执行记录。

开发者工具实际打开首页、定向、题库、训练、我的、准备、登录；使用现有管理员会话，未读取/注入 token，未提交考试、支付、导入或偏好保存。390×753px 内容视口、底部安全区34px：

- 定向嵌套选择器及准备年份遮罩覆盖整个页面，关闭后恢复底栏；滚动后同样成立。
- 准备页CTA top=621px、高132px，首屏可见；末尾提示滚动后 bottom=555.25px，小于CTA top。
- 训练最后一项 bottom=626.95px，小于悬浮胶囊 top=647px。
- 微信登录主按钮高44px，PC密码区可以展开；未提交登录。
- 打开现有真实历史记录，分数后为下一步动作；详情开关49.59px，展开后真实原文容器559.55px。未注入答案、未重新评分。结果页没有运行异常。
- 首页底部收起实测内容高度627.25→130.89→16.39→0.58→0px；页面总高度与原生滚动同步收敛，最终scrollTop=1308px处于合法范围；快速开→关→开成功，没有增加主动滚动补偿。
- 最终页面测量与截图保存在 Windows 交付中的 `verification` 与 `evidence`。截图缩放受当前开发者工具显示比例影响，布局数值来自原生节点测量，不用缩略图像素代替逻辑px。

## 未覆盖与复现

原生角色检查使用现有管理员会话；游客和普通考生用真实 Vue 模板/脚本 fixture 验证，不能冒充两个新账号的真机登录。原生实际视口为390px；320/375/414px、系统字体放大、iOS/Android真机、低基础库和真实手势滚动/键盘遮挡未在本轮全部验证。桌面操作工具返回跨盘锁错误，未为绕过它修改系统或伪造设备宽度。没有恒定60fps或全机型通过的结论。

人工复核：导入交付 `mp-weixin-prod` 并完整编译；依次以游客/普通付费账号/管理员进入八个核心页面。准备页展开条件后打开年份，滚动前后检查四边遮罩、关闭、快速重复开关；定向和我的选择器做同样检查，长选项在弹层内部滚动，背景不得跟随。选择无题条件及断网验证准确空态/重试，旧输入不丢失。首页多栏开关并在底部收起，结果切题及后台完成后仍保留当前题。用不同设备宽度/大字体检查长中文、44px控件、键盘与末项安全区；等待分析时可切换底栏，只有真正打开的模态选择器临时隐藏导航。

## 发布与回退

按功能分段提交到 master，提交附 Codex 协作署名。后端沿用 `scripts/deploy_verified_release.sh` 的临时快照、Pyarmor保护产物、预检/备份/激活，不直接覆盖加密路由为明文；大文件 question_service 保持原发布流程的明文例外。仅激活 backend 阶段，PC前端不激活。不迁移数据库、不更改真实密钥、题库、计费或外部模型配置；`LOCAL_REFERENCE_SCORING=false` 仍需部署预检确认。

小程序生成包单独同步服务器与 Windows；保留上一个包及 REVISION，按SHA-256核对。最终版本、实际服务器状态、健康检查、授权元数据响应和产物校验写入 Windows `release-info.json`、部署日志及交付说明；以这些执行记录判断是否已同步，不能只凭此计划性描述声称部署成功。

微信平台上传、体验版、审核和正式发布不自动执行。若需回退，恢复对应后端代码备份并重启验证健康；小程序恢复旧包重新按微信流程上传。此次无数据库迁移，不回退数据库。PC版本保持不变。
