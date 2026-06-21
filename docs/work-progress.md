# 避坑宝当前工作进度

更新时间：2026-06-21（Asia/Shanghai）

## 当前目标

把避坑宝从可运行原型继续推进到更接近上线的小程序式产品：前端视觉要有信任感和高级感，核心上传、审核、预览、解锁、历史记录链路保持可用，并为真实支付、真实 OCR、合规提审继续预留框架。

当前产品路径调整：网站版先采用免登录上传与订单/报告链路，短信登录后续再补。

收费路径调整：支付宝电脑网站支付受 ICP 备案卡点影响，先采用“收款码付款 + 后台人工确认”的方式验证真实付费意愿。

## 当前代码状态

- 当前本地分支：`main`
- 当前功能提交：`bf37051 Add dual manual payment channels`
- Vercel 项目 `bikengbao` 已连接 GitHub 仓库 `Tomaassfx/bikengbao`，后续 push 到 `main` 会触发 Vercel 自动部署。
- 生产域名保持：`https://bikengbao.lifeadmin-ai.xyz` 和 `https://bikengbao.vercel.app`
- 双收款码功能已推送 GitHub 并手动部署到 Vercel Production。
- 当前生产部署：`dpl_9T4NgYDaCJx2uFMrkBf86BSvDeyP`，状态 `READY`。

## 已完成

### 生产能力框架

- 已补真实微信登录框架：`server/adapters/wechat_auth.py`
- 已补微信支付 JSAPI 下单和回调解锁框架：`server/adapters/payment.py`
- 已补网站版支付宝支付框架：支付宝收银台跳转、异步通知验签、订单轮询和自动解锁。
- 已补扫码付款 + 人工确认支付框架：
  - `BIKENGBAO_PAYMENT_PROVIDER=manual_qr`
  - 用户端支持支付宝/微信双收款码切换、备注码和状态轮询
  - 两张收款码已上传 Vercel Blob，Production/Preview 环境变量已配置
  - `/v1/admin/orders/{orderId}/confirm-payment` 后台确认接口
  - `/admin.html` 内部确认页
  - 后台确认到账后自动解锁报告
- 支付宝、微信两张个人收款码已上传 Vercel Blob，图片不进入公开 GitHub 仓库。
- 临时付款资产上传 token 已删除，上传接口当前不可用；后台确认密钥未重置。
- 已补腾讯云 OCR 调用框架：`server/adapters/ocr.py`
- 已记录腾讯云 OCR 接入路径、实名认证卡点、CAM 子用户密钥方案和生产环境变量：`docs/tencent-ocr-setup.md`
- 已完成腾讯云实名认证、OCR 服务开通、CAM 子用户 `bikengbao-ocr-prod` 创建，并将 OCR 密钥配置到 Vercel Production/Preview。
- 已重新部署生产环境，线上 `/health` 已返回 `ocrProvider=tencent`。
- 已补本地 Vercel 绑定和部署脚本：
  - `.vercel/project.json`
  - `scripts/deploy-vercel.sh`
  - `scripts/vercel-dns-override.cjs`
  - `npm run deploy:vercel`
- 已将本地最新代码同步到 GitHub `Tomaassfx/bikengbao` 的 `main` 分支。
- 已补生产环境变量说明：`docs/production-env.md`
- 已补小程序提审材料清单：`docs/miniprogram-submit-checklist.md`
- 已补合规页面：
  - `legal/privacy.html`
  - `legal/terms.html`
  - `legal/disclaimer.html`

### 前端高级感改造

- 使用 `$design-taste-frontend` 做了 redesign 审计和 pre-flight 检查。
- 网页端统一为低饱和青绿色信任主色，配合赤色风险色，移除原型感较强的紫色/杂蓝色残留。
- 网页首页改为更像“付款前审查工作台”的表达：
  - 更短的首屏价值主张
  - 更明确的风险评分工作台
  - 更克制的审查路径和服务状态侧栏
  - 上传区、表单、报告卡片统一材质和边角系统
- 网页报告页优化：
  - 免费预览和完整报告状态更清晰
  - 付费区根据支付提供方显示“模拟支付并解锁”或“创建微信支付订单”
  - 风险卡、报价概览、话术和家人版总结视觉层级更稳定
- 网页历史页优化：
  - 状态标签从重复 eyebrow 改为功能状态 chip
  - 移动端标题、按钮和删除入口无遮挡
- 小程序端同步视觉语言：
  - 首页增加风险评分与三条典型风险的首屏产品信号
  - 首页、报告页、历史页统一卡片圆角、按钮、背景、主色和风险色

## 已验证

### 命令行检查

