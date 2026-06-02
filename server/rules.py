import math
import uuid
from typing import Dict, List

from .adapters.ai import build_family_summary, enrich_report
from .storage import now_text


BASELINE = {
    "拆除": {"min": 3500, "max": 9000, "aliases": ["拆除", "拆旧", "铲墙", "垃圾清运"]},
    "水电": {"min": 8000, "max": 18000, "aliases": ["水电", "电路", "水路", "强弱电"]},
    "防水": {"min": 2500, "max": 6500, "aliases": ["防水", "闭水"]},
    "泥瓦": {"min": 12000, "max": 28000, "aliases": ["瓷砖", "铺贴", "泥瓦", "找平"]},
    "木作": {"min": 12000, "max": 45000, "aliases": ["柜", "木作", "全屋定制", "吊顶"]},
    "油漆": {"min": 9000, "max": 22000, "aliases": ["乳胶漆", "墙面", "油漆", "腻子"]},
}

PACKAGE_HINTS = [
    "管理费",
    "设计费",
    "远程费",
    "保护费",
    "成品保护",
    "垃圾清运",
    "搬运费",
    "税费",
    "主材升级",
    "辅材升级",
]

QUESTIONS = [
    "请把所有“按实际发生结算”的项目改成单价、数量、上限金额和验收口径。",
    "请列出主材/辅材的品牌、型号、规格、环保等级和替换规则，并写进合同附件。",
    "请说明哪些项目不包含在当前总价里，后续增加时如何计价、谁确认后生效。",
    "请把延期赔付、质保年限、返修响应时间写成明确条款。",
    "请提供水电、防水、泥瓦、油漆四个节点的验收标准和照片留档要求。",
    "请确认付款节点是否可以改为按验收进度付款，而不是签约即支付大比例款项。",
]

NEXT_STEPS = [
    "先不要支付大额定金或签约款，至少补齐材料清单、报价明细和延期赔付条款。",
    "要求商家把口头承诺写进合同附件，并让对方盖章或通过企业微信确认。",
    "拿同样需求找 2 家商家横向比价，重点比较漏项而不是只比较总价。",
    "保留报价单、聊天记录、付款凭证、施工照片，后续争议时作为证据。",
]

SCRIPTS = [
    "我看了报价单，里面有几项写得比较模糊。麻烦把“按实际结算”“材料以现场为准”的项目补成明确单价、数量和上限金额。",
    "为了避免后续增项，我们希望把不包含的项目一次性列清楚，并写进合同附件。",
    "付款比例我们想按验收节点调整，签约款不超过 30%，水电/泥瓦/竣工验收后再分阶段付款。",
    "延期赔付和质保条款也请写明确，包括延期一天怎么赔、返修多久响应、材料替换如何确认。",
]


def money(value: float) -> str:
    return f"{round(value):,}"


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def risk(level: str, category: str, title: str, reason: str, ask: str) -> Dict:
    return {
        "id": uuid.uuid4().hex,
        "level": level,
        "category": category,
        "title": title,
        "reason": reason,
        "ask": ask,
    }


def infer_items(text: str, total: float, area: float) -> List[Dict]:
    items = []
    area_factor = clamp(area / 90, 0.7, 1.6)
    for name, config in BASELINE.items():
        matched = any(alias in text for alias in config["aliases"])
        implied = matched or (name == "水电" and "实际发生" in text)
        if not implied:
            continue
        base = round((config["min"] + config["max"]) / 2 * area_factor)
        items.append(
            {
                "name": name,
                "estimated": base,
                "range": f"{money(config['min'] * area_factor)}-{money(config['max'] * area_factor)} 元",
                "note": "需要结合品牌、工艺和城市人工成本确认",
            }
        )

    if items:
        return items

    return [
        {
            "name": "基础施工",
            "estimated": round(total * 0.46),
            "range": "需按拆除/水电/泥瓦/油漆拆分",
            "note": "报价项过少，无法判断单项合理性",
        },
        {
            "name": "主材/定制",
            "estimated": round(total * 0.32),
            "range": "需列品牌型号",
            "note": "主材不透明容易产生升级费用",
        },
    ]


