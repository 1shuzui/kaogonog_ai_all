# API 契约总览

本目录记录当前 FastAPI 业务接口的稳定使用方式，并对题库、套题、定向训练和评分这四条高耦合链路给出字段级契约。实际字段校验以运行中的 FastAPI OpenAPI 为准：本地服务启动后访问 **/docs**。

## URL 与版本边界

FastAPI 应用把 router 直接挂在根路径，开发环境中可以直接调用：

~~~text
http://127.0.0.1:8050/questions
http://127.0.0.1:8050/scoring/evaluate
~~~

PC 前端默认 API 基址配置为生产域名下的 **/api**。因此生产客户端通常看到 **/api/questions**；这个前缀由 Nginx/部署配置或 VITE_API_BASE 提供，不是后端代码中的 **/api/v1** 路由前缀。新客户端必须从可配置 API 基址拼接路径，不能硬编码生产域名或代理前缀。

除认证、健康检查、法律文档和公开分类树等明确公开接口外，业务调用一般需要：

~~~http
Authorization: Bearer <access-token>
Content-Type: application/json
~~~

上传音视频、DOCX 或表格的接口使用 multipart/form-data。

## 端点地图

| 业务域 | 当前路径族 | 详细说明 |
| --- | --- | --- |
| 服务探活 | GET /health、GET / | main.py 中的基础状态与文档入口 |
| 认证 | POST /token、/register、/auth/wechat/miniprogram*、/password-reset/* | 登录、注册、微信；密码重置见[管理员核验与验证码通道](../ops/password-reset-delivery.md) |
| 用户 | GET /user/info、/user/provinces、/user/terms-status；PUT /user/profile、/password、/preferences；POST /user/agree-terms | 用户资料、偏好、条款与风控 |
| 题库 | GET/POST /questions、GET /questions/random、GET/PUT/DELETE /questions/{id}、POST /questions/import、/questions/import/docx | [题库与套题接口](question-bank-and-suites.md) |
| 考试 | GET /exam/full-suites、GET /exam/full-suites/{id}/questions、POST /exam/start、/{examId}/upload、/{examId}/complete | [题库与套题接口](question-bank-and-suites.md) |
| 评分与转写 | POST /scoring/transcribe、/scoring/evaluate；GET /scoring/asr-status、/scoring/result/{examId}/{questionId} | [评分接口与分值契约](scoring.md) |
| 历史 | GET /history、/history/trend、/history/stats、/history/{examId} | 历史考试、趋势与统计 |
| 定向备面 | GET /positions；POST /targeted/focus、/targeted/generate、/training/generate；管理员 focus 配置接口 | [定向备面接口](targeted-training.md) |
| 试用与用量 | GET /trial/status、/trial/question；POST /trial/complete、/usage/report | 试用策略与计时用量 |
| 权益与支付 | GET /subscription/*；POST /subscription/switch、/payment/orders 等 | 套餐、权益、微信虚拟支付和退款 |
| 反馈 | GET/POST /support/feedback、POST /support/feedback/attachments、PATCH/DELETE /support/feedback/{id} | 用户反馈与管理员处理 |
| 邀请与看板 | /invite/admin/*、/admin/dashboard/* | 邀请码、渠道归因、系统与用户看板 |
| 法律 | GET /legal/documents | 法律、隐私与协议文档 |

## 高优先级契约

| 主题 | 关键结论 |
| --- | --- |
| 题库表示 | 生成资产的题干字段名是 **question**；REST 返回给客户端的字段名是 **stem**。后端同步时完成转换。 |
| 元数据存储 | JSON 资产的扩展元数据最终写入 Question.keywords._meta，不新增题库关系型列。 |
| 套题 | 全真套题只接受连续题号、同源文件和完整资格校验后的题目；不要让客户端从全量题目自行拼卷。 |
| 医疗分类 | 医疗卫生入口通过 portalTag/displayPortal 和岗位字段筛选；真实 examCategory 仍是事业单位考试。 |
| 分数 | contentScore、appearanceScore、totalScore、maxScore 是不同语义；不允许把默认仪态分反复叠加。 |
| 参考答案 | 参考答案用于后端评分上下文；普通题目响应只提供 hasReferenceAnswer，不把完整标准答案当作前台公共字段。 |
| 支付到账 | 小程序 `payResult=success` 只是查单提示；只有微信服务端查单返回 XPay 状态 2/3/4、订单号（返回时）一致、`order_type=0`（返回时）且 `order_fee` 与本地分价完全一致后，订单和权益才在同一事务中入账。金额缺失也拒绝发放。 |
| 个人数据 | 考试上传/完成、评分写入/结果和历史详情必须按当前用户名校验归属；不存在与越权统一返回 404。 |

微信官方把 XPay 状态 1 定义为“订单创建成功”，状态 2 才是“订单已经支付，待发货”，3/4 是发货中/已发货；查单响应中的 `order_fee` 是订单金额（分）。实现与边界以[微信小程序虚拟支付查询订单 API](https://developers.weixin.qq.com/miniprogram/dev/server/API/VirtualPayment/api_query_order)为准。小程序支付完成后会立即服务端查单；若回调或首次确认因网络中断，套餐页会轮询补核，订单详情也提供“查询微信到账状态”，不会让用户重新付款。端侧只收到脱敏核验摘要，不返回微信原始响应、openid 或签名请求参数。

当状态 2 的订单在本地事务中完成权益入账后，服务端再调用[微信通知已发货完成 API](https://developers.weixin.qq.com/miniprogram/dev/server/API/VirtualPayment/api_notify_provide_goods)。顺序不能倒置：先通知微信、后写本地权益会在数据库失败时形成“平台显示已发货但用户没到账”。发货通知失败不会回滚用户权益，而是在订单回调字段中标记 `delivery.status=pending`，后续幂等核单可重试；状态 3/4 则直接认定微信侧已进入或完成发货。

## 契约变更规则

1. 请求模型在 **app/schemas/common.py**，HTTP 语义在 **app/api/v1/routes/**，最终输出形状通常由 service 组装。
2. 新增筛选字段时，应同时更新后端 Pydantic 模型、service 筛选、PC 和小程序 API 封装、两端状态层以及本文档。
3. 生成题库 JSON 的字段变化还必须更新 assets 测试和 [医疗卫生题库知识库](../data/medical-question-bank.md)。
4. 任何会影响 score/满分/套题合计的字段变更，都必须写入 ADR 或更新已有 ADR，并覆盖默认分与实际分替换场景。
