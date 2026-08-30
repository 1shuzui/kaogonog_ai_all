# 密码重置、管理员核验与验证码通道

## 当前上线流程

当前版本先使用人工管理员通道，不依赖尚未完成实名资质、签名/模板审核或域名验证的外部服务：

1. 用户在 PC 或小程序填写用户名，以及可选的邮箱/手机号。
2. `POST /password-reset/request` 只创建一条当前待办；响应始终使用相同文案，不返回验证码，也不确认账号是否存在。
3. 管理员在 PC 工作台进入“密码重置核验”，对比用户名、账号邮箱、申请联系方式和既有客服信息。
4. 管理员点击“核验并生成验证码”。验证码明文只在本次管理员响应中显示一次，数据库只保存密码哈希。
5. 管理员通过已经核验的联系方式把验证码发给用户。用户在 15 分钟内输入验证码并设置新密码。
6. 同一验证码连续错误 8 次后锁定，管理员可重新签发；重置完成后删除当前申请，不保留近期密码重置审计列表。

该流程复用现有 `admin` 身份和后台路由守卫，不改变管理员权限体系。普通用户、未登录请求和越权请求都不能读取待办或签发验证码。

## 接口边界

| 接口 | 调用方 | 语义 |
| --- | --- | --- |
| `POST /password-reset/request` | 用户/匿名登录页 | 提交待管理员核验的申请；永不返回明文验证码。 |
| `GET /password-reset/admin/requests` | 管理员 | 读取当前待办，不作为历史审计接口。 |
| `POST /password-reset/admin/requests/{requestId}/issue` | 管理员 | 核验后签发一次性验证码；明文只返回一次。 |
| `POST /password-reset/verify` | 用户 | 校验管理员发送的验证码。 |
| `POST /password-reset/confirm` | 用户 | 再次校验验证码、更新密码并删除当前申请。 |

`password_reset_cases.user_id` 关联不可变用户主键，因此微信临时用户名改成 PC 用户名后，当前申请不会失去归属。表中不保存验证码明文；账号不存在时不写记录，用户响应仍与账号存在时一致。

## 国内短信验证码如何接入

国内短信不是拿到 AccessKey 就可以直接发送。正式接入前通常要完成账号实名认证、短信实名资质报备、签名申请、验证码模板申请和运营商报备。以腾讯云当前规则为例，国内短信需要先提交实名资质，再创建签名和正文模板；签名还要完成运营商侧报备。参见腾讯云官方的[国内短信快速入门](https://cloud.tencent.com/document/product/382/37745)与[短信使用须知](https://cloud.tencent.com/document/product/382/13444/)。

### 腾讯云短信

1. 完成腾讯云账号与短信实名资质配置，申请并审核通过签名、验证码模板。
2. 创建只允许发送短信所需权限的子账号/密钥，不把 `SecretId`、`SecretKey` 写入仓库。
3. Python 安装 `tencentcloud-sdk-python`，调用 `Sms` 服务的 `SendSms`；请求域名是 `sms.tencentcloudapi.com`。官方 Python 示例见[短信 SDK Python 调用](https://cloud.tencent.com/document/product/382/56059)，整体接入步骤见[国内短信快速入门](https://cloud.tencent.com/document/product/382/37745)。
4. 参数由服务端固定配置：`SdkAppId`、已审核 `SignName`、已审核 `TemplateId`；手机号和验证码作为收件人与模板变量传入。签名、模板 ID 不接受客户端覆盖。

### 阿里云短信

1. 在短信服务控制台完成资质、签名和验证码模板审核。
2. 使用 RAM 子用户和最小必要权限，通过环境变量或密钥管理服务注入凭证。
3. Python 安装 `alibabacloud_dysmsapi20170525`，构造 `SendSmsRequest`，填写 `phone_numbers`、`sign_name`、`template_code` 和 JSON 格式的 `template_param`。官方示例与环境变量说明见[阿里云短信 Python SDK 调用示例](https://help.aliyun.com/zh/sms/developer-reference/using-python-openapi-example)。

### 接入本项目时的实现位置

取得资质和密钥后，在独立通知服务中封装供应商 SDK，由管理员签发接口选择 `manual` 或 `sms` 通道。供应商返回受理成功后，才把申请标记为 `issued`；失败时保持 `pending`，管理员可以直接改用人工发送。必须保留以下行为：

- 供应商凭证只从服务器环境变量/密钥服务读取。
- 手机号写日志时脱敏，验证码与 AccessKey 不进入日志、错误响应或数据库明文字段。
- 单用户只保留当前申请，避免重复点击产生多条发送任务。
- 外部供应商失败不能自动放行重置，也不能把验证码回传给普通用户。
- 仍由本项目服务器校验验证码哈希和 15 分钟有效期，不能仅相信端侧“发送成功”。

## 邮箱验证码如何接入

如果前期用户已经绑定可靠邮箱，邮件通常比国内短信更容易启动，但仍应先验证发信域名/发信地址并配置 SPF、DKIM 等域名记录。

### 腾讯云邮件推送

腾讯云邮件推送提供 `SendEmail` API，也支持 SMTP。官方 [API 概览](https://cloud.tencent.com/document/product/1288/51062)列出了 `SendEmail` 与发送状态查询；[SMTP 发送指南](https://cloud.tencent.com/document/product/1288/65749)说明了发信地址、SMTP 密码及当前限频。新接入优先使用 API 或企业认证账号，发件域名和地址由服务器配置，收件地址使用用户已绑定邮箱或管理员核验后的地址。

### 阿里云邮件推送

阿里云 DirectMail 可通过 `SingleSendMail` 发送单封验证码邮件。先在控制台验证发信域名、创建发信地址，再使用 RAM 凭证调用；接口字段和限制见官方 [SingleSendMail 文档](https://help.aliyun.com/zh/direct-mail/singlesendmail)与 [DirectMail SDK 手册](https://help.aliyun.com/zh/direct-mail/sdk-manual)。

## 当前建议

项目早期保持 `manual` 管理员发送模式最稳妥：它没有供应商资质和密钥依赖，也符合当前低请求量。准备自动化时，若大多数用户已绑定并验证邮箱，可先接邮件；国内短信应在公司主体、实名资质、签名和验证码模板都审核通过后再开启。无论选择哪种通道，用户接口都继续返回通用受理结果，管理员后台与服务端验证码校验保持不变。
