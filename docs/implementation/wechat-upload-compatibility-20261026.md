# 方向弱点功能、复习题干与微信上传兼容修复（2026-10-26）

本次按已确认方案保留“分析方向弱点”：按所选方向的本人已保存成绩判断题型表现，默认练同方向、同题型新题，保留“重练低分题”切换。错题本和收藏夹共用页面的题干改为正常字重；同时修复微信上传阶段的 JavaScript 解析失败。

## 功能和提交范围

- [分析规则](../../civil-interview-backend/app/services/targeted_performance_rules.py)：近30个北京时间自然日、每题型至少5道不同题、低于60%优先提升、60%至不足80%需巩固、80%及以上较擅长。同题取期内最近有效成绩等权统计；真实零分有效，待点评或失败不算零分；不读取错题本个人低分线。
- [预选与开考复核](../../civil-interview-backend/app/services/targeted_practice_service.py)：默认同方向、同题型新题3道，可选1/3/5道；按全历史实际提交排除新题，允许主动切换低分重练。少题返回实际题量，耗尽禁止开考，不跨范围补题或随机替换固定ID。
- [练法选择](../../civil-interview-miniprogram/src/components/TargetedPracticePicker.vue)与[结果操作](../../civil-interview-miniprogram/src/components/TargetedResultActions.vue)：透传完整范围、年份和计时，练后返回原分析周期与阅读位置并刷新保存的成绩；继续练习默认新题。
- Git提交在隔离工作树逐块整理，仅纳入上述功能、其范围与导航依赖、本次题干样式和上传修复。原工作区的评分实验、任务迁移及其他未提交内容保留，不纳入本次提交。该分支不是本机所有源码的完整快照，也不表示生产已启用这些其他改动。

## 上传错误与修复

旧固定导入包经微信开发者工具 `preview` 实际复现 `invalid file: api/request.js, 1:972 SyntaxError: Unexpected token ?`。该处为 `??`；模拟器能运行，不代表微信上传解析器接受同一语法。旧包按ES2018检查有43个JavaScript文件超出该目标。

1. [Vite配置](../../civil-interview-miniprogram/vite.config.js)仅在微信构建设置 `target=es2018` 和对应压缩语法目标，统一转换现代语法，保留微信 `es6=false`，避免重新引入原生导航的二次转换问题。
2. [原生导航构建插件](../../civil-interview-miniprogram/scripts/native-tab-bar.mjs)转换直接输出的原生JS。uni-app在`writeBundle`阶段还会复制原始`custom-tab-bar/index.js`，因此在该复制完成后写回已转换产物。
3. [构建校验](../../civil-interview-miniprogram/scripts/validate-wechat-javascript.mjs)使用固定开发依赖Acorn解析所有生成的`.js`，与JSON、主题、图标检查一起阻止不兼容产物交付。新增回归先复现原生语法与复制覆盖错误，修复后通过。
4. [错题与收藏页](../../civil-interview-miniprogram/src/pages/favorites/index.vue)仅将题干的 `font-weight` 从800改为400；两个标签共享这一样式。

转换目标的语义见[esbuild官方说明](https://esbuild.github.io/api/#target)，输出钩子顺序见[Rollup官方说明](https://rollupjs.org/plugin-development/#writebundle)。

## 本轮验证与交付

- 当前完整源码客户端266项测试通过；现网同步流程兼容候选259项通过。隔离提交分支独立验证185项客户端测试与22项定向后端测试通过，包含实际ID、完整范围、零准备时间和练习上下文透传。
- 兼容生产包构建通过，60个JSON、123个JavaScript、4类主题与18个图标校验通过。隔离提交分支也独立构建通过，其基线资源为50个JSON、107个JavaScript和16个图标；不混报两个构建范围。
- 微信开发者工具实测“低分题”“收藏题”切换，各自题目实际计算字重均为400；采集到的页面异常和console error为0。使用合成复盘数据与请求替身，存储写入被抑制，没有写生产业务数据或调用模型；不是手机实机验收。
- 修复后候选与实际固定目录均由微信开发者工具成功生成预览包，平台返回932076字节，原语法错误未再出现。预览成功不等于提交审核或正式发布。
- Windows固定导入目录：`D:\项目\考公项目\mp-weixin-prod`；版本 `wechat-upload-fix-20261027T042834Z`。版本号使用UTC，实施日期按当前用户时区为10月26日。330个清单文件已逐一核对SHA-256。
- 原固定包完整备份：`D:\项目\考公项目\backups\wechat-upload-fix-20261027T042834Z\mp-weixin-prod`。目录重命名被本机文件句柄阻止后，改为先完整备份、再按清单同步文件并核对最终哈希。
- 外置证据：Windows项目资料目录下 `小程序上传修复-20261026/`；构建、测试和隔离提交工作树在 `/home/quyu/kaogong_upload_fix_20261026/`。本轮未更换服务器后端、未提交微信审核或正式发布。
