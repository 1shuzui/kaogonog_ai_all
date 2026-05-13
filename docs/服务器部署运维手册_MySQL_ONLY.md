# 公考面试平台服务器部署与运维手册（MySQL-only）

> 适用环境：`Ubuntu`、运行用户 `ubuntu`、项目根目录 `/home/ubuntu/civil`。  
> 本手册明确 **不使用 SQLite**，仅使用 MySQL。

## 0. 当前线上约定（必须先理解）

1. 反向代理：`Nginx` 监听 `80` 端口。
2. 前端静态目录：`/home/ubuntu/civil/latest/frontend`。
3. 后端服务：`systemd` 单元 `civil-backend.service`。
4. 后端工作目录：`/home/ubuntu/civil/latest/backend`。
5. 后端监听：`0.0.0.0:8050`（由 Nginx 反代，不直接对公网暴露）。
6. 数据库：`MySQL`，连接串由 `backend/.env` 中 `DATABASE_URL` 提供。
7. 版本切换：通过软链 `latest -> civil_release_xxx` 完成。

---

## 1. 前置条件清单（不满足则不要开始）

### 1.1 服务器与系统

1. 已有 Linux 服务器（推荐 Ubuntu 20.04/22.04）。
2. 具备 SSH 登录权限（私钥可用）。
3. 具备 `sudo` 权限。

检查命令：

```bash
whoami
hostname
uname -a
sudo -v
```

原理说明：
- 你后续会改 systemd、Nginx、服务文件，必须可执行 `sudo`。

### 1.2 运行时组件

1. `python3.10` 可用（PyArmor 运行时依赖）。
2. `nginx` 已安装并可启动。
3. `mysql` 服务可访问（本机或远程）。
4. 磁盘空间建议至少剩余 5GB。

检查命令：

```bash
python3.10 --version
nginx -v
mysql --version
df -h /
free -h
```

原理说明：
- PyArmor 生成的运行时与 Python ABI 强相关，Python 小版本不匹配会起不来。
- Nginx 负责静态文件与反代，MySQL 负责业务数据持久化。

### 1.3 网络与域名

1. 域名 A 记录指向服务器公网 IP。
2. 80 端口开放（HTTPS 上线时还需 443）。
3. 若启用防火墙，放行 `22/80/443`。

检查命令：

```bash
ss -lntp | grep -E ':22|:80|:443' || true
sudo ufw status verbose || true
```

---

## 2. 部署包上传与校验

### 2.1 上传

在本地执行：

```bash
scp -i ~/.ssh/civil.pem /home/quyu/civil/civil_release_20260509_202930.tar.gz ubuntu@150.158.87.179:/home/ubuntu/civil/
scp -i ~/.ssh/civil.pem /home/quyu/civil/civil_release_20260509_202930.tar.gz.sha256 ubuntu@150.158.87.179:/home/ubuntu/civil/
```

### 2.2 服务器验签

```bash
cd /home/ubuntu/civil
sha256sum -c civil_release_20260509_202930.tar.gz.sha256
```

原理说明：
- SHA256 用于确认文件传输过程未损坏、未被篡改。

---

## 3. 解压与版本切换（标准做法）

```bash
cd /home/ubuntu/civil
tar -xzf civil_release_20260509_202930.tar.gz
ln -sfn /home/ubuntu/civil/civil_release_20260509_202930 /home/ubuntu/civil/latest
readlink -f /home/ubuntu/civil/latest
```

原理说明：
- `latest` 是运行入口；切版本只改软链，回滚同理，避免改大量配置路径。

---

## 4. 解密配置（只在服务器落明文）

### 4.1 使用密钥解密

```bash
cd /home/ubuntu/civil/latest
CIVIL_CONFIG_KEY_FILE=/home/ubuntu/civil/CONFIG_DECRYPTION_KEY_civil_release_20260509_202930.txt ./scripts/decrypt_envs.sh
```

