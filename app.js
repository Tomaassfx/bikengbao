const isLocalStaticPreview =
  ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname) && window.location.port === "4173";
const API_BASE_URL = window.BIKENGBAO_API_BASE_URL || (isLocalStaticPreview ? "http://127.0.0.1:8787" : window.location.origin);
const REQUEST_TIMEOUT_MS = 30000;
const PRICE_OPTIONS = [29, 59, 99];
const REVIEW_STEPS = [
  ["资料解析", "识别报价项、合同条款和用户补充文本"],
  ["风险归类", "拆出报价、合同、增项和沟通风险"],
  ["行动建议", "生成追问清单、话术和家人版摘要"]
];
const SAMPLE_TEXT =
  "合同约定签约付 70%，水电按实际发生结算，主材升级另计，材料以现场为准。拆除、垃圾清运、成品保护、管理费另计。延期赔付双方协商，防水闭水验收标准未列明。";

const state = {
  activeView: "audit",
  files: [],
  uploadedFileIds: [],
  report: null,
  history: [],
  unlocked: false,
  pendingOrder: null,
  selectedPrice: 59,
  isBusy: false,
  busyLabel: "",
  toast: "",
  errors: {},
  token: localStorage.getItem("bikengbao_token") || "",
  service: null,
  form: {
    docType: "报价单",
    city: "上海",
    area: "89",
    homeType: "二手房翻新",
    stage: "已拿到报价，准备付款",
    budget: "128000",
    vendor: "某装修公司",
    ocrText:
      "水电改造按实际发生结算，材料品牌以现场为准。拆除 9000 元，墙面刷新 18000 元，防水 8500 元，瓷砖铺贴 26000 元，橱柜和全屋定制另计。付款节点：签约付 60%，水电验收付 30%，竣工付 10%。延期赔付双方协商。"
  }
};

function setBusy(isBusy, label = "") {
  state.isBusy = isBusy;
  state.busyLabel = label;
  render();
}

function setToast(message) {
  state.toast = message;
  render();
  window.clearTimeout(setToast.timer);
  setToast.timer = window.setTimeout(() => {
    state.toast = "";
    render();
  }, 3200);
}

async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), options.timeout || REQUEST_TIMEOUT_MS);
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    ...(options.headers || {})
  };
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, signal: controller.signal });
    const isJson = response.headers.get("content-type")?.includes("application/json");
    const payload = isJson ? await response.json().catch(() => ({})) : {};
    if (!response.ok) {
      throw new Error(payload.message || `请求失败：${response.status}`);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("请求超时，请稍后再试。");
    if (!navigator.onLine) throw new Error("当前网络不可用，请检查连接后重试。");
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function ensureAuth() {
  if (state.token) return;
  const payload = await apiRequest("/v1/auth/wechat", {
    method: "POST",
    body: JSON.stringify({ code: "web-demo" })
  });
  state.token = payload.token;
  localStorage.setItem("bikengbao_token", payload.token);
}

async function loadServiceStatus() {
  try {
    state.service = await apiRequest("/health");
  } catch {
    state.service = { ok: false, service: "bikengbao-api" };
  }
}

async function loadHistory() {
  try {
    await ensureAuth();
    const payload = await apiRequest("/v1/reports");
    state.history = payload.reports || [];
  } catch (error) {
    setToast(error.message || "历史记录加载失败");
  }
}

async function uploadSelectedFiles() {
  const ids = [];
  for (const file of state.files) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("docType", state.form.docType);
    const payload = await apiRequest("/v1/files", {
      method: "POST",
      body: formData
    });
    ids.push(payload.file.id);
  }
  state.uploadedFileIds = ids;
  return ids;
}

