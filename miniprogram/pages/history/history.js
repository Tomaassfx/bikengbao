const api = require("../../utils/api");

Page({
  data: {
    loading: false,
    reports: []
  },

  onShow() {
    this.loadReports();
  },

  async loadReports() {
    this.setData({ loading: true });
    try {
      const result = await api.request({ url: "/v1/reports" });
      this.setData({
        reports: result.reports.map((report) => ({
          ...report,
          riskCount: report.risks ? report.risks.length : report.riskCount
        }))
      });
    } catch (error) {
      wx.showToast({ title: error.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  openReport(event) {
    const id = event.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/report/report?id=${id}` });
  },

  deleteReport(event) {
    const id = event.currentTarget.dataset.id;
    wx.showModal({
      title: "删除资料",
      content: "删除后将移除报告和关联上传文件，无法恢复。",
      confirmText: "删除",
      confirmColor: "#c75146",
      success: async (result) => {
        if (!result.confirm) return;
        try {
          await api.request({ url: `/v1/reports/${id}`, method: "DELETE" });
          wx.showToast({ title: "已删除", icon: "success" });
          this.loadReports();
        } catch (error) {
          wx.showToast({ title: error.message || "删除失败", icon: "none" });
        }
      }
    });
  }
});