### 4.2 权限收紧

```bash
chmod 600 /home/ubuntu/civil/latest/backend/.env
```

原理说明：
- 加密包可传输，明文只在目标机短路径落地，降低泄漏面。

---

## 5. 强制 MySQL-only（去 SQLite 化）

> 目标：运行目录中没有 SQLite 数据文件，配置中没有 SQLite 连接。

### 5.1 检查并设置数据库连接

编辑 `/home/ubuntu/civil/latest/backend/.env`，确保：

```dotenv
DATABASE_URL=mysql+pymysql://<mysql_user>:<mysql_password>@<mysql_host>:3306/kaogong_ai
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=<mysql_user>
MYSQL_PASSWORD=<mysql_password>
MYSQL_DATABASE=kaogong_ai
```

检查命令：

```bash
grep -E '^(DATABASE_URL|MYSQL_HOST|MYSQL_PORT|MYSQL_USER|MYSQL_DATABASE)=' /home/ubuntu/civil/latest/backend/.env
```

判定标准：
- `DATABASE_URL` 必须以 `mysql+pymysql://` 开头；
- 不得出现 `sqlite:///`。

### 5.2 删除 SQLite 文件（最新目录 + 发布目录）

```bash
rm -f /home/ubuntu/civil/latest/backend/civil_interview.db
rm -f /home/ubuntu/civil/latest/data/civil_interview.sqlite.db
rm -f /home/ubuntu/civil/civil_release_20260509_202930/backend/civil_interview.db
rm -f /home/ubuntu/civil/civil_release_20260509_202930/data/civil_interview.sqlite.db
find /home/ubuntu/civil -type f \( -name '*sqlite*.db' -o -name 'civil_interview.db' \) -print
```

判定标准：
- 最后一条 `find` 不应输出任何文件。

原理说明：
- 防止误操作/误回退到本地 DB 文件，避免多数据源并存导致数据错乱。

---

## 6. 安装后端依赖（每次新版本建议执行）

```bash
cd /home/ubuntu/civil/latest
PYTHON_BIN=python3.10 ./scripts/install_backend_deps.sh
```

原理说明：
- 每个版本目录自己的 `.venv`，依赖隔离，避免系统环境污染。

---

## 7. MySQL 数据导入与校验

### 7.1 导入

```bash
cd /home/ubuntu/civil/latest
./scripts/import_mysql_dump.sh
```

### 7.2 数据校验（示例）

```bash
mysql -u <mysql_user> -p -e "USE kaogong_ai; SHOW TABLES;"
mysql -u <mysql_user> -p -e "USE kaogong_ai; SELECT COUNT(*) AS users_count FROM users;"
mysql -u <mysql_user> -p -e "USE kaogong_ai; SELECT COUNT(*) AS questions_count FROM questions;"
```

原理说明：
- 先结构后业务数据，确认关键表存在且行数合理，避免应用启动后才发现空库。

---

## 8. systemd 托管后端（生产必需）

### 8.1 服务文件

路径：`/etc/systemd/system/civil-backend.service`

关键字段解释：
- `WorkingDirectory`: 必须指向 `latest/backend`，保证相对路径与资源加载正确。
- `EnvironmentFile`: 从 `.env` 注入 DB 与 API 配置。
- `ExecStart`: 固定用 `.venv/bin/python -m uvicorn`，避免 PATH 混乱。
- `Restart=always`: 崩溃自动拉起。

### 8.2 生效与启动

```bash
sudo systemctl daemon-reload
sudo systemctl enable civil-backend.service
sudo systemctl restart civil-backend.service
sudo systemctl status civil-backend.service --no-pager -l
```

### 8.3 日志追踪

后端默认输出结构化 JSON 日志到 stdout/stderr，由 `systemd journal` 收集。  
生产推荐在 `/home/ubuntu/civil/latest/backend/.env` 中保留：

