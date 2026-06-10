import base64
import unittest
from urllib.parse import parse_qs, urlencode, urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

import server.adapters.payment as payment


class AlipayPaymentTests(unittest.TestCase):
    def setUp(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        self.private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        self.public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        self.originals = {
            "ALIPAY_APP_ID": payment.ALIPAY_APP_ID,
            "ALIPAY_APP_PRIVATE_KEY": payment.ALIPAY_APP_PRIVATE_KEY,
            "ALIPAY_APP_PRIVATE_KEY_PATH": payment.ALIPAY_APP_PRIVATE_KEY_PATH,
            "ALIPAY_PUBLIC_KEY": payment.ALIPAY_PUBLIC_KEY,
            "ALIPAY_PUBLIC_KEY_PATH": payment.ALIPAY_PUBLIC_KEY_PATH,
            "ALIPAY_GATEWAY": payment.ALIPAY_GATEWAY,
            "ALIPAY_NOTIFY_URL": payment.ALIPAY_NOTIFY_URL,
            "ALIPAY_RETURN_URL": payment.ALIPAY_RETURN_URL,
        }

        payment.ALIPAY_APP_ID = "2021000000000000"
        payment.ALIPAY_APP_PRIVATE_KEY = self.private_pem
        payment.ALIPAY_APP_PRIVATE_KEY_PATH = ""
        payment.ALIPAY_PUBLIC_KEY = self.public_pem
        payment.ALIPAY_PUBLIC_KEY_PATH = ""
        payment.ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"
        payment.ALIPAY_NOTIFY_URL = "https://example.com/v1/payments/alipay/notify"
        payment.ALIPAY_RETURN_URL = "https://example.com/report"

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(payment, name, value)

    def test_sign_content_sorts_and_excludes_signature_fields(self):
        content = payment.alipay_sign_content(
            {
                "z": "last",
                "a": "first",
                "sign": "ignored",
                "sign_type": "RSA2",
                "empty": "",
                "none": None,
            }
        )

        self.assertEqual(content, "a=first&z=last")

    def test_create_alipay_page_payment_generates_signed_payment_url(self):
        result = payment.create_alipay_page_payment(
            {
                "id": "ord_test_001",
                "reportId": "rep_test_001",
                "amount": 59,
                "description": "避坑宝装修审核报告",
                "clientType": "web",
            }
        )

        self.assertEqual(result["mode"], "alipay")
        self.assertEqual(result["paymentId"], "ord_test_001")
        self.assertEqual(result["params"]["method"], "alipay.trade.page.pay")
        parsed = urlparse(result["paymentUrl"])
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        self.assertEqual(query["app_id"], "2021000000000000")
        self.assertEqual(query["method"], "alipay.trade.page.pay")
        self.assertIn("reportId=rep_test_001", query["return_url"])
        self.assertIn("sign", query)

        payment.verify_alipay_signature(query)

    def test_parse_alipay_notification_verifies_signature(self):
        fields = {
            "app_id": "2021000000000000",
            "out_trade_no": "ord_test_001",
            "trade_no": "2026060922000000000001",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "59.00",
            "charset": "utf-8",
            "sign_type": "RSA2",
        }
        content = payment.alipay_sign_content(fields)
        private_key = serialization.load_pem_private_key(self.private_pem.encode("utf-8"), password=None)
        fields["sign"] = base64.b64encode(
            private_key.sign(content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        ).decode("utf-8")

        raw_body = urlencode(fields).encode("utf-8")
        notification = payment.parse_alipay_notification(raw_body)

        self.assertEqual(notification["out_trade_no"], "ord_test_001")
        self.assertEqual(notification["trade_status"], "TRADE_SUCCESS")


if __name__ == "__main__":
    unittest.main()
