# 复习记录、账号与媒体兼容契约

## 不可变归属

登录响应与 `GET /user/info` 新增字符串 `userId`，取自 `users.id`。保留 `username` 以及用户信息中旧 `id` 的原有含义。微信首次补全登录名不会改变 `userId`，不会合并已有 PC 账号、权益或练习记录。

`user_review_states` 以 `(user_id, exam_id, question_id)` 为复合主键，分别保存 `is_starred` 和 `hide_weak`。考试仍使用历史用户名字段；归属先由当前认证用户定位，再通过该用户的考试与真实答案验证。客户端不能指定归属用户，题干、分数和低分状态均取服务端记录。

## 当前用户复习接口

所有接口均需 Bearer 认证，生产网关前缀为 `/api`。

| 方法与路径 | 请求 | 结果 |
| --- | --- | --- |
| `GET /user/review-items` | `current >= 1`、`pageSize <= 200`、`type=all/weak/starred` | `userId/list/total/current/pageSize`；只返回本人可见复习记录 |
| `PUT /user/review-items` | `examId/questionId`，至少一个 `isStarred/hideWeak` | 持久化标记；无权、缺失、占位答案均返回同样的 404 |
| `POST /user/review-items/clear` | `scope=all/weak/starred` | 批量保存对应取消或移除标记，保留考试历史 |
| `POST /user/review-items/import` | 最多 200 个含 `examId/questionId/isStarred` 的 `items` | `imported/rejected` 等统计；逐条核验归属，重复导入幂等 |

低分题要求有效文字稿、有限的有效分数及正数满分，得分率低于 60%；真实零分计入，未作答占位、待评分和无效分数排除。无仪态分的历史结果优先使用 `questionScore/questionMaxScore`，其余沿用现有题目满分契约。取消收藏或移除低分题的状态不会被旧缓存再次导入覆盖；同一道题的新一次作答独立形成记录。

客户端只缓存当前 `userId` 的服务端快照。读写同时核对账号和 token，迟到请求不能写入另一会话。网络写入失败保留原状态并提示未保存；保存成功而刷新失败明确说明已保存并允许重新同步。旧全局和用户名缓存只作为一次迁移候选，原数据保留，无法证实归属的内容不展示。

## 认证恢复与练习统计

注册与微信补全共用真实规则：3–32 位英文字母、数字、下划线或连字符，保留 `wxmp_` 前缀不能由用户创建。冲突返回 409，已有 PC 账号使用账号密码登录。两端表单保留输入并持续显示中文错误。

找回密码顺序为提交申请、管理员核验并人工发送最新验证码、用户验证、设置新密码。改密成功后，同一事务撤销 web、wechat 和旧无会话标识 token 的使用资格。验证码过期、错误次数锁定、重签发与单次使用规则保持服务端校验。详见[密码重置运行手册](../ops/password-reset-delivery.md)。

`GET /history/stats` 新增 `scoredExams`，`totalExams` 是已完成历史次数，均分以已经有效点评的完成记录为分母并归一到 100 分；真实零分计入，待点评记录不拉低均分。历史缺失练习类型时展示“历史练习（未记录类型）”。

## 选题与历史媒体

准备页显式 `questionId` 优先于有序 `questionIds`，有序 ID 优先于旧生成缓存和随机抽题。`filterSnapshot` 传递地区、年份、分类、题型等白名单字段；失败保留选择，禁止用随机题替换。多题中途退出保留服务端原始 `questionIds`，结果页补齐未答占位并按原顺序展示。

`exam_answers.media_record` 是媒体持久化来源，同时兼容旧 `score_result.mediaRecord`。上传后立即保存 URL、类型、文件信息；转写、评分成功及重试均保留媒体地址，较旧评分元数据不能覆盖新上传。ASR 元数据只补写已验证归属的考试和题目，不按全局音频指纹猜测归属。客户端使用 API 基址统一解析 `/uploads` 地址，媒体类型规范为 MIME，历史重开无需依赖临时文件。

应用启动以可重复执行的增量方式创建复习表、补齐旧答案表的 `media_record` 列；已有数据不重写。旧客户端可继续使用原接口。回退应用代码时可保留新增表列。

管理员 JSON/Excel 导入先区分文件解析错误与数据库保存失败。行写入使用保存点隔离失败项；外层保存失败回滚本次事务。成功后清理选题和套题缓存。旧 `.xls` 明确提示另存为 `.xlsx`，损坏或加密 `.xlsx` 返回 400。

评分权重与模型流程未调整。能力维度、内容分上限、默认／实际仪态来源和套题只计一次的说明由两端共同展示，仍以[评分契约](scoring.md)为准。

## 验证

服务端测试：`test_review_service.py`、`test_acceptance_api_workflows.py`、`test_account_recovery_acceptance.py`、`test_media_persistence_acceptance.py`、`test_summary_acceptance.py`。客户端共用规则在 `shared/tests`，实际准备页、结果页、会话竞态也有回归。具体环境与尚待真机复验项见[验收记录](../testing/acceptance-repair-20260927.md)。