```dotenv
APP_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10
LOG_RETENTION_DAYS=30
LOG_ACCESS_ENABLED=true
```

字段说明：
- `LOG_LEVEL`: `DEBUG/INFO/WARNING/ERROR`，生产通常用 `INFO`。
- `LOG_FORMAT`: `json` 便于检索和后续接入日志平台；临时人工排查可设为 `text`。
- `LOG_FILE`: 留空时只走 journal；填写 `logs/backend.jsonl` 时，应用会启用 `RotatingFileHandler`。
- `LOG_MAX_BYTES` 与 `LOG_BACKUP_COUNT`: 应用内日志文件大小轮转策略。
- `LOG_RETENTION_DAYS`: 保留天数约定，用于运维策略说明；journal 的真实保留还要看 journald 配置。
- `LOG_ACCESS_ENABLED`: 是否记录每个 HTTP 请求的完成日志。

实时查看：

```bash
sudo journalctl -u civil-backend.service -f
```

查看最近 200 条并保持 JSON 原文：

```bash
sudo journalctl -u civil-backend.service -n 200 --no-pager -o cat
```

按请求 ID 串联一次请求：

```bash
sudo journalctl -u civil-backend.service --no-pager -o cat | grep '<x-request-id>'
```

生产日志统一字段：
- 基础字段：`timestamp`、`level`、`logger`、`message`、`event`、`module`、`function`、`line`。
- 请求字段：`request_id`、`user_id`、`method`、`path`、`status_code`、`duration_ms`、`client_ip`。
- 登录字段：`event=auth.login.succeeded/auth.login.failed`、`username`、`reason`。
- 支付字段：`event=payment.* / wechat_pay.*`、`order_no`、`package_code`、`amount`、`pay_channel`、`status`、`transaction_id`。
- 评分字段：`event=scoring.* / llm.* / asr.*`、`exam_id`、`question_id`、`scoring_mode`、`total_score`、`grade`。
- 异常字段：`exception.type`、`exception.message`、`exception.stack`。

脱敏规则：
- 不得记录明文密码、token、Authorization、API Key、私钥、微信 `openid/session_key`、支付签名、密文回调体等。
- 后端日志过滤器会把敏感键值替换为 `***`，前端与小程序 logger 也会做同类脱敏。
- 排查问题时优先使用 `request_id/order_no/exam_id` 定位，避免把 `.env`、完整 token 或证书内容贴入日志。

如果需要限制 journal 保留量，可编辑：

```bash
sudo nano /etc/systemd/journald.conf
```

建议项：

```ini
SystemMaxUse=1G
MaxRetentionSec=30day
```

生效：

```bash
sudo systemctl restart systemd-journald
```

原理说明：
- 应用日志输出到 stdout/stderr 后由 systemd 接管，服务崩溃前后的日志仍可通过 journal 统一查看。
- `x-request-id` 会从前端/小程序传入，缺失时后端生成，并随响应头返回，用于把前端报错、Nginx 访问、后端业务日志串成一条链路。
- 应用内文件轮转适合临时落盘；长期生产建议让 journal 或专业日志平台负责保留、压缩、检索和告警。

---

## 9. Nginx 配置与重载

配置文件：`/etc/nginx/conf.d/default.conf`

最小可用配置（示例）：

```nginx
server {
    listen 80;
    server_name xzqianmianyuzhoukeji.com;

    root /home/ubuntu/civil/latest/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8050/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8050/uploads/;
    }
}
```

检查与重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager -l
```

原理说明：
- `try_files ... /index.html` 支持前端 history 路由。
- `/api/` 反代时末尾 `/` 决定路径拼接行为，当前配置会把 `/api/token` 转到后端 `/token`。

---

## 10. 上线后验收清单（必须逐条验证）

前端与小程序构建时也有日志开关：

```dotenv
# PC 前端：civil-interview-frontend/.env.production
VITE_API_BASE=https://xzqianmianyuzhoukeji.com/api
VITE_LOG_LEVEL=error