async function generateReport() {
  const errors = validateAuditForm();
  state.errors = errors;
  if (Object.keys(errors).length) {
    render();
    setToast("请先补齐高亮字段。");
    return;
  }
  try {
    setBusy(true, state.files.length ? "上传资料并生成报告中..." : "生成报告中...");
    await ensureAuth();
    const fileIds = await uploadSelectedFiles();
    const payload = await apiRequest("/v1/audits", {
      method: "POST",
      body: JSON.stringify({ ...state.form, fileIds })
    });
    state.report = payload.report;
    state.unlocked = Boolean(payload.report.unlocked);
    state.activeView = "report";
    await loadHistory();
    setToast(payload.report.aiStatus === "deepseek_ok" ? "DeepSeek 已参与生成报告。" : "已生成免费预览。");
  } catch (error) {
    setToast(error.message || "生成报告失败");
  } finally {
    setBusy(false);
  }
}

async function unlockReport() {
  if (!state.report) return;
  let paymentWindow = null;
  try {
    const provider = state.service?.paymentProvider || "mock";
    if (provider === "alipay") {
      paymentWindow = window.open("", "_blank", "noopener,noreferrer");
    }
    setBusy(true, provider === "alipay" ? "创建支付宝订单..." : "创建订单并解锁报告...");
    await ensureAuth();
    const orderPayload = await apiRequest("/v1/orders", {
      method: "POST",
      body: JSON.stringify({
        reportId: state.report.id,
        amount: state.selectedPrice,
        clientType: detectClientType()
      })
    });

    if (orderPayload.payment?.mode === "alipay") {
      state.pendingOrder = {
        id: orderPayload.order.id,
        amount: orderPayload.order.amount,
        paymentUrl: orderPayload.payment.paymentUrl
      };
      if (paymentWindow && orderPayload.payment.paymentUrl) {
        paymentWindow.location.href = orderPayload.payment.paymentUrl;
      } else if (paymentWindow) {
        paymentWindow.close();
      }
      setBusy(false);
      render();
      setToast("支付宝收银台已打开，付款成功后会自动解锁报告。");
      pollOrder(orderPayload.order.id);
      return;
    }

    if (orderPayload.payment?.mode === "wechat") {
      if (paymentWindow) paymentWindow.close();
      setToast("已创建微信支付订单，请在小程序内完成支付。");
      return;
    }
    if (paymentWindow) paymentWindow.close();

    const paidPayload = await apiRequest(`/v1/orders/${orderPayload.order.id}/mock-pay`, {
      method: "POST",
      body: JSON.stringify({})
    });
    state.report = paidPayload.report;
    state.unlocked = Boolean(paidPayload.report.unlocked);
    await loadHistory();
    setToast(`已模拟支付 ${state.selectedPrice} 元，完整报告已解锁。`);
  } catch (error) {
    if (paymentWindow) paymentWindow.close();
    setToast(error.message || "解锁失败");
  } finally {
    setBusy(false);
  }
}

async function pollOrder(orderId, attempts = 45) {
  for (let index = 0; index < attempts; index += 1) {
    await wait(2000);
    try {
      const payload = await apiRequest(`/v1/orders/${orderId}`);
      if (payload.order?.status === "paid") {
        state.pendingOrder = null;
        state.report = payload.report;
        state.unlocked = Boolean(payload.report?.unlocked);
        await loadHistory();
        setToast("支付成功，完整报告已解锁。");
        render();
        return;
      }
      if (payload.order?.status === "failed") {
        setToast("支付未完成，请重新发起支付。");
        render();
        return;
      }
    } catch (error) {
      if (index > 2) setToast(error.message || "支付状态查询失败");
    }
  }
  setToast("还没有收到支付成功通知，稍后可在历史记录中查看。");
}

async function deleteReport(id) {
  if (!window.confirm("确定删除这份报告和关联资料吗？")) return;
  try {
    setBusy(true, "删除报告和关联资料...");
    await apiRequest(`/v1/reports/${id}`, { method: "DELETE" });
    state.history = state.history.filter((report) => report.id !== id);
    if (state.report?.id === id) {
      state.report = null;
      state.unlocked = false;
    }
    setToast("已删除历史记录和关联资料。");
  } catch (error) {
    setToast(error.message || "删除失败");
  } finally {
    setBusy(false);
  }
}

