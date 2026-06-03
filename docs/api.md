# API 约定

默认地址：`http://127.0.0.1:8787`

Vercel 部署后默认同源访问：

- `GET /health`
- `POST /v1/auth/wechat`
- `POST /v1/files`
- `POST /v1/audits`
- `POST /v1/orders`
- `POST /v1/orders/{orderId}/mock-pay`
- `GET /v1/reports`
- `GET /v1/reports/{reportId}`
- `DELETE /v1/reports/{reportId}`

`GET /health` 会返回当前适配器状态，不包含任何密钥：

```json
{
  "ok": true,
  "service": "bikengbao-api",
  "aiProvider": "deepseek",
  "ocrProvider": "mock",
  "paymentProvider": "mock",
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
{ "reportId": "report_id", "amount": 59 }
```

开发环境模拟支付：

`POST /v1/orders/{orderId}/mock-pay`

正式上线时，将 `server/adapters/payment.py` 替换为微信支付参数生成和回调验签。