# 小程序：civil-interview-miniprogram/.env.production
VITE_API_BASE=https://xzqianmianyuzhoukeji.com/api
VITE_API_BASE_H5=https://xzqianmianyuzhoukeji.com/api
VITE_API_BASE_MP_WEIXIN=https://xzqianmianyuzhoukeji.com/api
VITE_LOG_LEVEL=error
```

说明：
- 可选值为 `debug/info/warn/error/silent`。
- 生产建议 `error`，联调可临时改为 `debug`。
- PC 前端和小程序请求都会生成 `X-Request-ID`，后端会记录同一个 `request_id`。
- 客户端日志统一走 `src/utils/logger.js`，业务代码不要直接写 `console.log/warn/error`。

```bash
# 1) 后端健康
curl -s -o /tmp/health.json -w "%{http_code}\n" http://127.0.0.1:8050/health
cat /tmp/health.json

# 2) 后端登录（直连）
curl -s -o /tmp/token_backend.json -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8050/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=123456789"
cat /tmp/token_backend.json

# 3) Nginx 入口登录（反代链路）
curl -s -o /tmp/token_nginx.json -w "%{http_code}\n" \
  -X POST http://127.0.0.1/api/token \
  -H "Host: xzqianmianyuzhoukeji.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=123456789"
cat /tmp/token_nginx.json
```

判定标准：
- 三处 HTTP 状态码均为 `200`；
- token JSON 中存在 `access_token` 字段。

---

## 11. 常见故障与定位

### 11.1 502 Bad Gateway

现象：Nginx 返回 502。  
排查顺序：

```bash
sudo systemctl status civil-backend --no-pager -l
sudo journalctl -u civil-backend -n 120 --no-pager
ss -lntp | grep 8050 || true
```

结论判定：
- 若 8050 未监听：后端没起来；
- 若日志出现 MySQL 拒绝：检查 `DATABASE_URL` 与账号授权。

### 11.2 登录提示“账号或密码错误”

排查命令：

```bash
curl -s -o /tmp/token_debug.json -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8050/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=<你的密码>"
cat /tmp/token_debug.json
```

说明：
- 401 基本是数据库中的密码哈希与输入不匹配，不是前端静态资源问题。

### 11.3 配置更新后服务起不来

```bash
sudo systemctl restart civil-backend
sudo journalctl -u civil-backend -n 200 --no-pager
grep -E '^(DATABASE_URL|MYSQL_)' /home/ubuntu/civil/latest/backend/.env
```

---

## 12. 升级与回滚标准流程

### 12.1 升级

1. 上传新包并验签  
2. 解压新目录  
3. `latest` 指向新目录  
4. 解密 `.env`、检查 MySQL 连接  
5. 依赖安装  
6. 重启服务  
7. 执行验收清单

### 12.2 回滚

```bash
ln -sfn /home/ubuntu/civil/<旧版本目录> /home/ubuntu/civil/latest
sudo systemctl restart civil-backend
sudo systemctl status civil-backend --no-pager -l
```

原理说明：
- 回滚只切软链，避免“改配置+改代码”双变量导致回滚不可控。

---

## 13. 安全与规范（强烈建议）

1. 不要在聊天或日志中暴露 `.env` 明文。  
2. `backend/.env` 权限固定为 `600`。  
3. 为 MySQL 使用专用最小权限账号，不使用 `root` 作为应用账号。  
4. 生产建议启用 HTTPS（80 跳转 443）并配置证书自动续期。  
5. 对外仅暴露 Nginx 端口，不直接暴露 8050。

---

## 14. 本次变更记录（2026-05-10）

1. 后端运行配置已固定为 MySQL。  
2. 服务器部署目录中的 SQLite 文件已清除。  
3. `civil-backend.service` 保持 `enabled + active`。  
4. `health` 与 `token(admin/123456789)` 已验证通过。  