- `node --check app.js` 通过
- `node --check miniprogram/pages/home/home.js` 通过
- `node --check miniprogram/pages/report/report.js` 通过
- `node --check miniprogram/pages/history/history.js` 通过
- `python3 -m compileall server api` 通过
- `python3 -m unittest discover -s tests` 通过
- `python3 -m compileall -q server api tests` 通过
- `https://bikengbao.lifeadmin-ai.xyz/health` 返回：`aiProvider=deepseek`、`authProvider=mock`、`ocrProvider=tencent`、`paymentProvider=manual_qr`、`dbProvider=postgres`、`fileStorageProvider=blob`
- `https://bikengbao.vercel.app/health` 返回同样生产状态。
- `git diff --check` 通过
- 机械检查通过：未发现 `—`、旧紫色 `#6d4b7f`、旧蓝色变量、旧 `surface-warm`、旧 `#f4c05e`、明显残留 `border-radius: 8px`
- Vercel Git 连接已验证：部署来源为 GitHub `main`；当前双支付功能提交为 `bf37051 Add dual manual payment channels`，另已手动部署到 Production。
- 线上静态资源已验证：`app.js` 包含 `desk-matrix` / `hydrateMotion`，`styles.css` 包含 `desk-scan` / `page-sweep` / `reveal-ready`。
- 线上 API smoke 已通过：认证、生成预览报告、历史读取、删除测试报告均成功，报告返回 `aiStatus=deepseek_ok`。
- Vercel 最近 2 分钟生产错误日志为空；此前 1 条 504 为本轮第一次 smoke 脚本超时测试产生，后续重跑通过。
- 双收款码单元测试共 7 个，全部通过。
- 生产 API smoke 已验证：订单返回 `alipay`、`wechat` 两个渠道，两个 Blob URL 均匹配，备注码存在。
- 临时付款资产上传接口在线上返回 `401`，确认一次性 token 已删除。

### 浏览器和本地链路验证

- 本地静态服务：`python3 -m http.server 4173`
- 本地 API 服务：`BIKENGBAO_DATA_DIR=/tmp/bikengbao-design-test python3 -m server.run`
- 桌面首屏检查通过：
  - 导航单行
  - CTA 未换行
  - 首页工作台、上传区、表单和侧栏正常渲染
- 移动宽度检查通过：
  - 首屏无横向溢出
  - 导航、CTA、风险工作台、上传区正常折叠
- 本地端到端流程通过：
  - `/health` 返回正常
  - 前端登录 mock 用户成功
  - 创建免费预览报告成功
  - 创建订单成功
  - 模拟支付解锁完整报告成功
  - 完整报告、下载按钮、历史记录页正常渲染
- Chrome 桌面检查通过：
  - 首页首屏、风险仪表盘、上传表单、侧栏状态正常渲染
  - 免费预览、模拟支付解锁、完整报告、历史记录链路正常
- Chrome 移动宽度检查通过：
  - 首页和历史页无明显横向溢出
  - 导航、CTA、历史操作按钮没有挤出容器
- 双收款码浏览器检查通过：
  - 支付宝默认选中，二维码和收款方正确
  - 切换微信后二维码 URL、收款方和选中状态同步变化
  - 桌面无控制台错误；390px 移动宽度无横向溢出

## 当前未完成

### 网站人工收费上线阻塞项

1. 用户身份隔离：当前 `authProvider=mock`，网页统一提交 `web-demo`，不同用户可能共享或丢失报告历史。公开收费前必须改成稳定的匿名会话，后续再升级短信登录。
2. 后台确认密钥：Vercel 中已有加密值，但运营方未掌握明文。本轮按要求未重置，因此暂时无法使用 `/admin.html` 人工确认订单。
3. 真实付款闭环：需要用一笔最低 29 元真实订单验证扫码、备注码、后台确认和报告解锁。
4. 合规信息：隐私政策、用户协议仍需填写真实运营主体、发布日期、客服联系方式和退款规则。
5. 接口防刷：文件上传、腾讯 OCR、DeepSeek 和报告生成接口仍缺少生产限流与成本保护。

### 后续自动支付与小程序

- 若后续恢复支付宝自动收款，支付宝真实支付仍需验证：
  - 支付宝应用已上线或沙箱可用
  - 电脑网站支付/手机网站支付产品已开通
  - 用沙箱或小额真实订单跑通 `/v1/payments/alipay/notify` 异步通知和自动解锁
- 真实微信登录需要提供：
  - `WECHAT_APP_ID`
  - `WECHAT_APP_SECRET`
- 真实微信支付需要提供：
  - `WECHAT_MCH_ID`
  - `WECHAT_PAY_SERIAL_NO`
  - 商户私钥 PEM
  - `WECHAT_PAY_API_V3_KEY`
  - 微信支付平台证书 PEM
  - 支付回调地址
- 真实 OCR 已接入腾讯云：
  - `BIKENGBAO_OCR_PROVIDER=tencent`
  - `TENCENT_OCR_REGION=ap-guangzhou`
  - `TENCENT_OCR_ACTION=GeneralBasicOCR`
  - 密钥已配置到 Vercel，不写入仓库
- 小程序正式提审仍需补：
  - 运营主体信息
  - 客服联系方式
  - 服务类目确认
  - 隐私政策发布日期和主体名称
  - 小程序后台 request/upload/download 合法域名配置

## 下一步建议

1. 先实现网站匿名用户隔离，阻止不同用户互相看到报告。
2. 运营方准备好保存密钥后，再重置 `BIKENGBAO_ADMIN_CONFIRM_TOKEN`。
3. 用一笔 29 元真实付款验证扫码、备注码、后台确认和报告解锁。
4. 填写运营主体、客服、发布日期、退款规则，并增加接口限流后再公开投放。
5. 增加访问、上传、预览、支付点击、支付成功、复制话术等关键埋点。

## 最近一轮功能改动范围

- 支付渠道和后端：`server/adapters/payment.py`、`server/app.py`、`server/config.py`
- 网页和小程序支付界面：`app.js`、`styles.css`、`miniprogram/pages/report/*`
- 配置和文档：`.env.example`、`docs/api.md`、`docs/production-env.md`、`docs/production-checklist.md`、`docs/work-progress.md`
- 测试：`tests/test_manual_payment.py`
