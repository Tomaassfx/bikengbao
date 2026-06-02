const { API_BASE_URL } = require("../config/env");

function getToken() {
  return wx.getStorageSync("token") || "";
}

function request({ url, method = "GET", data = {}, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header: {
        "Content-Type": "application/json",
        Authorization: getToken() ? `Bearer ${getToken()}` : "",
        ...header
      },
      success(response) {
        const payload = response.data || {};
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(payload);
          return;
        }
        reject(new Error(payload.message || "请求失败"));
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

function uploadFile(filePath, meta = {}) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${API_BASE_URL}/v1/files`,
      filePath,
      name: "file",
      formData: meta,
      header: {
        Authorization: getToken() ? `Bearer ${getToken()}` : ""
      },
      success(response) {
        try {
          const payload = JSON.parse(response.data || "{}");
          if (response.statusCode >= 200 && response.statusCode < 300) {
            resolve(payload);
            return;
          }
          reject(new Error(payload.message || "上传失败"));
        } catch (error) {
          reject(error);
        }
      },
      fail(error) {
        reject(error);
      }
    });
  });
}

module.exports = {
  request,
  uploadFile
};
