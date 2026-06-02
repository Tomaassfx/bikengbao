import uuid
from typing import Dict

from ..config import PAYMENT_PROVIDER


def create_payment(order: Dict) -> Dict:
    if PAYMENT_PROVIDER == "mock":
        return {
            "mode": "mock",
            "params": {},
            "paymentId": f"mockpay_{uuid.uuid4().hex}"
        }

    if PAYMENT_PROVIDER == "wechat":
        return {
            "mode": "wechat",
            "params": {
                "timeStamp": "",
                "nonceStr": "",
                "package": "",
                "signType": "RSA",
                "paySign": ""
            },
            "paymentId": ""
        }

    raise NotImplementedError(f"Payment provider {PAYMENT_PROVIDER} is not configured.")
