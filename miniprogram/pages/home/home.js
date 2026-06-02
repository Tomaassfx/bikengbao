const api = require("../../utils/api");

const docTypes = ["报价单", "合同", "户型图", "聊天记录"];
const homeTypes = ["二手房翻新", "新房装修", "局部改造", "出租房装修"];
const stages = ["已拿到报价，准备付款", "正在比价", "准备签合同", "施工前确认", "出现争议"];

Page({
  data: {
    docTypes,
    homeTypes,
    stages,
    docTypeIndex: 0,
    homeTypeIndex: 0,
    stageIndex: 0,
    files: [],
    submitting: false,
    form: {
      docType: "报价单",
      city: "上海",
      area: "89",
      homeType: "二手房翻新",
      stage: "已拿到报价，准备付款",
      budget: "128000",
      vendor: "某装修公司",
      ocrText: "水电改造按实际发生结算，材料品牌以现场为准。拆除 9000 元，墙面刷新 18000 元，防水 8500 元，瓷砖铺贴 26000 元，橱柜和全屋定制另计。付款节点：签约付 60%，水电验收付 30%，竣工付 10%。延期赔付双方协商。"
    }
  },

  onInput(event) {
    const key = event.currentTarget.dataset.key;
    this.setData({
      [`form.${key}`]: event.detail.value
    });
  },

  onDocTypeChange(event) {
    const index = Number(event.detail.value);
    this.setData({
      docTypeIndex: index,
      "form.docType": docTypes[index]
    });
  },

  onHomeTypeChange(event) {
    const index = Number(event.detail.value);
    this.setData({
      homeTypeIndex: index,
      "form.homeType": homeTypes[index]
    });
  },

  onStageChange(event) {
    const index = Number(event.detail.value);
    this.setData({
      stageIndex: index,
      "form.stage": stages[index]
    });
  },

  chooseFiles() {
    wx.chooseMessageFile({
      count: 6,
      type: "all",
      success: async ({ tempFiles }) => {
        const pendingFiles = tempFiles.map((file) => ({
          id: `${Date.now()}-${file.name}`,
          name: file.name,
          path: file.path,
          statusText: "待上传"
        }));
        this.setData({ files: [...this.data.files, ...pendingFiles] });
        await this.uploadPendingFiles(pendingFiles);
      }
    });
  },

  async uploadPendingFiles(pendingFiles) {
    const uploaded = [...this.data.files];
    for (const file of pendingFiles) {
      const index = uploaded.findIndex((item) => item.id === file.id);
      uploaded[index].statusText = "上传中";
      this.setData({ files: uploaded });
      try {
        const result = await api.uploadFile(file.path, {
          docType: this.data.form.docType,
          filename: file.name
        });
        uploaded[index] = {
          ...uploaded[index],
          fileId: result.file.id,
          statusText: "已上传"
        };
      } catch (error) {
        uploaded[index].statusText = "上传失败";
        wx.showToast({ title: "文件上传失败", icon: "none" });
      }
      this.setData({ files: uploaded });
    }
  },

  fillSample() {
    this.setData({
      docTypeIndex: 1,
      homeTypeIndex: 1,
      stageIndex: 2,
      form: {
        docType: "合同",
        city: "杭州",
        area: "112",
        homeType: "新房装修",
        stage: "准备签合同",
        budget: "186000",
        vendor: "星禾装饰",
        ocrText: "合同约定签约付 70%，水电按实际发生结算，主材升级另计，材料以现场为准。拆除、垃圾清运、成品保护、管理费另计。延期赔付双方协商，防水闭水验收标准未列明。"
      }
    });
  },

  async submitAudit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      const fileIds = this.data.files.filter((file) => file.fileId).map((file) => file.fileId);
      const result = await api.request({
        url: "/v1/audits",
        method: "POST",
        data: {
          ...this.data.form,
          fileIds
        }
      });
      wx.navigateTo({
        url: `/pages/report/report?id=${result.report.id}`
      });
    } catch (error) {
      wx.showToast({ title: error.message || "生成失败", icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  }
});
