const api = require("../../utils/api");
const { money, riskClass } = require("../../utils/format");

Page({
  data: {
    reportId: "",
    report: null,
    visibleRisks: [],
    unlocked: false,
    selectedPrice: 59,
    manualPayment: null,
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
      } else if (order.payment.mode === "manual_qr") {
        const channels = order.payment.channels && order.payment.channels.length
          ? order.payment.channels
          : [{
              id: "alipay",
              label: "支付宝",
              qrImageUrl: order.payment.qrImageUrl,
              accountName: order.payment.accountName,
              accountHint: order.payment.accountHint
            }];
        const selectedChannel = channels.find((channel) => channel.qrImageUrl) || channels[0];
        this.setData({
          manualPayment: {
            orderId: order.order.id,
            amountText: order.payment.amountText,
            qrImageUrl: order.payment.qrImageUrl,
            accountName: order.payment.accountName,
            accountHint: order.payment.accountHint,
            reference: order.payment.reference,
            instructions: order.payment.instructions || [],
            channels,
            selectedChannelId: selectedChannel.id,
            selectedChannel
          }
        });
        wx.showToast({ title: "扫码后等待人工确认", icon: "none" });
        this.waitForUnlock();
        return;
      } else if (order.payment.mode === "wechat") {
        await this.requestPayment(order.payment.params);
        await this.waitForUnlock();
      } else {
        wx.showToast({ title: "当前支付方式请在网页端完成", icon: "none" });
        return;
      }

      const refreshed = await api.request({ url: `/v1/reports/${this.data.reportId}` });
      this.applyReport(refreshed.report);
      wx.showToast({ title: refreshed.report.unlocked ? "已解锁完整报告" : "支付确认中", icon: refreshed.report.unlocked ? "success" : "none" });
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

  async waitForUnlock() {
    for (let index = 0; index < 6; index += 1) {
      const result = await api.request({ url: `/v1/reports/${this.data.reportId}` });
      if (result.report && result.report.unlocked) {
        this.applyReport(result.report);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
  },

  async refreshManualPayment() {
    const orderId = this.data.manualPayment && this.data.manualPayment.orderId;
    if (!orderId) return;
    try {
      const result = await api.request({ url: `/v1/orders/${orderId}` });
      if (result.order && result.order.status === "paid") {
        this.setData({ manualPayment: null });
        this.applyReport(result.report);
        wx.showToast({ title: "已解锁完整报告", icon: "success" });
        return;
      }
      wx.showToast({ title: "还未确认到账", icon: "none" });
    } catch (error) {
      wx.showToast({ title: error.message || "状态查询失败", icon: "none" });
    }
  },

  selectManualChannel(event) {
    const payment = this.data.manualPayment;
    if (!payment) return;
    const selectedChannelId = event.currentTarget.dataset.channel;
    const selectedChannel = payment.channels.find((channel) => channel.id === selectedChannelId);
    if (!selectedChannel) return;
    this.setData({
      manualPayment: {
        ...payment,
        selectedChannelId,
        selectedChannel
      }
    });
  },

  copyManualPayment() {
    const payment = this.data.manualPayment;
    if (!payment) return;
    wx.setClipboardData({
      data: [
        "避坑宝报告解锁付款",
        `付款方式：${payment.selectedChannel.label}`,
        `金额：${payment.amountText} 元`,
        `付款备注码：${payment.reference}`,
        `收款方：${payment.selectedChannel.accountName}`,
        `订单号：${payment.orderId}`
      ].join("\n")
    });
  },

  copyText(event) {
    const kind = event.currentTarget.dataset.kind;
    const report = this.data.report;
    const text = kind === "family" ? report.familySummary : report.scripts.join("\n\n");
    wx.setClipboardData({ data: text });
  }
});
