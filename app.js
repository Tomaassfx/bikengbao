const isLocalStaticPreview =
  ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname) && window.location.port === "4173";
const API_BASE_URL = window.BIKENGBAO_API_BASE_URL || (isLocalStaticPreview ? "http://127.0.0.1:8787" : window.location.origin);

const state = {
  activeView: "audit",
  files: [],
  uploadedFileIds: [],
  report: null,
  history: [],
  unlocked: false,
  selectedPrice: 59,
  isBusy: false,
  toast: "",
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

function setBusy(isBusy) {
  state.isBusy = isBusy;
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
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    ...(options.headers || {})
  };
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || `请求失败：${response.status}`);
  }
  return payload;
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
  try {
    setBusy(true);
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
  try {
    setBusy(true);
    await ensureAuth();
    const orderPayload = await apiRequest("/v1/orders", {
      method: "POST",
      body: JSON.stringify({ reportId: state.report.id, amount: state.selectedPrice })
    });
    const paidPayload = await apiRequest(`/v1/orders/${orderPayload.order.id}/mock-pay`, {
      method: "POST",
      body: JSON.stringify({})
    });
    state.report = paidPayload.report;
    state.unlocked = Boolean(paidPayload.report.unlocked);
    await loadHistory();
    setToast(`已模拟支付 ${state.selectedPrice} 元，完整报告已解锁。`);
  } catch (error) {
    setToast(error.message || "解锁失败");
  } finally {
    setBusy(false);
  }
}

async function deleteReport(id) {
  try {
    setBusy(true);
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
    setBusy(true);
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

function money(value) {
  const num = Number(value || 0);
  return num.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
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
}

function renderShell() {
  return `
    <header class="topbar">
      <div class="brand" aria-label="避坑宝">
        <span class="brand-mark">${icon("shield-check")}</span>
        <span>
          <strong>避坑宝</strong>
          <small>花钱前审一审</small>
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
    ${state.toast ? `<div class="toast" role="status">${escapeHtml(state.toast)}</div>` : ""}
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
        <div class="section-heading">
          <span class="eyebrow">装修报价 / 合同审核</span>
          <h1>上传报价单，先查清楚再付款</h1>
          <p>第一版聚焦装修消费：识别报价虚高、漏项、增项、付款节点和合同模糊条款。</p>
        </div>

        <div class="upload-card">
          <label class="dropzone" for="fileInput">
            ${icon("upload-cloud")}
            <strong>上传图片、PDF 或聊天截图</strong>
            <span>支持报价单照片、合同截图、户型图、商家聊天记录</span>
            <input id="fileInput" type="file" multiple accept="image/*,.pdf,.txt" />
          </label>
          <div class="file-list" aria-live="polite">
            ${
              state.files.length
                ? state.files.map((file) => `<span>${icon("paperclip")}${escapeHtml(file.name)}</span>`).join("")
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
          <label class="field">
            <span>OCR 识别文本 / 报价合同内容</span>
            <textarea name="ocrText" rows="8">${escapeHtml(state.form.ocrText)}</textarea>
            <small>当前线上 API 已接真实报告生成接口；OCR 暂为占位，用户粘贴内容会参与审核。</small>
          </label>
          <div class="form-actions">
            <button class="primary-button" type="submit" ${state.isBusy ? "disabled" : ""}>${icon("scan-search")}${state.isBusy ? "处理中..." : "生成免费预览"}</button>
            <button class="ghost-button" type="button" data-action="sample" ${state.isBusy ? "disabled" : ""}>${icon("wand-sparkles")}填入高风险样例</button>
          </div>
        </form>
      </div>
      <aside class="side-panel" aria-label="产品验证指标">
        <div class="metric-board">
          <h2>服务状态</h2>
          ${metric(state.service?.ok ? "后端可用" : "后端异常", state.service?.ok ? "在线" : "离线", aiLabel)}
          ${metric("当前闭环", "API 驱动", "报告、订单、历史均来自服务端")}
          ${metric("支付模式", "Mock", "V1 验证不真实扣款")}
        </div>
        <div class="principles">
          <h2>第一版边界</h2>
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

function fieldInput(name, label, placeholder, type = "text") {
  return `
    <label class="field">
      <span>${label}</span>
      <input name="${name}" type="${type}" value="${escapeHtml(state.form[name])}" placeholder="${escapeHtml(placeholder)}" />
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
  return `
    <div class="paywall">
      <div>
        <h2>解锁完整报告</h2>
        <p>查看全部风险、报价概览、追问清单、砍价话术和家人版总结。</p>
      </div>
      <div class="price-options" role="radiogroup" aria-label="报告价格">
        ${[29, 59, 99].map((price) => `<button class="price-chip ${state.selectedPrice === price ? "selected" : ""}" type="button" data-price="${price}" aria-pressed="${state.selectedPrice === price}">${price} 元</button>`).join("")}
      </div>
      <button class="primary-button" type="button" data-action="unlock" ${state.isBusy ? "disabled" : ""}>${icon("wallet")}${state.isBusy ? "处理中..." : "模拟支付并解锁"}</button>
      <small>当前为验证原型，不会发起真实扣款。报告 ID：${escapeHtml(report.id)}</small>
    </div>
  `;
}

function renderHistory() {
  const reports = state.history;
  return `
    <section class="history-layout">
      <div class="section-heading">
        <span class="eyebrow">服务端历史记录</span>
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
        <span class="eyebrow">${report.unlocked ? "已解锁" : "免费预览"}</span>
        <h2>${escapeHtml(report.title)}</h2>
        <p>${escapeHtml(report.createdAt)} · ${escapeHtml(report.conclusion)} · ${(report.risks || []).length} 条预览风险</p>
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

  document.querySelector("[data-action='sample']")?.addEventListener("click", () => {
    state.form = {
      docType: "合同",
      city: "杭州",
      area: "112",
      homeType: "新房装修",
      stage: "准备签合同",
      budget: "186000",
      vendor: "星禾装饰",
      ocrText:
        "合同约定签约付 70%，水电按实际发生结算，主材升级另计，材料以现场为准。拆除、垃圾清运、成品保护、管理费另计。延期赔付双方协商，防水闭水验收标准未列明。"
    };
    render();
    setToast("已填入高风险样例。");
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

function render() {
  document.querySelector("#app").innerHTML = renderShell();
  bindEvents();
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 2 } });
}

async function init() {
  render();
  await loadServiceStatus();
  await loadHistory();
  render();
}

init();
