# API 约定

默认地址：`http://127.0.0.1:8787`

Vercel 部署后默认同源访问：

- `GET /health`
- `POST /v1/auth/wechat`
- `POST /v1/files`
- `POST /v1/audits`
- `POST /v1/orders`
- `GET /v1/orders/{orderId}`
- `POST /v1/orders/{orderId}/mock-pay`
- `POST /v1/admin/orders/{orderId}/confirm-payment`
- `POST /v1/payments/wechat/notify`
- `POST /v1/payments/alipay/notify`
- `GET /v1/reports`
- `GET /v1/reports/{reportId}`
- `DELETE /v1/reports/{reportId}`

`GET /health` 会返回当前适配器状态，不包含任何密钥：

```json
{
  "ok": true,
  "service": "bikengbao-api",
  "authProvider": "wechat",
  "aiProvider": "deepseek",
  "ocrProvider": "tencent",
  "paymentProvider": "manual_qr",
  "dbProvider": "postgres",
  "fileStorageProvider": "blob"
}
```

## 鉴权

小程序启动后调用：

`POST /v1/auth/wechat`

请求：

```json
{ "code": "wx.login 返回的 code" }
```

响应：

```json
{
  "token": "demo-token-wx_xxx",
  "user": { "id": "wx_xxx", "nickname": "避坑宝用户" }
}
```

正式微信登录启用条件：

- `BIKENGBAO_AUTH_PROVIDER=wechat`
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

后续请求 Header：

```http
Authorization: Bearer demo-token-wx_xxx
```

## 文件上传

`POST /v1/files`

`multipart/form-data`：

- `file`：图片、PDF、聊天截图。
- `docType`：报价单、合同、户型图、聊天记录。
- `filename`：原始文件名。

响应：

```json
{
  "file": {
    "id": "file_id",
    "filename": "quote.pdf",
    "docType": "报价单",
    "ocrText": "mock OCR text"
  }
}
```

## 生成审核

`POST /v1/audits`

请求：

```json
{
  "docType": "报价单",
  "city": "上海",
  "area": "89",
  "homeType": "二手房翻新",
  "stage": "已拿到报价，准备付款",
  "budget": "128000",
  "vendor": "某装修公司",
  "ocrText": "合同和报价文本",
  "fileIds": ["file_id"]
}
```

响应。未支付时只返回 3 条风险预览；`aiStatus` 用于线上测试 DeepSeek 是否真正参与：

```json
{
  "report": {
    "id": "report_id",
    "unlocked": false,
    "aiStatus": "deepseek_ok",
    "risks": []
  }
}
```

`aiStatus` 取值：

- `mock`：未配置真实 AI，使用规则引擎报告。
- `deepseek_ok`：DeepSeek 调用成功，并增强了家人版总结、追问清单、话术或下一步建议。
- `deepseek_error`：DeepSeek 调用失败，接口仍返回规则报告，同时带 `aiError` 方便排查。

## 报告

列表：

`GET /v1/reports`

详情：

`GET /v1/reports/{reportId}`

删除报告与关联资料：

`DELETE /v1/reports/{reportId}`

## 订单与支付

创建订单：

`POST /v1/orders`

```json
{ "reportId": "report_id", "amount": 59, "clientType": "web" }
```

查询订单状态：

`GET /v1/orders/{orderId}`

网站端用于轮询支付状态。订单支付成功后，响应会包含已解锁报告。

开发环境模拟支付：

`POST /v1/orders/{orderId}/mock-pay`

仅当 `BIKENGBAO_PAYMENT_PROVIDER=mock` 时允许调用。正式支付环境会拒绝该接口，避免绕过真实支付。

扫码付款 + 人工确认：

`BIKENGBAO_PAYMENT_PROVIDER=manual_qr` 时，`POST /v1/orders` 会返回：

```json
{
  "payment": {
    "mode": "manual_qr",
    "qrImageUrl": "https://example.com/receipt-qr.png",
    "accountName": "避坑宝运营",
    "accountHint": "支付宝或微信收款码",
    "reference": "BKB-ORDER1234",
    "amountText": "59.00",
    "instructions": ["付款备注请填写：BKB-ORDER1234"]
  }
}
```

后台人工确认到账：

`POST /v1/admin/orders/{orderId}/confirm-payment`

Header：

```http
Authorization: Bearer <BIKENGBAO_ADMIN_CONFIRM_TOKEN>
```

请求：

```json
{ "paidAmount": 59, "transactionId": "收款流水号", "note": "备注码匹配" }
```

确认成功后订单变为 `paid`，对应报告会自动解锁。生产环境需要配置：

- `BIKENGBAO_PAYMENT_PROVIDER=manual_qr`
- `MANUAL_PAYMENT_QR_IMAGE_URL`
- `MANUAL_PAYMENT_ACCOUNT_NAME`
- `MANUAL_PAYMENT_ACCOUNT_HINT`
- `MANUAL_PAYMENT_NOTE_PREFIX`
- `BIKENGBAO_ADMIN_CONFIRM_TOKEN`

内部确认页：`/admin.html`。该页面不挂前台导航，必须输入后台确认密钥才能操作。

微信支付回调：

`POST /v1/payments/wechat/notify`

正式上线需要配置：

- `BIKENGBAO_PAYMENT_PROVIDER=wechat`
- `WECHAT_APP_ID`
- `WECHAT_MCH_ID`
- `WECHAT_PAY_SERIAL_NO`
- `WECHAT_PAY_PRIVATE_KEY` 或 `WECHAT_PAY_PRIVATE_KEY_PATH`
- `WECHAT_PAY_API_V3_KEY`
- `WECHAT_PAY_PLATFORM_CERT` 或 `WECHAT_PAY_PLATFORM_CERT_PATH`
- `WECHAT_PAY_NOTIFY_URL`

支付宝网站支付回调：

`POST /v1/payments/alipay/notify`

正式上线需要配置：

- `BIKENGBAO_PAYMENT_PROVIDER=alipay`
- `ALIPAY_APP_ID`
- `ALIPAY_APP_PRIVATE_KEY` 或 `ALIPAY_APP_PRIVATE_KEY_PATH`
- `ALIPAY_PUBLIC_KEY` 或 `ALIPAY_PUBLIC_KEY_PATH`
- `ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do`
- `ALIPAY_NOTIFY_URL=https://bikengbao.lifeadmin-ai.xyz/v1/payments/alipay/notify`
- `ALIPAY_RETURN_URL=https://bikengbao.lifeadmin-ai.xyz/`

## OCR

腾讯云 OCR 启用条件：

- `BIKENGBAO_OCR_PROVIDER=tencent`
- `TENCENT_SECRET_ID`
- `TENCENT_SECRET_KEY`
- `TENCENT_OCR_REGION`
- `TENCENT_OCR_ACTION`
