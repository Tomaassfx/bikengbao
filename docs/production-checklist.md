# 上线前检查清单

## 必须替换

- 数据库：已支持 Neon Postgres。Vercel 生产环境配置 `BIKENGBAO_DB_PROVIDER=postgres` 和 `DATABASE_URL` 后启用。
- 文件存储：已支持 Vercel Blob。Vercel 生产环境配置 `BIKENGBAO_FILE_STORAGE_PROVIDER=blob` 和 `BLOB_READ_WRITE_TOKEN` 后启用。
- OCR：在 `server/adapters/ocr.py` 接入腾讯云、百度、阿里或火山 OCR。
- AI：DeepSeek 已接入，部署平台配置 `BIKENGBAO_AI_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY` 后，报告会返回 `aiStatus=deepseek_ok`。
- DeepSeek：密钥只放环境变量，不要写入代码、README 或小程序配置。
- 支付：在 `server/adapters/payment.py` 接入微信支付 JSAPI，并增加支付回调验签。
- 登录：将模拟 token 替换为微信 `code2session` 和服务端 session/JWT。
- 域名：Web 后端必须部署到 HTTPS；微信小程序上线时，还要将该域名加入 request/uploadFile 合法域名。

## 合规与安全

- 隐私政策、用户协议、免责声明。
- 上传文件加密存储，敏感信息脱敏。
- 用户删除报告时同步删除对象存储文件。
- 后端接口鉴权、限流、防刷、防重复支付。
- 日志不得记录完整合同、手机号、地址等敏感信息。

## 当前 Vercel 演示边界

- 可以验证 Web 页面、API、DeepSeek、模拟支付、报告解锁、历史记录。
- 数据库和对象存储接入后，线上数据不再依赖 `/tmp`。
- Vercel Blob 当前使用不可猜测路径存储原始文件，接口不向前端返回 Blob URL。后续建议增加自动过期清理、上传前敏感信息脱敏和后台删除审计。
- 小程序上线还缺微信小程序 AppID、微信支付商户号、隐私政策、用户协议和小程序后台域名白名单。

## 产品验证

- 埋点：访问、上传、预览、支付点击、支付成功、复制话术、删除资料。
- A/B 价格：29/59/99 元。
- 报告质量抽检：随机审核输出，避免法律结论、过度承诺和事实编造。
- 客服入口：处理 OCR 识别失败、支付失败、退款和报告争议。
