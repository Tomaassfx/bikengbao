import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ..config import OCR_PROVIDER, TENCENT_OCR_ACTION, TENCENT_OCR_REGION, TENCENT_SECRET_ID, TENCENT_SECRET_KEY


def extract_text(file_record: Dict[str, Any]) -> str:
    if OCR_PROVIDER == "mock":
        filename = file_record.get("filename", "上传文件")
        doc_type = file_record.get("docType", "资料")
        return f"{doc_type} {filename} 已上传，等待真实 OCR 识别。"

    if OCR_PROVIDER == "tencent":
        return extract_text_with_tencent(file_record)

    raise RuntimeError(f"OCR provider {OCR_PROVIDER} is not configured.")


def extract_text_with_tencent(file_record: Dict[str, Any]) -> str:
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("腾讯云 OCR 未配置 TENCENT_SECRET_ID 或 TENCENT_SECRET_KEY")

    payload: Dict[str, Any] = {}
    if file_record.get("blobUrl"):
        payload["ImageUrl"] = file_record["blobUrl"]
    elif file_record.get("path"):
        payload["ImageBase64"] = image_base64(file_record["path"])
    else:
        raise RuntimeError("OCR 未找到可识别的文件地址")

    result = tencent_ocr_request(TENCENT_OCR_ACTION, payload)
    if result.get("Error"):
        raise RuntimeError(result["Error"].get("Message") or "腾讯云 OCR 识别失败")

    lines = []
    for item in result.get("TextDetections", []) or []:
        text = item.get("DetectedText")
        if text:
            lines.append(text)
    return "\n".join(lines).strip() or "OCR 未识别出有效文本"


def image_base64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def tencent_ocr_request(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    service = "ocr"
    host = "ocr.tencentcloudapi.com"
    version = "2018-11-19"
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    canonical_request = "\n".join(
        [
            "POST",
            "/",
            "",
            f"content-type:application/json; charset=utf-8\nhost:{host}\nx-tc-action:{action.lower()}\n",
            "content-type;host;x-tc-action",
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
        ]
    )
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = "\n".join(
        [
            algorithm,
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac_sha256(hmac_sha256(hmac_sha256(("TC3" + TENCENT_SECRET_KEY).encode("utf-8"), date), service), "tc3_request")
    signed = hmac.new(signature, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"{algorithm} Credential={TENCENT_SECRET_ID}/{credential_scope}, "
        "SignedHeaders=content-type;host;x-tc-action, "
        f"Signature={signed}"
    )
    request = Request(
        f"https://{host}",
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Version": version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": TENCENT_OCR_REGION,
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"腾讯云 OCR 请求失败：{exc.code} {detail}") from exc
    return payload.get("Response", payload)


def hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
