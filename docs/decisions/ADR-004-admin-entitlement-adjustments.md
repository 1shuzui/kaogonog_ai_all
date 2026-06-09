# ADR-004: 管理员人工权益调整与微信支付订单分离

## Status
Accepted

## Date
2026-06-09

## Context

管理员需要处理用户售后场景，例如 ASR 异常补偿、活动赠送、测试账号补发、退款后的权益扣减和误操作修正。已有权益余额保存在 `user_subscriptions`，微信虚拟支付订单保存在 `payment_orders`，真实答题扣量保存在 `usage_records`。

如果把人工补发伪造成支付订单，会让订单中心、微信查单、退款和审核口径失真。如果把退款扣减伪造成答题用量，会让用户历史练习记录和售后处理混在一起，也会影响后续排查“为什么扣了时长”。

## Decision

- 新增 `entitlement_adjustments` 表，记录每次管理员人工补发或扣减的审计流水。
- 人工补发创建新的 `user_subscriptions`，使用 `package_code=manual_grant`、`plan_type=manual`、`source_order_no=''`。
- 人工补发不创建 `payment_orders`，不调用微信虚拟支付接口。
- 人工扣减通过增加指定 `user_subscriptions.used_minutes` 生效；有每日限额时同步调整 `daily_used_minutes`。
- 人工扣减不写 `usage_records`，不伪造答题记录。
- 误操作不删除流水，通过新增反向调整纠正。
- 每次调整后刷新 `users.preferences.subscription` 快照，让 PC 和小程序立即看到最新余额。

## Alternatives Considered

### 复用 `payment_orders`

优点是订单列表可以天然看到人工补发。

拒绝原因：人工补发并不是微信虚拟支付，复用订单表会污染支付、查单、退款和审核口径。

### 复用 `usage_records`

优点是扣减排查只看一张表。

拒绝原因：`usage_records` 表示用户真实答题或练习用量，售后扣减不是答题行为，混用会误导历史分析和用户投诉排查。

### 直接修改余额但不留审计表

优点是实现最简单。

拒绝原因：权益调整属于高风险后台操作，必须知道谁在什么时候因为什么原因改了什么。

## Consequences

- 管理员有独立工作台处理权益补发、扣减和流水查询。
- 普通用户只看到余额变化，不看到内部客服处理记录。
- 数据库多一张审计表，上线前需要补建表。
- 误操作会留下多条流水，但这是可追溯售后处理所需的成本。
