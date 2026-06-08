import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ..config import (
    PAYMENT_PROVIDER,
    WECHAT_APP_ID,
    WECHAT_MCH_ID,
    WECHAT_PAY_API_BASE,
    WECHAT_PAY_API_V3_KEY,
    WECHAT_PAY_NOTIFY_URL,
    WECHAT_PAY_PLATFORM_CERT,
    WECHAT_PAY_PLATFORM_CERT_PATH,
    WECHAT_PAY_PRIVATE_KEY,
    WECHAT_PAY_PRIVATE_KEY_PATH,
    WECHAT_PAY_SERIAL_NO,
)


def create_payment(order: Dict[str, Any]) -> Dict[str, Any]:
    if PAYMENT_PROVIDER == "mock":
        return {
            "mode": "mock",
            "params": {},
            "paymentId": f"mockpay_{uuid.uuid4().hex}",
        }

    if PAYMENT_PROVIDER == "wechat":
        return create_wechat_jsapi_payment(order)

    raise RuntimeError(f"Payment provider {PAYMENT_PROVIDER} is not configured.")


def create_wechat_jsapi_payment(order: Dict[str, Any]) -> Dict[str, Any]:
    assert_wechat_payment_config()
    openid = order.get("openid") or ""
    if not openid:
        raise RuntimeError("微信支付需要真实微信 openid，请先启用 BIKENGBAO_AUTH_PROVIDER=wechat")

    body = {
        "appid": WECHAT_APP_ID,
        "mchid": WECHAT_MCH_ID,
        "description": order.get("description") or "避坑宝装修审核报告",
        "out_trade_no": order["id"],
        "notify_url": WECHAT_PAY_NOTIFY_URL,
        "amount": {"total": int(order["amount"]) * 100, "currency": "CNY"},
        "payer": {"openid": openid},
    }
    payload = wechat_request("POST", "/v3/pay/transactions/jsapi", body)
    prepay_id = payload.get("prepay_id", "")
    if not prepay_id:
        raise RuntimeError("微信支付未返回 prepay_id")

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    package = f"prepay_id={prepay_id}"
    pay_sign = sign_message(f"{WECHAT_APP_ID}\n{timestamp}\n{nonce}\n{package}\n")

    return {
        "mode": "wechat",
        "paymentId": prepay_id,
        "params": {
            "timeStamp": timestamp,
            "nonceStr": nonce,
            "package": package,
            "signType": "RSA",
            "paySign": pay_sign,
        },
    }


def parse_wechat_notification(headers: Mapping[str, str], raw_body: bytes) -> Dict[str, Any]:
    assert_wechat_notify_config()
    body_text = raw_body.decode("utf-8")
    verify_wechat_signature(headers, body_text)
    payload = json.loads(body_text or "{}")
    resource = payload.get("resource") or {}
    plain = decrypt_wechat_resource(resource)
    return json.loads(plain)


def wechat_request(method: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
    authorization = (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{WECHAT_MCH_ID}",'
        f'nonce_str="{nonce}",'
        f'signature="{sign_message(message)}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{WECHAT_PAY_SERIAL_NO}"'
    )
    request = Request(
        f"{WECHAT_PAY_API_BASE}{path}",
        data=body.encode("utf-8"),
        method=method,
        headers={
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "bikengbao/0.1",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"微信支付请求失败：{exc.code} {detail}") from exc


def sign_message(message: str) -> str:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise RuntimeError("微信支付需要 cryptography 依赖，请安装 requirements.txt") from exc

    private_key = serialization.load_pem_private_key(load_secret(WECHAT_PAY_PRIVATE_KEY, WECHAT_PAY_PRIVATE_KEY_PATH), password=None)
    signature = private_key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("utf-8")


def verify_wechat_signature(headers: Mapping[str, str], body_text: str) -> None:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise RuntimeError("微信支付回调验签需要 cryptography 依赖，请安装 requirements.txt") from exc

    timestamp = header_value(headers, "Wechatpay-Timestamp")
    nonce = header_value(headers, "Wechatpay-Nonce")
    signature = header_value(headers, "Wechatpay-Signature")
    message = f"{timestamp}\n{nonce}\n{body_text}\n"
    cert = x509.load_pem_x509_certificate(load_secret(WECHAT_PAY_PLATFORM_CERT, WECHAT_PAY_PLATFORM_CERT_PATH))
    cert.public_key().verify(base64.b64decode(signature), message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())


def decrypt_wechat_resource(resource: Dict[str, Any]) -> str:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError("微信支付回调解密需要 cryptography 依赖，请安装 requirements.txt") from exc

    key = WECHAT_PAY_API_V3_KEY.encode("utf-8")
    aesgcm = AESGCM(key)
    associated_data = (resource.get("associated_data") or "").encode("utf-8")
    nonce = (resource.get("nonce") or "").encode("utf-8")
    ciphertext = base64.b64decode(resource.get("ciphertext") or "")
    return aesgcm.decrypt(nonce, ciphertext, associated_data).decode("utf-8")


def assert_wechat_payment_config() -> None:
    missing = [
        name
        for name, value in {
            "WECHAT_APP_ID": WECHAT_APP_ID,
            "WECHAT_MCH_ID": WECHAT_MCH_ID,
            "WECHAT_PAY_SERIAL_NO": WECHAT_PAY_SERIAL_NO,
            "WECHAT_PAY_NOTIFY_URL": WECHAT_PAY_NOTIFY_URL,
        }.items()
        if not value
    ]
    if not WECHAT_PAY_PRIVATE_KEY and not WECHAT_PAY_PRIVATE_KEY_PATH:
        missing.append("WECHAT_PAY_PRIVATE_KEY 或 WECHAT_PAY_PRIVATE_KEY_PATH")
    if missing:
        raise RuntimeError(f"微信支付配置缺失：{', '.join(missing)}")


def assert_wechat_notify_config() -> None:
    missing = []
    if not WECHAT_PAY_API_V3_KEY:
        missing.append("WECHAT_PAY_API_V3_KEY")
    if not WECHAT_PAY_PLATFORM_CERT and not WECHAT_PAY_PLATFORM_CERT_PATH:
        missing.append("WECHAT_PAY_PLATFORM_CERT 或 WECHAT_PAY_PLATFORM_CERT_PATH")
    if missing:
        raise RuntimeError(f"微信支付回调配置缺失：{', '.join(missing)}")


def load_secret(value: str, path: str) -> bytes:
    if value:
        return value.replace("\\n", "\n").encode("utf-8")
    return Path(path).read_bytes()


def header_value(headers: Mapping[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    raise RuntimeError(f"微信支付回调缺少请求头：{name}")