def generate_report(user_id: str, form: Dict, files: List[Dict]) -> Dict:
    total = float(form.get("budget") or 0)
    area = float(form.get("area") or 1)
    text = " ".join(
        [
            str(form.get("ocrText", "")),
            str(form.get("docType", "")),
            str(form.get("stage", "")),
            str(form.get("homeType", "")),
            " ".join(file.get("ocrText", "") for file in files),
        ]
    )
    unit_price = round(total / area) if total and area else 0
    risks = build_risks(text, unit_price)
    high_count = len([item for item in risks if item["level"] == "高"])
    middle_count = len([item for item in risks if item["level"] == "中"])
    conclusion = "建议谨慎" if high_count >= 3 else "可继续沟通" if high_count >= 1 or middle_count >= 3 else "风险较低"
    score = math.floor(clamp(92 - high_count * 18 - middle_count * 9, 18, 96))
    title = f"{form.get('city', '未知城市')} {form.get('area', '-')}m² {form.get('homeType', '装修')}审核报告"
    file_summary = "、".join(file.get("filename", "上传文件") for file in files) or "未上传文件，使用粘贴文本生成"

    report = {
        "id": uuid.uuid4().hex,
        "userId": user_id,
        "createdAt": now_text(),
        "createdAtMs": 0,
        "title": title,
        "docType": form.get("docType", "报价单"),
        "city": form.get("city", ""),
        "area": area,
        "total": total,
        "unitPrice": unit_price,
        "vendor": form.get("vendor", "未填写商家"),
        "stage": form.get("stage", ""),
        "conclusion": conclusion,
        "score": score,
        "risks": risks,
        "items": infer_items(text, total, area),
        "fileSummary": file_summary,
        "fileIds": [file["id"] for file in files],
        "familySummary": build_family_summary(form.get("docType", "报价单"), conclusion, risks),
        "questions": QUESTIONS,
        "scripts": SCRIPTS,
        "nextSteps": NEXT_STEPS,
        "disclaimer": "本报告为消费决策辅助，不构成法律意见、工程鉴定、价格鉴定或监理意见。",
        "unlocked": False,
        "deleted": False,
    }
    return enrich_report(report)


def build_risks(text: str, unit_price: int) -> List[Dict]:
    risks = []
    if unit_price > 1600:
        risks.append(
            risk(
                "高",
                "价格异常",
                f"单平约 {money(unit_price)} 元，已经偏向高位",
                "当前总价相对面积偏高，需要确认是否包含主材、定制、家电和管理费，避免低价项与高价项混在一起。",
                "请商家按拆除、水电、泥瓦、木作、油漆、主材、管理费拆分总价，并标注每项数量和单价。",
            )
        )

    if "实际发生" in text or "另计" in text or "增项" in text:
        risks.append(
            risk(
                "高",
                "后期增项",
                "存在“实际发生/另计”表述，后续加价风险较高",
                "这类表述通常意味着当前报价不是封闭价格，施工中可能以现场情况为由继续加收费用。",
                "要求写明计价公式、单价、预估数量、最高上限和需要你书面确认后才可增项。",
            )
        )

    if "以现场为准" in text or "双方协商" in text or "口头" in text:
        risks.append(
            risk(
                "高",
                "合同模糊",
                "合同关键条款模糊，争议时难以举证",
                "“以现场为准”“双方协商”缺少明确标准，后续出现延期、返修、材料替换时会很难追责。",
                "把延期赔付、材料替换、验收标准、返修响应时间写成可执行条款。",
            )
        )

    if "60%" in text or "70%" in text or "签约付" in text:
        risks.append(
            risk(
                "高",
                "付款风险",
                "签约/开工前付款比例偏高",
                "前期付款过高会削弱后续议价和整改能力，施工质量或延期发生时用户处于被动。",
                "建议改为签约款不超过 30%，后续按水电、泥瓦、竣工验收分阶段付款。",
            )
        )

    if "质保" not in text and "保修" not in text:
        risks.append(
            risk(
                "中",
                "售后缺口",
                "未识别到质保/保修条款",
                "水电、防水、墙面开裂、柜体五金等问题常在入住后暴露，缺少质保条款会增加返修难度。",
                "要求分别写明隐蔽工程、防水、表面工程、定制柜体的质保年限和响应时间。",
            )
        )

    if "品牌" not in text and "型号" not in text and "规格" not in text:
        risks.append(
            risk(
                "中",
                "材料不透明",
                "材料品牌/型号/规格不完整",
                "只写材料类别不写品牌型号，容易在施工时替换成低配材料，也不利于验收。",
                "要求主材和辅材清单写明品牌、型号、规格、环保等级、替换规则。",
            )
        )

    missing = [word for word in ["防水", "闭水", "验收", "延期", "违约"] if word not in text]
    if len(missing) >= 3:
        risks.append(
            risk(
                "中",
                "漏项风险",
                "防水/验收/延期等关键节点描述不足",
                "这些项目是装修纠纷高发点，报价或合同没有写清会让后续责任边界不清。",
                f"补充以下条款：{'、'.join(missing)}。",
            )
        )

    repeated = [word for word in PACKAGE_HINTS if word in text]
    if len(repeated) >= 2:
        risks.append(
            risk(
                "中",
                "重复收费",
                "识别到多个附加收费项，需要确认是否重复",
                f"{'、'.join(repeated)} 可能已经包含在管理费或施工费中，建议逐项确认边界。",
                "请商家说明每个附加收费项对应的服务内容、数量和是否已包含在其他项目里。",
            )
        )

    risks.append(
        risk(
            "低",
            "证据留存",
            "建议保留完整沟通和确认记录",
            "装修争议通常依赖报价单、合同附件、聊天记录、付款凭证和现场照片证明。",
            "所有变更、增项、材料替换都通过微信文字或合同附件确认，不只口头沟通。",
        )
    )
    return risks