async function loadReport(id) {
  try {
    setBusy(true, "加载报告...");
    const payload = await apiRequest(`/v1/reports/${id}`);
    state.report = payload.report;
    state.unlocked = Boolean(payload.report.unlocked);
    state.activeView = "report";
  } catch (error) {
    setToast(error.message || "报告加载失败");
  } finally {
    setBusy(false);
  }
}

async function resumePaymentReturn() {
  const params = new URLSearchParams(window.location.search);
  const reportId = params.get("reportId");
  const orderId = params.get("out_trade_no");
  if (reportId) {
    await loadReport(reportId);
  }
  if (orderId) {
    state.pendingOrder = { id: orderId };
    setToast("已从支付宝返回，正在确认支付结果。");
    pollOrder(orderId, 15);
  }
  if (reportId || orderId) {
    window.history.replaceState({}, "", window.location.pathname);
  }
}

function validateAuditForm() {
  const errors = {};
  const area = Number(state.form.area);
  const budget = Number(state.form.budget);
  if (!state.form.city.trim()) errors.city = "请输入城市";
  if (!Number.isFinite(area) || area <= 0) errors.area = "面积需大于 0";
  if (!Number.isFinite(budget) || budget <= 0) errors.budget = "报价需大于 0";
  if (!state.form.ocrText.trim() && !state.files.length) errors.ocrText = "请上传文件或粘贴报价合同内容";
  return errors;
}

