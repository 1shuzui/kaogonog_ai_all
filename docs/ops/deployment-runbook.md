# 部署与同步手册

## 部署前检查

```bash
cd /home/quyu/kaogong_ai
git status --short
```

确认：

- 业务源码改动是预期的。
- `.env`、`*.pem`、`*.p12` 没有出现在 Git 待提交中。
- 小程序和 PC 构建脚本可运行。

## 构建

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run build

cd /home/quyu/kaogong_ai/civil-interview-miniprogram
npm run build:mp-weixin:prod
```

## 同步服务器

推荐使用分阶段发布脚本。先提交代码、运行相关测试，再构建独立产物并做服务端导入预检，后端验收完成后同步页面：

```bash
cd /home/quyu/kaogong_ai
PYARMOR=/home/quyu/.pyenv/versions/3.10.20/bin/pyarmor bash scripts/deploy_verified_release.sh
# 复制上一步输出的 release ID；后续两步必须使用同一个 ID。
RELEASE_ID=<release-id> PHASE=backend bash scripts/deploy_verified_release.sh
RELEASE_ID=<release-id> PHASE=web bash scripts/deploy_verified_release.sh
```

每次发布保留 `/home/ubuntu/civil/releases/<release-id>` 产物与 `/home/ubuntu/civil/backups/<release-id>` 回滚副本，线上 `REVISION` 标明对应 Git 提交。后端激活失败自动恢复旧代码并重启。密钥、`.env`、虚拟环境、录音、数据库和模型缓存沿用服务器现有内容；预检要求 `LOCAL_REFERENCE_SCORING=false`。不自动安装新的依赖版本。

小程序产物同步至服务器后，仍需通过微信开发者工具上传并在微信后台发布，手机端才会收到界面更新。后端修复对现有小程序版本立即生效。

### 修复空证据导致的历史 0 分

`scripts/repair_empty_evidence_scores.py` 默认仅列出已确认的故障记录：有原文、模型打分为 0、评语明确说明证据包为空。不会修改真实空白答案或普通低分。

在服务器的新版本后端目录运行，先预览，再明确应用：

```bash
PYTHONPATH=. .venv/bin/python /home/ubuntu/civil/releases/<release-id>/repair_empty_evidence_scores.py
PYTHONPATH=. .venv/bin/python /home/ubuntu/civil/releases/<release-id>/repair_empty_evidence_scores.py \
  --apply --backup-dir /home/ubuntu/civil/backups/<release-id>/score-repair
```

应用前完整备份匹配记录和历史汇总（目录 0700，文件 0600）；外部模型完成后才替换成绩，保留原文、录音、用时与原作答时间，同步更新历史汇总。备份含用户答案，只保留在服务器私有目录，不提交 Git、不放在网站目录。

对应故障测试：

```bash
cd civil-interview-backend
../.venv/bin/python -m pytest -q tests/test_llm_response_contract.py tests/test_answer_persistence_and_local_scoring.py
cd ../civil-interview-miniprogram
node --experimental-vm-modules --test tests/answerRecovery.test.mjs
```

### 旧部署脚本

以下旧脚本保留兼容用途；常规更新优先使用上面的分阶段发布流程。

```bash
cd /home/quyu/kaogong_ai

# 只同步前端和小程序
bash scripts/deploy_clean_to_server.sh

# 同步后端、前端和小程序
DEPLOY_BACKEND=1 bash scripts/deploy_clean_to_server.sh
```

后端同步会保留服务器现有密钥、数据库、上传文件和模型缓存，但会把 `LOCAL_REFERENCE_SCORING` 明确更新为 `false`，
确保题库参考答案只作为外部模型上下文，不因服务器旧 `.env` 配置而回到本地规则点评。

## 部署后验证

- 访问生产首页：https://xzqianmianyuzhoukeji.com
- 检查后端健康接口或主要 API。
- 小程序开发者工具导入 `civil-interview-miniprogram/dist/build/mp-weixin-prod`。
- 验证登录、首页浏览、专项练习、全真模拟、套餐中心、订单中心、反馈入口。

## 回滚原则

- 先确认服务器部署脚本是否保留历史产物。
- 若是前端静态资源问题，优先重新构建并同步上一版静态产物。
- 若是后端问题，先看 systemd 日志和应用日志，再决定是否恢复上一版代码。
