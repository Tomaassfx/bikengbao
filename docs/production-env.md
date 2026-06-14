# 生产环境变量

## 已配置或已验证

- `BIKENGBAO_AI_PROVIDER=deepseek`
- `DEEPSEEK_API_KEY`
- `BIKENGBAO_DB_PROVIDER=postgres`
- `DATABASE_URL`
- `BIKENGBAO_FILE_STORAGE_PROVIDER=blob`
- `BLOB_READ_WRITE_TOKEN`
- 当前收费闭环先切到扫码付款 + 人工确认：`BIKENGBAO_PAYMENT_PROVIDER=manual_qr`，并通过后台确认密钥解锁报告。
- `https://bikengbao.lifeadmin-ai.xyz/health` 已验证返回 `dbProvider=postgres`、`fileStorageProvider=blob`。

## 微信登录

- `BIKENGBAO_AUTH_PROVIDER=wechat`
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

## 微信支付 JSAPI

- `BIKENGBAO_PAYMENT_PROVIDER=wechat`
- `WECHAT_APP_ID`
- `WECHAT_MCH_ID`
- `WECHAT_PAY_SERIAL_NO`
- `WECHAT_PAY_PRIVATE_KEY` 或 `WECHAT_PAY_PRIVATE_KEY_PATH`
- `WECHAT_PAY_API_V3_KEY`
- `WECHAT_PAY_PLATFORM_CERT` 或 `WECHAT_PAY_PLATFORM_CERT_PATH`
- `WECHAT_PAY_NOTIFY_URL=https://bikengbao.lifeadmin-ai.xyz/v1/payments/wechat/notify`

## 支付宝网站支付

- `BIKENGBAO_PAYMENT_PROVIDER=alipay`
- `ALIPAY_APP_ID`
- `ALIPAY_APP_PRIVATE_KEY` 或 `ALIPAY_APP_PRIVATE_KEY_PATH`
- `ALIPAY_PUBLIC_KEY` 或 `ALIPAY_PUBLIC_KEY_PATH`
- `ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do`
- `ALIPAY_NOTIFY_URL=https://bikengbao.lifeadmin-ai.xyz/v1/payments/alipay/notify`
- `ALIPAY_RETURN_URL=https://bikengbao.lifeadmin-ai.xyz/`

## 扫码付款 + 人工确认

- `BIKENGBAO_PAYMENT_PROVIDER=manual_qr`
- `MANUAL_PAYMENT_QR_IMAGE_URL`
- `MANUAL_PAYMENT_ACCOUNT_NAME=避坑宝运营`
- `MANUAL_PAYMENT_ACCOUNT_HINT=支付宝或微信收款码`
- `MANUAL_PAYMENT_NOTE_PREFIX=BKB`
- `MANUAL_PAYMENT_EXPIRES_MINUTES=30`
- `BIKENGBAO_ADMIN_CONFIRM_TOKEN`

后台确认页：

- `https://bikengbao.lifeadmin-ai.xyz/admin.html`

确认接口：

- `POST /v1/admin/orders/{orderId}/confirm-payment`
- Header：`Authorization: Bearer <BIKENGBAO_ADMIN_CONFIRM_TOKEN>`

## 腾讯云 OCR

- `BIKENGBAO_OCR_PROVIDER=tencent`
- `TENCENT_SECRET_ID`
- `TENCENT_SECRET_KEY`
- `TENCENT_OCR_REGION=ap-guangzhou`
- `TENCENT_OCR_ACTION=GeneralBasicOCR`

## 安全提醒

- 不要把任何密钥写入 GitHub、小程序前端、README 截图或聊天记录。
- Vercel 环境变量建议按 Production、Preview、Development 分开配置。
- 微信支付私钥和平台证书如使用环境变量，换行可写成 `\n`。
- 本地支付宝私钥文件只用于生成 Vercel 环境变量，不提交到 GitHub。
