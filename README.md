# 避坑宝 MVP

面向中国普通消费者的装修报价/合同审核 MVP。当前仓库包含三部分：

- `miniprogram/`：微信小程序前端，包含上传审核、报告页、历史记录、我的页。
- `server/`：后端 API 框架，包含登录、文件上传、生成审核、订单、模拟支付、历史记录、删除资料。
- 根目录 `index.html` / `app.js` / `styles.css`：Vercel Web 演示入口，已接入同源后端 API，可验证上传、报告、订单、解锁、历史记录。

## 运行

启动后端 API：

```bash
python3 -m server.run
```

健康检查：

```bash
curl http://127.0.0.1:8787/health
```

打开微信开发者工具，导入本目录，项目配置会读取 `project.config.json`，小程序根目录为 `miniprogram/`。

本地调试时，小程序接口地址在 `miniprogram/config/env.js`：

```js
API_BASE_URL: "http://127.0.0.1:8787"
```

如果微信开发者工具无法请求本地接口，需要在开发者工具里勾选“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。

## Vercel 部署

仓库已包含 Vercel Python Function 入口：

- `api/index.py`
- `vercel.json`

Vercel 生产环境需要配置环境变量：

```bash
BIKENGBAO_AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
BIKENGBAO_DB_PROVIDER=postgres
DATABASE_URL=Neon Postgres 连接串
BIKENGBAO_FILE_STORAGE_PROVIDER=blob
BLOB_READ_WRITE_TOKEN=Vercel Blob 读写 Token
```

本地开发未配置 `DATABASE_URL` 和 `BLOB_READ_WRITE_TOKEN` 时，会自动回退到 JSON 文件数据库和本地上传目录。正式线上不要依赖 `/tmp`，否则 Serverless 实例回收后数据会丢失。

Web 演示页本地预览：

```bash
python3 -m http.server 4173
```

然后访问 `http://127.0.0.1:4173`。本地 4173 页面会自动请求 `http://127.0.0.1:8787`；部署到 Vercel 后会自动请求同域名下的 `/health` 和 `/v1/*`。

## 已实现

- 微信小程序原生页面框架。
- 服务端文件上传、报告生成、历史记录、删除资料。
- 免费预览 3 条风险，支付后服务端解锁完整报告。
- Web 页面与小程序共用后端 API，本地模拟微信登录和模拟支付，便于先验证产品闭环。
- 网站版已支持扫码付款 + 后台人工确认：用户生成付款备注码，运营在 `/admin.html` 确认到账后自动解锁报告。
- 规则引擎生成报价/合同风险、追问清单、砍价话术、家人版总结。
- DeepSeek AI 适配已实现，OCR、微信支付适配器仍为占位，后续可以接真实服务。
- 生产数据层适配已实现：Neon Postgres 存用户、文件记录、报告和订单；Vercel Blob 存用户上传原始文件。

## V1 边界

当前后端仍保留本地 JSON 和本地文件作为开发兜底。正式上线前还需要替换真实 OCR、微信支付、微信登录、隐私政策和用户协议。

本产品不提供法律意见、工程鉴定、装修公司推荐或监理服务。报告仅作为消费决策辅助。
