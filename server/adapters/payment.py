import base64
import datetime as dt
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request, urlopen

from ..config import (
    ALIPAY_APP_ID,
    ALIPAY_APP_PRIVATE_KEY,
    ALIPAY_APP_PRIVATE_KEY_PATH,
    ALIPAY_GATEWAY,
    ALIPAY_NOTIFY_URL,
    ALIPAY_PUBLIC_KEY,
    ALIPAY_PUBLIC_KEY_PATH,
    ALIPAY_RETURN_URL,
    MANUAL_PAYMENT_ACCOUNT_HINT,
    MANUAL_PAYMENT_ACCOUNT_NAME,
    MANUAL_PAYMENT_EXPIRES_MINUTES,
    MANUAL_PAYMENT_NOTE_PREFIX,
    MANUAL_PAYMENT_QR_IMAGE_URL,
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

    if PAYMENT_PROVIDER == "alipay":
        return create_alipay_page_payment(order)

    if PAYMENT_PROVIDER in {"manual", "manual_qr"}:
        return create_manual_qr_payment(order)

    raise RuntimeError(f"Payment provider {PAYMENT_PROVIDER} is not configured.")


def create_manual_qr_payment(order: Dict[str, Any]) -> Dict[str, Any]:
    reference = manual_payment_reference(order)
    amount = int(order["amount"])
    return {
        "mode": "manual_qr",
        "paymentId": reference,
        "qrImageUrl": MANUAL_PAYMENT_QR_IMAGE_URL,
        "accountName": MANUAL_PAYMENT_ACCOUNT_NAME,
        "accountHint": MANUAL_PAYMENT_ACCOUNT_HINT,
        "reference": reference,
        "amountText": f"{amount:.2f}",
        "expiresInMinutes": MANUAL_PAYMENT_EXPIRES_MINUTES,
        "instructions": [
            "扫码后请按订单金额付款，不要合并多笔订单。",
            f"付款备注请填写：{reference}",
            "人工核对到账后，报告会自动解锁；通常在运营在线时几分钟内完成。",
        ],
    }


def manual_payment_reference(order: Dict[str, Any]) -> str:
    raw_id = str(order.get("id", "")).replace("-", "")
    short_id = raw_id[:10].upper() or uuid.uuid4().hex[:10].upper()
    prefix = "".join(str(MANUAL_PAYMENT_NOTE_PREFIX or "BKB").split()).upper()
    return f"{prefix}-{short_id}"


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


def create_alipay_page_payment(order: Dict[str, Any]) -> Dict[str, Any]:
    assert_alipay_payment_config()
    method, product_code = alipay_method(order.get("clientType", "web"))
    biz_content = {
        "out_trade_no": order["id"],
        "total_amount": f"{int(order['amount']):.2f}",
        "subject": order.get("description") or "避坑宝装修审核报告",
        "product_code": product_code,
    }
    params = {
        "app_id": ALIPAY_APP_ID,
        "method": method,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": ALIPAY_NOTIFY_URL,
        "return_url": alipay_return_url(order),
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    params["sign"] = sign_alipay_params(params)
    return {
        "mode": "alipay",
        "paymentId": order["id"],
        "paymentUrl": f"{ALIPAY_GATEWAY}?{urlencode(params)}",
        "params": {
            "method": method,
            "productCode": product_code,
        },
    }


def parse_alipay_notification(raw_body: bytes) -> Dict[str, Any]:
    assert_alipay_notify_config()
    form = dict(parse_qsl(raw_body.decode("utf-8"), keep_blank_values=True))
    if not form:
        raise RuntimeError("支付宝回调为空")
    verify_alipay_signature(form)
    return form


def alipay_method(client_type: str) -> Tuple[str, str]:
    if client_type == "mobile":
        return "alipay.trade.wap.pay", "QUICK_WAP_WAY"
    return "alipay.trade.page.pay", "FAST_INSTANT_TRADE_PAY"


def alipay_return_url(order: Dict[str, Any]) -> str:
    if not ALIPAY_RETURN_URL:
        return ""
    separator = "&" if "?" in ALIPAY_RETURN_URL else "?"
    return f"{ALIPAY_RETURN_URL}{separator}reportId={order['reportId']}"


def sign_alipay_params(params: Mapping[str, Any]) -> str:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise RuntimeError("支付宝支付需要 cryptography 依赖，请安装 requirements.txt") from exc

    content = alipay_sign_content(params)
    private_key = serialization.load_pem_private_key(load_pem_secret(ALIPAY_APP_PRIVATE_KEY, ALIPAY_APP_PRIVATE_KEY_PATH, "PRIVATE KEY"), password=None)
    signature = private_key.sign(content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("utf-8")


def verify_alipay_signature(params: Mapping[str, str]) -> None:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise RuntimeError("支付宝回调验签需要 cryptography 依赖，请安装 requirements.txt") from exc

    signature = params.get("sign", "")
    if not signature:
        raise RuntimeError("支付宝回调缺少 sign")
    content = alipay_sign_content(params)
    public_key = serialization.load_pem_public_key(load_pem_secret(ALIPAY_PUBLIC_KEY, ALIPAY_PUBLIC_KEY_PATH, "PUBLIC KEY"))
    public_key.verify(base64.b64decode(signature), content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())


def alipay_sign_content(params: Mapping[str, Any]) -> str:
    pairs = []
    for key in sorted(params):
        if key in {"sign", "sign_type"}:
            continue
        value = params[key]
        if value is None or value == "":
            continue
        pairs.append(f"{key}={value}")
    return "&".join(pairs)


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


def assert_alipay_payment_config() -> None:
    missing = [
        name
        for name, value in {
            "ALIPAY_APP_ID": ALIPAY_APP_ID,
            "ALIPAY_NOTIFY_URL": ALIPAY_NOTIFY_URL,
            "ALIPAY_RETURN_URL": ALIPAY_RETURN_URL,
        }.items()
        if not value
    ]
    if not ALIPAY_APP_PRIVATE_KEY and not ALIPAY_APP_PRIVATE_KEY_PATH:
        missing.append("ALIPAY_APP_PRIVATE_KEY 或 ALIPAY_APP_PRIVATE_KEY_PATH")
    if missing:
        raise RuntimeError(f"支付宝支付配置缺失：{', '.join(missing)}")


def assert_alipay_notify_config() -> None:
    missing = []
    if not ALIPAY_PUBLIC_KEY and not ALIPAY_PUBLIC_KEY_PATH:
        missing.append("ALIPAY_PUBLIC_KEY 或 ALIPAY_PUBLIC_KEY_PATH")
    if missing:
        raise RuntimeError(f"支付宝回调配置缺失：{', '.join(missing)}")


def load_secret(value: str, path: str) -> bytes:
    if value:
        return value.replace("\\n", "\n").encode("utf-8")
    return Path(path).read_bytes()


def load_pem_secret(value: str, path: str, label: str) -> bytes:
    raw = load_secret(value, path).decode("utf-8").strip()
    if "-----BEGIN" in raw:
        return raw.encode("utf-8")
    compact = "".join(raw.split())
    lines = "\n".join(compact[index : index + 64] for index in range(0, len(compact), 64))
    return f"-----BEGIN {label}-----\n{lines}\n-----END {label}-----\n".encode("utf-8")


def header_value(headers: Mapping[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    raise RuntimeError(f"微信支付回调缺少请求头：{name}")
