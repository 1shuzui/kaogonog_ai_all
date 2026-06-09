# 密钥与本地配置恢复

真实配置和证书已迁到 `/home/quyu/doc_kaogong/doc_secret/`。仓库内不要保留真实密钥、真实 `.env` 或软链。

## 外置位置

| 原路径 | 外置路径 |
| --- | --- |
| `.env` | `/home/quyu/doc_kaogong/doc_secret/.env` |
| `ai_gongwu_backend/.env` | `/home/quyu/doc_kaogong/doc_secret/ai_gongwu_backend/.env` |
| `civil-interview-backend/.env` | `/home/quyu/doc_kaogong/doc_secret/civil-interview-backend/.env` |
| `civil-interview-frontend/.env` | `/home/quyu/doc_kaogong/doc_secret/civil-interview-frontend/.env` |
| `civil-interview-miniprogram/.env` | `/home/quyu/doc_kaogong/doc_secret/civil-interview-miniprogram/.env` |
| `apiclient_cert.p12` | `/home/quyu/doc_kaogong/doc_secret/apiclient_cert.p12` |
| `apiclient_cert.pem` | `/home/quyu/doc_kaogong/doc_secret/apiclient_cert.pem` |
| `apiclient_key.pem` | `/home/quyu/doc_kaogong/doc_secret/apiclient_key.pem` |
| `pub_key.pem` | `/home/quyu/doc_kaogong/doc_secret/pub_key.pem` |

## 恢复命令

```bash
cd /home/quyu/kaogong_ai

cp /home/quyu/doc_kaogong/doc_secret/.env .env
cp /home/quyu/doc_kaogong/doc_secret/ai_gongwu_backend/.env ai_gongwu_backend/.env
cp /home/quyu/doc_kaogong/doc_secret/civil-interview-backend/.env civil-interview-backend/.env
cp /home/quyu/doc_kaogong/doc_secret/civil-interview-frontend/.env civil-interview-frontend/.env
cp /home/quyu/doc_kaogong/doc_secret/civil-interview-miniprogram/.env civil-interview-miniprogram/.env

cp /home/quyu/doc_kaogong/doc_secret/apiclient_cert.p12 apiclient_cert.p12
cp /home/quyu/doc_kaogong/doc_secret/apiclient_cert.pem apiclient_cert.pem
cp /home/quyu/doc_kaogong/doc_secret/apiclient_key.pem apiclient_key.pem
cp /home/quyu/doc_kaogong/doc_secret/pub_key.pem pub_key.pem
```

## 校验命令

```bash
cd /home/quyu/kaogong_ai
git check-ignore -v .env apiclient_cert.p12 apiclient_cert.pem apiclient_key.pem pub_key.pem
git status --short --ignored | rg '\\.env|\\.pem|\\.p12|pub_key'
```

如果这些文件出现在普通 Git 待提交列表中，先停止提交并检查 `.gitignore`。