function money(value) {
  const num = Number(value || 0);
  return num.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function detectClientType() {
  const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  return isMobile ? "mobile" : "web";
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function servicePill() {
  const ok = state.service?.ok;
  const db = state.service?.dbProvider || "unknown";
  const fileStore = state.service?.fileStorageProvider || "unknown";
  const ai = state.service?.aiProvider || "unknown";
  return `
    <div class="service-pill ${ok ? "online" : "offline"}" aria-label="服务状态">
      <span></span>
      <strong>${ok ? "审查服务在线" : "服务连接中"}</strong>
      <small>${escapeHtml(ai)} / ${escapeHtml(db)} / ${escapeHtml(fileStore)}</small>
    </div>
  `;
}

function riskStats(report) {
  const risks = report?.risks || [];
  return ["高", "中", "低"].map((level) => ({
    level,
    count: risks.filter((risk) => risk.level === level).length
  }));
}

function riskClass(level) {
  if (level === "高") return "danger";
  if (level === "中") return "warning";
  return "calm";
}

function icon(name) {
  return `<i data-lucide="${name}" aria-hidden="true"></i>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    setToast("已复制到剪贴板。");
  } catch {
    setToast("复制失败，请手动选择文本复制。");
  }
}

function downloadReport() {
  if (!state.report) return;
  const report = state.report;
  const risks = report.risks || [];
  const text = [
    `避坑宝审核报告：${report.title}`,
    `生成时间：${report.createdAt}`,
    `总体结论：${report.conclusion}`,
    `风险评分：${report.score}/100`,
    `AI 状态：${report.aiStatus || "unknown"}`,
    "",
    "风险项目：",
    ...risks.map((risk) => `【${risk.level}】${risk.title}\n原因：${risk.reason}\n建议追问：${risk.ask}`),
    "",
    "家人版总结：",
    report.familySummary,
    "",
    "免责声明：",
    report.disclaimer
  ].join("\n\n");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${report.title}.txt`;
  link.click();
  URL.revokeObjectURL(url);
}

function handleFileChange(event) {
  state.files = Array.from(event.target.files || []);
  render();
}

function updateForm(key, value) {
  state.form[key] = value;
  if (state.errors[key]) delete state.errors[key];
}

function renderShell() {
  return `
    <header class="topbar">
      <div class="brand" aria-label="避坑宝">
        <span class="brand-mark">${icon("shield-check")}</span>
        <span>
          <strong>避坑宝</strong>
          <small>大额消费付款前审查</small>
        </span>
      </div>
      <nav class="nav" aria-label="主要导航">
        ${navButton("audit", "上传审核", "upload-cloud")}
        ${navButton("report", "风险报告", "file-search")}
        ${navButton("history", "历史记录", "clock")}
      </nav>
    </header>
    <main id="main" class="app-shell">
      ${renderCurrentView()}
    </main>
    ${state.isBusy ? renderBusyLayer() : ""}
    ${state.toast ? `<div class="toast" role="status">${escapeHtml(state.toast)}</div>` : ""}
  `;
}

function renderBusyLayer() {
  return `
    <div class="busy-layer" role="status" aria-live="polite">
      <div>
        <div class="review-beacon">${icon("scan-search")}</div>
        <strong>${escapeHtml(state.busyLabel || "处理中...")}</strong>
        <span>正在校验资料、生成风险摘要和追问清单</span>
        <div class="busy-checks" aria-hidden="true">
          <i></i><i></i><i></i>
        </div>
      </div>
    </div>
  `;
}

function navButton(view, label, iconName) {
  const active = state.activeView === view ? "active" : "";
  return `<button class="nav-button ${active}" type="button" data-view="${view}" aria-current="${active ? "page" : "false"}">${icon(iconName)}<span>${label}</span></button>`;
}

function renderCurrentView() {
  if (state.activeView === "history") return renderHistory();
  if (state.activeView === "report") return renderReport();
  return renderAudit();
}

function renderAudit() {
  const aiLabel = state.service?.aiProvider ? `AI：${state.service.aiProvider}` : "API 待连接";
  return `
    <section class="workspace">
      <div class="audit-panel">
        <div class="hero-panel" aria-label="付款前审查工作台">
          <div class="hero-copy">
            <span class="eyebrow">装修报价 / 合同审核</span>
            <h1>付款前，把装修疑点查清楚</h1>
            <p>上传报价、合同或聊天承诺，拆出异常报价、模糊条款和可追问话术。</p>
            <div class="hero-actions">
              <button class="primary-button" type="button" data-action="focus-upload">${icon("upload-cloud")}开始审查</button>
              <button class="ghost-button" type="button" data-action="sample">${icon("wand-sparkles")}看高风险样例</button>
            </div>
          </div>
          <div class="review-desk" aria-label="审核台摘要">
            <div class="desk-header">
              <span>付款前审查单</span>
              <strong>待确认 12 项</strong>
            </div>
            <div class="desk-score">
              <strong>59</strong>
              <span>风险评分</span>
            </div>
            <div class="desk-lines">
              <span><i></i>付款节点偏前</span>
              <span><i></i>主材标准不清</span>
              <span><i></i>水电增项入口</span>
            </div>
            <div class="desk-matrix" aria-label="风险维度">
              <div class="matrix-row"><span>报价</span><i style="--fill:78%"></i><strong>78</strong></div>
              <div class="matrix-row"><span>合同</span><i style="--fill:64%"></i><strong>64</strong></div>
              <div class="matrix-row"><span>增项</span><i style="--fill:86%"></i><strong>86</strong></div>
              <div class="matrix-row"><span>证据</span><i style="--fill:48%"></i><strong>48</strong></div>
            </div>
            <small>免费预览先给 3 条明显风险，完整报告解锁全部细项。</small>
          </div>
          <div class="hero-insights" aria-label="审核能力摘要">
            ${insightCard("生成预览", "约 1 分钟", "视文件大小和 AI 响应而定", "timer")}
            ${insightCard("免费可看", "3 条", "先判断报告是否值得解锁", "badge-check")}
            ${insightCard("闭环动作", "追问清单", "把风险转成可执行问题", "route")}
          </div>
        </div>

        <div class="upload-card">
          <label class="dropzone" for="fileInput">
            ${icon("upload-cloud")}
            <strong>把资料放到审查台</strong>
            <span>支持报价单照片、合同截图、PDF、户型图、商家聊天记录</span>
            <input id="fileInput" type="file" multiple accept="image/*,.pdf,.txt" />
          </label>
          <div class="file-list" aria-live="polite">
            ${
              state.files.length
                ? state.files.map((file) => `<span>${icon("paperclip")}<strong>${escapeHtml(file.name)}</strong><small>${formatBytes(file.size)}</small></span>`).join("")
                : `<span>${icon("info")}可先用下方示例文本体验审核流程</span>`
            }
          </div>
        </div>

        <form class="audit-form" id="auditForm">
          <div class="form-grid">
            ${fieldSelect("docType", "资料类型", ["报价单", "合同", "户型图", "聊天记录"])}
            ${fieldInput("city", "所在城市", "上海")}
            ${fieldInput("area", "房屋面积 m²", "89", "number")}
            ${fieldSelect("homeType", "装修类型", ["二手房翻新", "新房装修", "局部改造", "出租房装修"])}
            ${fieldSelect("stage", "装修阶段", ["已拿到报价，准备付款", "正在比价", "准备签合同", "施工前确认", "出现争议"])}
            ${fieldInput("budget", "报价总额 元", "128000", "number")}
          </div>
          ${fieldInput("vendor", "商家名称或备注", "某装修公司")}
          <label class="field ${state.errors.ocrText ? "field-error" : ""}">
            <span>OCR 识别文本 / 报价合同内容</span>
            <textarea name="ocrText" rows="8">${escapeHtml(state.form.ocrText)}</textarea>
            <small>${escapeHtml(state.errors.ocrText || "上传文件会自动识别；也可以先粘贴报价或合同内容体验审核。")}</small>
          </label>
          <div class="form-actions">
            <button class="primary-button" type="submit" ${state.isBusy ? "disabled" : ""}>${icon("scan-search")}${state.isBusy ? "处理中..." : "生成免费预览"}</button>
            <button class="ghost-button" type="button" data-action="sample" ${state.isBusy ? "disabled" : ""}>${icon("wand-sparkles")}填入高风险样例</button>
          </div>
        </form>
      </div>
      <aside class="side-panel" aria-label="产品验证指标">
        ${servicePill()}
        <div class="process-panel">
          <h2>审查路径</h2>
          <div class="step-list">
            ${REVIEW_STEPS.map(([title, detail], index) => `<div class="step-item"><span>${index + 1}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div>`).join("")}
          </div>
        </div>
        <div class="metric-board">
          <h2>上线状态</h2>
          ${metric(state.service?.ok ? "后端可用" : "后端异常", state.service?.ok ? "在线" : "离线", aiLabel)}
          ${metric("数据库", state.service?.dbProvider || "检测中", "报告、订单、历史持久化")}
          ${metric("对象存储", state.service?.fileStorageProvider || "检测中", "原始文件不依赖临时目录")}
        </div>
        <div class="principles">
          <h2>信任边界</h2>
          <ul>
            <li>不推荐装修公司，不接广告。</li>
            <li>不输出法律结论，只做消费风险提示。</li>
            <li>资料支持删除，敏感信息不写入前端代码。</li>
            <li>先做装修，不扩展全品类。</li>
          </ul>
        </div>
      </aside>
    </section>
  `;
}

function insightCard(label, value, detail, iconName) {
  return `<div class="insight-card">${icon(iconName)}<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function fieldInput(name, label, placeholder, type = "text") {
  return `
    <label class="field ${state.errors[name] ? "field-error" : ""}">
      <span>${label}</span>
      <input name="${name}" type="${type}" value="${escapeHtml(state.form[name])}" placeholder="${escapeHtml(placeholder)}" />
      ${state.errors[name] ? `<small>${escapeHtml(state.errors[name])}</small>` : ""}
    </label>
  `;
}

function fieldSelect(name, label, options) {
  return `
    <label class="field">
      <span>${label}</span>
      <select name="${name}">
        ${options.map((option) => `<option value="${escapeHtml(option)}" ${state.form[name] === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
      </select>
    </label>
  `;
}

function metric(label, value, detail) {
  return `<div class="metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span><small>${escapeHtml(detail)}</small></div>`;
}

function renderReport() {
  if (!state.report) {
    return `
      <section class="empty-state">
        ${icon("file-search")}
        <h1>还没有审核报告</h1>
        <p>先上传报价单、合同或聊天截图，系统会生成免费预览和完整报告。</p>
        <button class="primary-button" type="button" data-view="audit">${icon("upload-cloud")}去上传</button>
      </section>
    `;
  }
  const report = state.report;
  const visibleRisks = report.risks || [];
  const stats = riskStats(report);
  return `
    <section class="report-layout">
      <div class="report-main">
        <div class="report-header">
          <div>
            <span class="eyebrow">${escapeHtml(report.docType)}审核报告 · ${escapeHtml(report.aiStatus || "ai_unknown")}</span>
            <h1>${escapeHtml(report.title)}</h1>
            <p>${escapeHtml(report.fileSummary)}</p>
          </div>
          <div class="score-dial" aria-label="风险评分 ${report.score} 分">
            <strong>${escapeHtml(report.score)}</strong>
            <span>风险评分</span>
          </div>
        </div>

        <div class="risk-radar" aria-label="风险分布">
          ${stats.map((item) => {
            const width = Math.min(100, Math.max(12, item.count * 22));
            return `<div class="radar-item ${riskClass(item.level)}"><span>${escapeHtml(item.level)}风险</span><strong>${item.count}</strong><i style="--w:${width}%"></i></div>`;
          }).join("")}
        </div>

        <div class="summary-strip">
          ${summaryItem("总体结论", report.conclusion, "shield-alert")}
          ${summaryItem("报价总额", `${money(report.total)} 元`, "receipt")}
          ${summaryItem("单平价格", `${money(report.unitPrice)} 元/m²`, "ruler")}
          ${summaryItem("审核时间", report.createdAt, "calendar-clock")}
        </div>

        <section class="report-section">
          <div class="section-title">
            <h2>风险明细</h2>
            <span>${state.unlocked ? "完整报告" : "免费预览 3 条"}</span>
          </div>
          <div class="risk-list">
            ${visibleRisks.map(renderRisk).join("")}
          </div>
          ${!state.unlocked ? renderPaywall(report) : ""}
        </section>

        ${
          state.unlocked
            ? `
            <section class="report-section">
              <div class="section-title"><h2>报价概览</h2><span>${escapeHtml(report.vendor)}</span></div>
              <div class="item-grid">
                ${(report.items || []).map((item) => `<article class="item-card"><strong>${escapeHtml(item.name)}</strong><span>${money(item.estimated)} 元</span><small>参考范围：${escapeHtml(item.range)}</small><p>${escapeHtml(item.note)}</p></article>`).join("")}
              </div>
            </section>
            <section class="report-section two-column">
              <div>
                <div class="section-title"><h2>需要追问商家</h2></div>
                <ol class="clean-list">${(report.questions || []).map((question) => `<li>${escapeHtml(question)}</li>`).join("")}</ol>
              </div>
              <div>
                <div class="section-title"><h2>下一步建议</h2></div>
                <ol class="clean-list">${(report.nextSteps || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
              </div>
            </section>
            <section class="report-section">
              <div class="section-title"><h2>可复制沟通话术</h2><button class="icon-button" type="button" data-copy="scripts" aria-label="复制沟通话术" title="复制沟通话术">${icon("copy")}</button></div>
              <div class="script-box">${(report.scripts || []).map((script) => `<p>${escapeHtml(script)}</p>`).join("")}</div>
            </section>
            <section class="report-section">
              <div class="section-title"><h2>家人版总结</h2><button class="icon-button" type="button" data-copy="family" aria-label="复制家人版总结" title="复制家人版总结">${icon("copy")}</button></div>
              <p class="family-summary">${escapeHtml(report.familySummary)}</p>
              <p class="disclaimer">${escapeHtml(report.disclaimer)}</p>
            </section>
          `
            : ""
        }
      </div>
      <aside class="report-actions">
        <div class="action-note">
          <strong>本次报告</strong>
          <span>${state.unlocked ? "完整报告已解锁" : "当前为免费预览"}</span>
        </div>
        <button class="primary-button" type="button" data-action="download" ${state.unlocked ? "" : "disabled"}>${icon("download")}下载报告</button>
        <button class="ghost-button" type="button" data-view="audit">${icon("plus")}再审一份</button>
        <button class="ghost-button" type="button" data-view="history">${icon("clock")}查看历史</button>
        <div class="upsell">
          <strong>后续服务入口</strong>
          <span>合同复查 199 元</span>
          <span>人工专家复核 499 元起</span>
          <span>施工节点检查包</span>
        </div>
      </aside>
    </section>
  `;
}

function summaryItem(label, value, iconName) {
  return `<div class="summary-item">${icon(iconName)}<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`;
}

function renderRisk(risk) {
  return `
    <article class="risk-card ${riskClass(risk.level)}">
      <div class="risk-top">
        <span>${escapeHtml(risk.level)}风险</span>
        <small>${escapeHtml(risk.category)}</small>
      </div>
      <h3>${escapeHtml(risk.title)}</h3>
      <p>${escapeHtml(risk.reason)}</p>
      <div class="ask-box"><strong>建议追问</strong><span>${escapeHtml(risk.ask)}</span></div>
    </article>
  `;
}

function renderPaywall(report) {
  const provider = state.service?.paymentProvider || "mock";
  const unlockLabel = paymentUnlockLabel(provider);
  const paymentNote = paymentHint(provider, report.id);
  return `
    <div class="paywall">
      <div>
        <h2>解锁完整报告</h2>
        <p>查看全部风险、报价概览、追问清单、砍价话术和家人版总结。</p>
      </div>
      <div class="price-options" role="radiogroup" aria-label="报告价格">
        ${PRICE_OPTIONS.map((price) => `<button class="price-chip ${state.selectedPrice === price ? "selected" : ""}" type="button" data-price="${price}" aria-pressed="${state.selectedPrice === price}">${price} 元</button>`).join("")}
      </div>
      <button class="primary-button" type="button" data-action="unlock" ${state.isBusy ? "disabled" : ""}>${icon("wallet")}${state.isBusy ? "处理中..." : unlockLabel}</button>
      <small>${escapeHtml(paymentNote)}</small>
      ${state.pendingOrder?.paymentUrl ? `<a class="payment-link" href="${escapeHtml(state.pendingOrder.paymentUrl)}" target="_blank" rel="noreferrer">重新打开支付宝收银台</a>` : ""}
    </div>
  `;
}

function paymentUnlockLabel(provider) {
  if (provider === "alipay") return "支付宝付款并解锁";
  if (provider === "wechat") return "创建微信支付订单";
  return "模拟支付并解锁";
}

function paymentHint(provider, reportId) {
  if (provider === "alipay") return `支付宝付款成功后自动解锁。报告 ID：${reportId}`;
  if (provider === "wechat") return `将在微信小程序内完成支付确认。报告 ID：${reportId}`;
  return `当前为验证环境，不会发起真实扣款。报告 ID：${reportId}`;
}

function renderHistory() {
  const reports = state.history;
  return `
    <section class="history-layout">
      <div class="section-heading">
        <span class="section-kicker">服务端历史记录</span>
        <h1>已审核资料</h1>
        <p>历史记录来自后端 API，可查看、删除并同步到当前登录用户。</p>
      </div>
      ${
        reports.length
          ? `<div class="history-list">${reports.map(renderHistoryItem).join("")}</div>`
          : `<div class="empty-state compact">${icon("clock")}<h2>暂无历史记录</h2><p>生成报告后会自动出现在这里。</p></div>`
      }
    </section>
  `;
}

function renderHistoryItem(report) {
  return `
    <article class="history-item">
      <div>
        <span class="status-chip">${report.unlocked ? "已解锁" : "免费预览"}</span>
        <h2>${escapeHtml(report.title)}</h2>
        <p>${escapeHtml(report.createdAt)} / ${escapeHtml(report.conclusion)} / ${(report.risks || []).length} 条预览风险</p>
      </div>
      <div class="history-actions">
        <button class="ghost-button" type="button" data-load="${escapeHtml(report.id)}">${icon("file-search")}查看</button>
        <button class="icon-button danger-icon" type="button" data-delete="${escapeHtml(report.id)}" aria-label="删除历史记录" title="删除历史记录">${icon("trash-2")}</button>
      </div>
    </article>
  `;
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.activeView = button.dataset.view;
      if (state.activeView === "history") await loadHistory();
      render();
    });
  });

  const fileInput = document.querySelector("#fileInput");
  if (fileInput) fileInput.addEventListener("change", handleFileChange);

  const form = document.querySelector("#auditForm");
  if (form) {
    form.addEventListener("input", (event) => {
      const target = event.target;
      if (target.name) updateForm(target.name, target.value);
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await generateReport();
    });
  }

  document.querySelectorAll("[data-action='sample']").forEach((button) => {
    button.addEventListener("click", () => {
      state.form = {
        docType: "合同",
        city: "杭州",
        area: "112",
        homeType: "新房装修",
        stage: "准备签合同",
        budget: "186000",
        vendor: "星禾装饰",
        ocrText: SAMPLE_TEXT
      };
      state.errors = {};
      render();
      setToast("已填入高风险样例。");
    });
  });

  document.querySelector("[data-action='focus-upload']")?.addEventListener("click", () => {
    document.querySelector("#fileInput")?.focus();
    document.querySelector(".upload-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  document.querySelectorAll("[data-price]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedPrice = Number(button.dataset.price);
      render();
    });
  });

  document.querySelector("[data-action='unlock']")?.addEventListener("click", unlockReport);
  document.querySelector("[data-action='download']")?.addEventListener("click", downloadReport);
  document.querySelector("[data-copy='scripts']")?.addEventListener("click", () => copyText((state.report.scripts || []).join("\n\n")));
  document.querySelector("[data-copy='family']")?.addEventListener("click", () => copyText(state.report.familySummary || ""));

  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", () => deleteReport(button.dataset.delete));
  });
  document.querySelectorAll("[data-load]").forEach((button) => {
    button.addEventListener("click", () => loadReport(button.dataset.load));
  });
}

function hydrateMotion() {
  const targets = document.querySelectorAll(
    ".hero-panel, .upload-card, .audit-form, .side-panel > *, .report-header, .risk-radar, .summary-strip, .report-section, .report-actions, .history-list"
  );
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (hydrateMotion.observer) hydrateMotion.observer.disconnect();
  targets.forEach((element, index) => {
    element.classList.add("reveal-ready");
    element.style.setProperty("--reveal-delay", `${Math.min(index * 45, 280)}ms`);
  });
  if (reduceMotion || !("IntersectionObserver" in window)) {
    targets.forEach((element) => element.classList.add("is-visible"));
    return;
  }
  hydrateMotion.observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        hydrateMotion.observer.unobserve(entry.target);
      });
    },
    { threshold: 0.14 }
  );
  targets.forEach((element) => hydrateMotion.observer.observe(element));
}

function render() {
  document.querySelector("#app").innerHTML = renderShell();
  bindEvents();
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 2 } });
  hydrateMotion();
}

async function init() {
  render();
  await loadServiceStatus();
  await loadHistory();
  await resumePaymentReturn();
  render();
}

init();
