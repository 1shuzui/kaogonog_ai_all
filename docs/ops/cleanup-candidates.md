# 清理候选清单

本次整理不删除、不移动这些目录，只记录体积和重建方式。后续要真正删除时，再单独确认。

| 路径 | 当前判断 | 说明 |
| --- | --- | --- |
| `.venv/` | 可重建 | Python 虚拟环境，体积最大；删除后需重新安装依赖。 |
| `civil-interview-frontend/node_modules/` | 可重建 | `npm install` 可恢复。 |
| `civil-interview-miniprogram/node_modules/` | 可重建 | `npm install` 可恢复。 |
| `civil-interview-frontend/dist/` | 可重建 | `npm run build` 生成。 |
| `civil-interview-miniprogram/dist/` | 可重建 | `npm run build:mp-weixin:prod` 生成。 |
| `**/__pycache__/` | 可删除 | Python 字节码缓存。 |
| `**/.pytest_cache/` | 可删除 | pytest 缓存。 |
| `test-results/`、`civil-interview-frontend/test-results/` | 可删除 | 自动化测试产物。 |
| `.run/` | 谨慎清理 | 本地运行日志和旧数据库备份；数据库备份已迁到 `doc_secret`。 |
| `civil-interview-backend/storage/modelscope_cache/` | 暂不移动 | FunASR 模型缓存，约 502M，可重下但成本较高。 |

## 体积复核命令

```bash
cd /home/quyu/kaogong_ai
du -sh .venv civil-interview-frontend/node_modules civil-interview-miniprogram/node_modules \
  civil-interview-frontend/dist civil-interview-miniprogram/dist \
  civil-interview-backend/storage/modelscope_cache 2>/dev/null
```

## 后续删除建议

- 只在确认不需要立即本地运行时删除 `.venv` 和 `node_modules`。
- 不要删除 `civil-interview-backend/storage/modelscope_cache`，除非接受下次 ASR 首次运行重新下载模型。
- 删除构建产物前，先确认没有准备同步服务器的产物依赖这些目录。
