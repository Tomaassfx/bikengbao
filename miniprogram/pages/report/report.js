const api = require("../../utils/api");
const { money, riskClass } = require("../../utils/format");

Page({
  data: {
    reportId: "",
    report: null,
    visibleRisks: [],
    unlocked: false,
    selectedPrice: 59,
    paying: false
  },

  onLoad(options) {
    this.setData({ reportId: options.id || "" });
    if (options.id) this.loadReport(options.id);
  },

  async loadReport(id) {
    try {
      const result = await api.request({ url: `/v1/reports/${id}` });
      this.applyReport(result.report);
    } catch (error) {
      wx.showToast({ title: error.message || "报告加载失败", icon: "none" });
    }
  },

  applyReport(report) {
    const formatted = this.formatReport(report);
    const unlocked = Boolean(report.unlocked);
    this.setData({
      report: formatted,
      unlocked,
      visibleRisks: unlocked ? formatted.risks : formatted.risks.slice(0, 3)
    });
  },

  formatReport(report) {
    return {
      ...report,
      totalText: `${money(report.total)} 元`,
      unitPriceText: `${money(report.unitPrice)} 元/m²`,
      risks: report.risks.map((risk) => ({
        ...risk,
        className: riskClass(risk.level)
      })),
      items: report.items.map((item) => ({
        ...item,
        estimatedText: `${money(item.estimated)} 元`
      }))
    };
  },

  selectPrice(event) {
    this.setData({ selectedPrice: Number(event.currentTarget.dataset.price) });
  },

  async createOrder() {
    if (this.data.paying) return;
    this.setData({ paying: true });
    try {
      const order = await api.request({
        url: "/v1/orders",
        method: "POST",
        data: {
          reportId: this.data.reportId,
          amount: this.data.selectedPrice
        }
      });

      if (order.payment.mode === "mock") {
        await api.request({
          url: `/v1/orders/${order.order.id}/mock-pay`,
          method: "POST"
        });
      } else {
        await this.requestPayment(order.payment.params);
      }

      const refreshed = await api.request({ url: `/v1/reports/${this.data.reportId}` });
      this.applyReport(refreshed.report);
      wx.showToast({ title: "已解锁完整报告", icon: "success" });
    } catch (error) {
      wx.showToast({ title: error.message || "支付失败", icon: "none" });
    } finally {
      this.setData({ paying: false });
    }
  },

  requestPayment(params) {
    return new Promise((resolve, reject) => {
      wx.requestPayment({
        ...params,
        success: resolve,
        fail: reject
      });
    });
  },

  copyText(event) {
    const kind = event.currentTarget.dataset.kind;
    const report = this.data.report;
    const text = kind === "family" ? report.familySummary : report.scripts.join("\n\n");
    wx.setClipboardData({ data: text });
  }
});
