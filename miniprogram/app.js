const { API_BASE_URL } = require("./config/env");
const api = require("./utils/api");

App({
  globalData: {
    apiBaseUrl: API_BASE_URL,
    token: "",
    user: null
  },

  onLaunch() {
    const token = wx.getStorageSync("token");
    const user = wx.getStorageSync("user");
    if (token) this.globalData.token = token;
    if (user) this.globalData.user = user;
    if (!token) this.loginSilently();
  },

  loginSilently() {
    wx.login({
      success: async ({ code }) => {
        try {
          const result = await api.request({
            url: "/v1/auth/wechat",
            method: "POST",
            data: { code }
          });
          this.globalData.token = result.token;
          this.globalData.user = result.user;
          wx.setStorageSync("token", result.token);
          wx.setStorageSync("user", result.user);
        } catch (error) {
          console.warn("login failed", error);
        }
      }
    });
  }
});
