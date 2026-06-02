function money(value) {
  const number = Number(value || 0);
  return number.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
}

function riskClass(level) {
  if (level === "高") return "danger";
  if (level === "中") return "warning";
  return "calm";
}

module.exports = {
  money,
  riskClass
};
