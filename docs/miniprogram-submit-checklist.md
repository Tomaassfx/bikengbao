# 微信小程序提审清单

## 账号与主体

- 微信小程序 AppID。
- 小程序主体名称、营业执照或个人主体信息。
- 管理员微信、开发者权限。
- 类目建议：生活服务、工具、家装相关类目。最终以微信后台可选类目为准。

## 服务器域名

- request 合法域名：`https://bikengbao.lifeadmin-ai.xyz`
- uploadFile 合法域名：`https://bikengbao.lifeadmin-ai.xyz`
- downloadFile 合法域名：如后续直接下载报告或文件，再补对应域名。

## 页面与材料

- 首页截图：上传报价单，查装修坑。
- 报告页截图：风险明细、追问清单、免责声明。
- 历史记录截图：删除资料入口。
- 用户协议链接：`https://bikengbao.lifeadmin-ai.xyz/legal/terms.html`
- 隐私政策链接：`https://bikengbao.lifeadmin-ai.xyz/legal/privacy.html`
- 免责声明链接：`https://bikengbao.lifeadmin-ai.xyz/legal/disclaimer.html`

## 隐私接口

- 明示收集资料类型：报价单、合同、户型图、聊天截图、城市、面积、预算。
- 明示用途：OCR、AI 分析、报告生成、订单支付、售后处理。
- 删除机制：历史记录删除报告并同步删除关联文件。

## 支付

- 微信支付商户号。
- JSAPI 支付产品权限。
- 支付回调地址：`https://bikengbao.lifeadmin-ai.xyz/v1/payments/wechat/notify`
- 退款和客服说明。

## 提审前自测

- 真机上传图片。
- 生成免费预览。
- 发起微信支付。
- 支付成功后等待回调解锁报告。
- 删除历史资料。
- 隐私政策、用户协议、免责声明可打开。
