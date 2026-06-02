# 避坑宝 MVP

面向中国普通消费者的装修报价/合同审核 MVP。当前仓库包含三部分：

- `miniprogram/`：微信小程序前端，包含上传审核、报告页、历史记录、我的页。
- `server/`：后端 API 框架，包含登录、文件上传、生成审核、订单、模拟支付、历史记录、删除资料。
- 根目录 `index.html` / `app.js` / `styles.css`：上一版 Web 原型，可继续作为落地页或 UI 参考。

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
BIKENGBAO_DATA_DIR=/tmp/bikengbao
```

注意：`/tmp` 只能用于演示，Vercel Serverless 不适合用本地文件做生产持久化。正式上线必须接数据库和对象存储。

Web 原型仍可单独打开：

```bash
python3 -m http.server 4173
```

然后访问 `http://localhost:4173`。

## 已实现

- 微信小程序原生页面框架。
- 服务端文件上传、报告生成、历史记录、删除资料。
- 免费预览 3 条风险，支付后服务端解锁完整报告。
- 本地模拟微信登录和模拟支付，便于先验证产品闭环。
- 规则引擎生成报价/合同风险、追问清单、砍价话术、家人版总结。
- AI、OCR、微信支付适配器占位，后续可以接真实服务。

## V1 边界

当前后端使用本地 JSON 文件作为数据库，适合 MVP 开发和演示。正式上线前需要替换为生产数据库、对象存储、真实 OCR、AI API、微信支付、HTTPS 域名、隐私政策和用户协议。

本产品不提供法律意见、工程鉴定、装修公司推荐或监理服务。报告仅作为消费决策辅助。
