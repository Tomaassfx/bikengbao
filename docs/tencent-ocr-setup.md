# 腾讯云 OCR 接入记录

更新时间：2026-06-14（Asia/Shanghai）

## 当前结论

避坑宝网站版先走免登录上传和报告解锁，短信登录后续再补。真实 OCR 先接腾讯云文字识别，V1 推荐使用“通用印刷体识别”接口：

- 控制台入口：https://console.cloud.tencent.com/ocr/general
- API 文档：https://cloud.tencent.com/document/product/866/33526
- 请求域名：`ocr.tencentcloudapi.com`
- 接口版本：`2018-11-19`
- V1 接口动作：`GeneralBasicOCR`
- 默认地域：`ap-guangzhou`

V1 先用 `GeneralBasicOCR` 的原因：它能覆盖报价单照片、合同截图、聊天截图、PDF 单页等通用文字提取场景，成本和集成复杂度低。后续如果报价单表格结构化质量不够，再升级表格识别或高精度识别。

## 今天在腾讯云控制台看到的状态

- OCR 控制台已能打开到“通用文字识别”产品页。
- 腾讯云账号已完成实名认证。
- 文字识别 OCR 服务已完成开通。
- API 密钥管理页可打开：https://console.cloud.tencent.com/cam/capi
- 腾讯云密钥页明确提示：不建议使用主账号 API 访问密钥，建议改用子用户密钥或临时凭证。
- 密钥页提示：为降低密钥泄漏风险，`SecretKey` 自 2023-11-30 起仅支持创建时查看和保存，之后不能再次查询。
- 已创建 CAM 子用户 `bikengbao-ocr-prod`，访问方式为“编程访问”，授权策略为 `QcloudOCRReadOnlyaccess`。
- 腾讯云 OCR 密钥已配置到 Vercel Production 和 Preview 环境变量；密钥值不写入仓库文档。

账号 ID、密钥值、实名信息不记录到仓库文档，避免未来同步 GitHub 时公开暴露。

## 需要你完成或提供的东西

当前腾讯云 OCR 接入已完成，不再需要你额外提供 OCR 密钥。

不要把 `SecretKey` 发到 GitHub、前端代码、README、截图或公开聊天里。给我配置时，最好只用于 Vercel 环境变量；如果必须发在聊天里，用完后建议在腾讯云轮换一次。

## Vercel 需要配置的环境变量

```bash
BIKENGBAO_OCR_PROVIDER=tencent
TENCENT_SECRET_ID=<腾讯云 CAM 子用户 SecretId>
TENCENT_SECRET_KEY=<腾讯云 CAM 子用户 SecretKey>
TENCENT_OCR_REGION=ap-guangzhou
TENCENT_OCR_ACTION=GeneralBasicOCR
```

配置完成后，需要重新部署 Vercel。上线验证以 `/health` 返回 `ocrProvider=tencent` 为准。

当前状态：Vercel Production/Preview 已配置并重新部署，线上 `/health` 已返回 `ocrProvider=tencent`。

## 当前代码如何调用 OCR

代码位置：`server/adapters/ocr.py`

- 如果上传文件已进入对象存储并有 `blobUrl`，服务端会把 `ImageUrl` 发给腾讯云 OCR。
- 如果本地存在文件路径，则会把文件转成 `ImageBase64` 发送。
- 腾讯云返回 `TextDetections` 后，系统会提取每一行的 `DetectedText` 拼成报告分析文本。

注意：腾讯云文档要求图片或 PDF Base64 不超过 10M；如果用 `ImageUrl`，腾讯云需要能在短时间内下载到文件。线上 Vercel Blob 地址需要保持可公开读取或至少腾讯云可访问。

## 后续升级方向

- 报价单照片、合同截图、聊天截图：继续使用 `GeneralBasicOCR`。
- 模糊小字、长串数字较多的报价单：评估高精度通用 OCR。
- 表格型报价单：评估表格识别或文档智能 OCR。
- 多页 PDF：先做逐页识别，再合并文本；V1 当前先按单页或图片优先验证。

## 完成后我可以继续做的验证

已完成：

1. 腾讯云 OCR 环境变量已写入 Vercel Production/Preview。
2. 已重新部署生产环境。
3. `/health` 已切到 `ocrProvider=tencent`。
4. 已上传测试报价单图片，确认 OCR 返回真实识别文本。
5. 已用 OCR 文本生成测试报告，返回 `aiStatus=deepseek_ok`。
6. 已删除测试报告和关联测试文件。

后续如果真实用户上传的报价单识别效果不稳定，再决定是否切高精度 OCR 或表格 OCR。
