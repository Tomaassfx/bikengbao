# 避坑宝当前工作进度

更新时间：2026-06-03 19:48（Asia/Shanghai）

## 当前目标

把避坑宝从“可演示网页”继续推进到更接近上线的小程序式产品框架：优化前端体验、增强代码健壮性、本地验证后部署到 Vercel，并记录剩余上线事项。

## 已完成

- 已接入生产侧基础资源：
  - Vercel 项目：`bikengbao`
  - 线上域名：`https://bikengbao.lifeadmin-ai.xyz`
  - 备用域名：`https://bikengbao.vercel.app`
  - Neon Postgres：用于用户、报告、订单、文件元数据
  - Vercel Blob：用于上传资料对象存储
  - DeepSeek API Key：已配置在 Vercel 环境变量中
- 已完成第一轮 UI/UX 升级：
  - 首页改为更接近产品工作台的布局
  - 增加审核能力摘要、服务状态、审核步骤面板
  - 增加文件大小展示、表单错误提示、忙碌遮罩、Toast 动效
  - 报告页增加风险分布展示
  - 增强移动端适配，已确认窄屏无横向溢出
- 已完成前端健壮性补强：
  - API 请求增加 30 秒超时
  - 识别 JSON/非 JSON 响应
  - 网络断开和超时给出可读错误
  - 提交前校验城市、面积、预算、资料内容
  - 删除历史报告前增加确认
- 已完成后端健壮性补强：
  - 上传接口增加 `Content-Length` 大小限制
  - 默认最大上传体积为 12 MB，可通过 `BIKENGBAO_MAX_UPLOAD_BYTES` 配置
  - JSON 解析异常不再直接导致服务崩溃
- 已完成本轮生产部署：
  - 生产域名：`https://bikengbao.lifeadmin-ai.xyz`
  - Vercel 默认域名：`https://bikengbao.vercel.app`
  - 部署 ID：`dpl_Fuc4dr3pyzhGGY32YEzgTrjipQoL`

## 已验证

- 本地静态检查：
  - `node --check app.js` 通过
  - `python3 -m compileall server api` 通过
- 本地浏览器验证：
  - 首页可打开
  - 桌面首屏可访问树确认关键 UI、表单、服务状态和审核步骤正常渲染
  - 示例文本可生成免费预览
  - 模拟支付可解锁完整报告
  - 报告页可展示完整风险、报价概览、追问清单、下一步建议、话术和家人版总结
  - 移动窄屏宽度下无横向滚动
- 生产环境验证：
  - `/health` 返回 `deepseek`、`postgres`、`blob`
  - 文件上传成功
  - DeepSeek 参与生成报告，返回 `aiStatus=deepseek_ok`
  - 免费预览返回 3 条风险
  - 订单创建成功
  - 模拟支付后完整报告解锁
  - 历史报告读取成功

## 当前未完成

- 尚未接入真实 OCR。
- 尚未接入真实微信登录和微信支付。
- 尚未补隐私政策、用户协议和小程序后台域名白名单。
- Chrome 坐标点击工具在当前屏幕缩放下有落点误差，本轮已用 API 冒烟和可访问树复核替代完整页面自动点击。

## 下一步建议

1. 继续补上线前关键能力：
   - 微信小程序登录与用户身份绑定
   - 微信支付或合规支付链路
   - OCR 服务接入
   - 文件隐私、删除、脱敏策略
   - 管理后台和人工复核入口
2. 增加自动化测试脚本，覆盖健康检查、上传、生成报告、订单、解锁和历史记录。
3. 恢复或切换浏览器自动化工具后，补一轮完整桌面/移动截图回归。

## 代码改动范围

- `app.js`
- `styles.css`
- `server/app.py`
- `server/config.py`
- `docs/work-progress.md`
