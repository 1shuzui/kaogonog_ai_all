# 管理员权益管理

本文说明 PC 管理员如何补发、扣减和核查用户权益。这个功能只处理人工售后调整，不编辑套餐价格，也不创建微信虚拟支付订单。

## 入口

- PC 端登录管理员账号。
- 进入“我的”页，点击“管理员工作台”。
- 进入“用户权益管理”查询用户，或进入“权益调整流水”核查历史记录。

## 查询用户

1. 在“用户权益管理”输入用户名、昵称或邮箱关键字。
2. 点击“查询”。
3. 在用户列表点击“查看”。

详情页会展示：

- 用户基础信息。
- 总剩余分钟、今日可用分钟、付费订单数量。
- 每条权益的套餐名、总分钟、已用分钟、每日限额、有效期和状态。
- 最近人工调整记录。

## 补发人工权益

补发用于客服补偿、活动赠送、测试账号或误操作修正。补发后会立即新增一条 `user_subscriptions` 记录：

- `package_code=manual_grant`
- `plan_type=manual`
- `source_order_no=''`

操作步骤：

1. 在用户详情页点击“补发权益”。
2. 手动填写补发分钟数、每日限额、开始时间、到期时间、原因类型和备注。
3. 补发超过 300 分钟时，前端会二次确认。
4. 提交后刷新用户权益列表和最近调整记录。

注意：

- 每日限额为 `0` 表示不限，但仍需要管理员主动填写。
- 到期时间必须晚于开始时间。
- 备注要写清沟通背景或审批依据，方便后续查账。
- 补发不会创建 `payment_orders`，所以不会影响微信虚拟支付订单、查单和退款口径。

## 扣减指定权益

扣减用于退款扣减、误操作修正或售后纠错。扣减通过增加指定权益的 `used_minutes` 生效，不写 `usage_records`。

操作步骤：

1. 在用户权益列表找到目标权益。
2. 点击“扣减”。
3. 填写扣减分钟数、原因类型和备注。
4. 扣减超过该权益剩余 80%，或扣完后权益将失效时，前端会二次确认。
5. 提交后刷新用户权益列表和最近调整记录。

边界：

- 扣减不能超过目标权益剩余分钟数。
- 扣减后剩余为 0 时，权益会变为 `inactive`。
- 有每日限额的权益会同步增加 `daily_used_minutes`，保证当天余额也立即减少。
- 扣减不修改历史 `usage_records`，因为用户真实答题用量和售后处理必须分开。

## 查调整流水

“权益调整流水”可按以下条件筛选：

- 用户名。
- 动作：补发、扣减。
- 操作者。
- 时间范围。

流水包含：

- 被调整用户和权益 ID。
- 分钟变化。
- 原因类型和备注。
- 调整前后余额摘要。
- 操作者和时间。

## 误操作处理

不要删除流水，也不要直接改数据库抹掉历史记录。

推荐做法：

- 误补发：对对应权益做一次扣减，原因类型选“误操作修正”。
- 误扣减：给用户补发同等分钟的人工权益，原因类型选“误操作修正”。

这样会保留两条调整流水，能够还原完整处理过程。

## 排查 SQL

```sql
SELECT id, package_code, plan_type, status, total_minutes, used_minutes,
       daily_limit_minutes, daily_used_minutes, start_at, end_at
FROM user_subscriptions
WHERE username = '替换成用户名'
ORDER BY created_at DESC, id DESC;

SELECT target_username, subscription_id, action_type, minutes_delta,
       reason_type, remark, operator, created_at
FROM entitlement_adjustments
WHERE target_username = '替换成用户名'
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## 风险提醒

- 不要把人工补偿写成真实支付订单。
- 不要用 `usage_records` 伪造扣减记录。
- 不要允许普通用户查看后台调整流水。
- 上线前确认 `entitlement_adjustments` 表已通过 `database_setup.py --check` 或初始化脚本创建。
