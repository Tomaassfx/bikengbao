# 避坑宝当前工作进度

更新时间：2026-06-10 23:34（Asia/Shanghai）

## 当前目标

把避坑宝从可运行原型继续推进到更接近上线的小程序式产品：前端视觉要有信任感和高级感，核心上传、审核、预览、解锁、历史记录链路保持可用，并为真实支付、真实 OCR、合规提审继续预留框架。

## 当前代码状态

- 当前本地分支：`main`
- 本轮前端动效优化基于提交：`1701f64 Record latest Vercel deployment status`
- Vercel 项目 `bikengbao` 已连接 GitHub 仓库 `Tomaassfx/bikengbao`，后续 push 到 `main` 会触发 Vercel 自动部署。
- 生产域名保持：`https://bikengbao.lifeadmin-ai.xyz` 和 `https://bikengbao.vercel.app`
- 本轮改动已推送 GitHub，并通过 Vercel Git 自动部署到生产环境。

## 已完成

### 生产能力框架

- 已补真实微信登录框架：`server/adapters/wechat_auth.py`
- 已补微信支付 JSAPI 下单和回调解锁框架：`server/adapters/payment.py`
- 已补网站版支付宝支付框架：支付宝收银台跳转、异步通知验签、订单轮询和自动解锁。
- 已在 Vercel 项目 `bikengbao` 添加支付宝生产变量，并验证线上 `/health` 返回 `paymentProvider=alipay`。
- 已补腾讯云 OCR 调用框架：`server/adapters/ocr.py`
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
- `https://bikengbao.lifeadmin-ai.xyz/health` 返回：`aiProvider=deepseek`、`ocrProvider=mock`、`paymentProvider=alipay`、`dbProvider=postgres`、`fileStorageProvider=blob`
- `https://bikengbao.vercel.app/health` 返回同样生产状态。
- `git diff --check` 通过
- 机械检查通过：未发现 `—`、旧紫色 `#6d4b7f`、旧蓝色变量、旧 `surface-warm`、旧 `#f4c05e`、明显残留 `border-radius: 8px`
- Vercel 自动部署已验证：部署来源为 GitHub `main`，本轮功能提交信息为 `Polish premium audit UI motion`。
- 线上静态资源已验证：`app.js` 包含 `desk-matrix` / `hydrateMotion`，`styles.css` 包含 `desk-scan` / `page-sweep` / `reveal-ready`。
- 线上 API smoke 已通过：认证、生成预览报告、历史读取、删除测试报告均成功，报告返回 `aiStatus=deepseek_ok`。
- Vercel 最近 2 分钟生产错误日志为空；此前 1 条 504 为本轮第一次 smoke 脚本超时测试产生，后续重跑通过。

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

## 当前未完成

- 若先做网站版收费，支付宝真实支付仍需验证：
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
- 真实 OCR 需要提供：
  - `TENCENT_SECRET_ID`
  - `TENCENT_SECRET_KEY`
  - OCR 地域和具体接口选择
- 小程序正式提审仍需补：
  - 运营主体信息
  - 客服联系方式
  - 服务类目确认
  - 隐私政策发布日期和主体名称
  - 小程序后台 request/upload/download 合法域名配置

## 下一步建议

1. 配置腾讯 OCR 生产变量，验证 `ocrProvider=tencent`。
2. 用支付宝沙箱或小额真实订单验证付款后自动解锁报告。
3. 增加访问、上传、预览、支付点击、支付成功、复制话术等关键埋点。
4. 明确运营主体、客服、隐私政策发布日期后再做正式投放或小程序提审。

## 本轮改动范围

- `app.js`
- `styles.css`
- `docs/work-progress.md`
- `docs/production-checklist.md`
