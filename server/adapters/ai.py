import json
import urllib.error
import urllib.request
from typing import Dict, List

from ..config import AI_PROVIDER, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def enrich_report(base_report: Dict) -> Dict:
    """AI adapter placeholder.

    The rule engine already creates a usable report. When an AI API key is
    provided, call the selected model here to improve contract explanation,
    negotiation scripts, and family summary while keeping the same response
    schema.
    """
    if AI_PROVIDER == "mock":
        return base_report
    if AI_PROVIDER == "deepseek":
        return enrich_with_deepseek(base_report)
    raise NotImplementedError(f"AI provider {AI_PROVIDER} is not configured yet.")


def enrich_with_deepseek(base_report: Dict) -> Dict:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    prompt = {
        "title": base_report["title"],
        "docType": base_report["docType"],
        "city": base_report["city"],
        "area": base_report["area"],
        "total": base_report["total"],
        "unitPrice": base_report["unitPrice"],
        "vendor": base_report["vendor"],
        "stage": base_report["stage"],
        "conclusion": base_report["conclusion"],
        "risks": base_report["risks"],
        "items": base_report["items"],
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是中国装修消费风险审核助手。只做消费决策辅助，不输出法律结论、工程鉴定、"
                    "价格鉴定或监理意见。基于给定规则报告，优化用户可执行内容。必须返回 JSON，"
                    "字段为 familySummary, questions, scripts, nextSteps。每个数组字段 4-6 条，"
                    "语言要具体、克制、可直接发给装修公司。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False),
            },
        ],
    }
    request = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8")
            completion = json.loads(raw)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek API error: {error.code} {detail[:200]}") from error

    content = completion["choices"][0]["message"]["content"]
    enhanced = json.loads(content)
    report = dict(base_report)
    if isinstance(enhanced.get("familySummary"), str):
        report["familySummary"] = enhanced["familySummary"]
    for key in ["questions", "scripts", "nextSteps"]:
        if isinstance(enhanced.get(key), list) and enhanced[key]:
            report[key] = [str(item) for item in enhanced[key]][:6]
    return report


def build_family_summary(doc_type: str, conclusion: str, risks: List[Dict]) -> str:
    top_categories = "、".join([risk["category"] for risk in risks[:3]])
    return (
        f"这份{doc_type}总体判断为“{conclusion}”。主要风险集中在{top_categories}。"
        "建议先补齐报价明细、材料型号、付款节点和延期/质保条款，再决定是否付款。"
    )
