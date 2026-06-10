# 支付宝网站支付接入清单

## 需要在支付宝后台准备

- 支付宝开放平台网页/移动应用。
- 已开通的电脑网站支付，建议同时开通手机网站支付。
- `ALIPAY_APP_ID`：应用详情里的 APPID。
- `ALIPAY_APP_PRIVATE_KEY`：使用支付宝开放平台开发助手生成，自己保存。
- `ALIPAY_PUBLIC_KEY`：把应用公钥上传到支付宝后，在支付宝后台复制支付宝公钥。

## Vercel 环境变量

```env
BIKENGBAO_PAYMENT_PROVIDER=alipay
ALIPAY_APP_ID=
ALIPAY_APP_PRIVATE_KEY=
ALIPAY_PUBLIC_KEY=
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
ALIPAY_NOTIFY_URL=https://bikengbao.lifeadmin-ai.xyz/v1/payments/alipay/notify
ALIPAY_RETURN_URL=https://bikengbao.lifeadmin-ai.xyz/
```

## 联调验证

1. 访问网站并生成免费预览报告。
2. 点击支付宝付款并解锁。
3. 确认打开支付宝收银台。
4. 完成沙箱或小额真实支付。
5. 等待 `/v1/payments/alipay/notify` 收到支付宝异步通知。
6. 前端轮询 `/v1/orders/{orderId}`，订单变为 `paid`。
7. 报告自动解锁完整内容。

## 注意

- 应用私钥只能放服务端环境变量，不能写入前端、小程序、GitHub 或文档截图。
- 支付成功必须以支付宝异步通知验签为准，不能只看浏览器同步跳转。
- `ALIPAY_RETURN_URL` 回跳只用于用户体验，自动解锁依赖 `ALIPAY_NOTIFY_URL`。
