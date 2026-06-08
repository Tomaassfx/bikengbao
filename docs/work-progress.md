# 避坑宝当前工作进度

更新时间：2026-06-08 19:36（Asia/Shanghai）

## 当前目标

把避坑宝从可运行原型继续推进到更接近上线的小程序式产品：前端视觉要有信任感和高级感，核心上传、审核、预览、解锁、历史记录链路保持可用，并为真实支付、真实 OCR、合规提审继续预留框架。

## 当前代码状态

- 当前本地分支：`main`
- 最新本地基础提交：`338b1df Add production payment OCR and compliance framework`
- 当前还有一轮前端高级感改造改动，准备本地提交保存
- 生产站点仍需重新部署后才会包含本轮前端改造

## 已完成

### 生产能力框架

- 已补真实微信登录框架：`server/adapters/wechat_auth.py`
- 已补微信支付 JSAPI 下单和回调解锁框架：`server/adapters/payment.py`
- 已补腾讯云 OCR 调用框架：`server/adapters/ocr.py`
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
- `git diff --check` 通过
- 机械检查通过：未发现 `—`、旧紫色 `#6d4b7f`、旧蓝色变量、旧 `surface-warm`、旧 `#f4c05e`、明显残留 `border-radius: 8px`

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

## 当前未完成

- 本轮前端改造尚未部署到 Vercel 生产环境。
- 远端 GitHub 同步仍依赖可用的 GitHub 写入方式或本机 Git 凭据。
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

1. 提交并同步本轮前端高级感改造。
2. 重新部署最新代码到 Vercel。
3. 在 Vercel 配置微信登录、微信支付、腾讯 OCR 的生产环境变量。
4. 用微信开发者工具跑小程序真机预览。
5. 准备提审材料并补齐小程序后台域名白名单。

## 本轮改动范围

- `app.js`
- `styles.css`
- `miniprogram/app.wxss`
- `miniprogram/pages/home/home.wxml`
- `miniprogram/pages/home/home.wxss`
- `miniprogram/pages/report/report.wxss`
- `miniprogram/pages/history/history.wxss`
- `docs/work-progress.md`
