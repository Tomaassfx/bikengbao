import json
import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import server.adapters.payment as payment
import server.app as app
import server.storage as storage


class ManualPaymentFlowTests(unittest.TestCase):
    def setUp(self):
        self.originals = {
            "app_PAYMENT_PROVIDER": app.PAYMENT_PROVIDER,
            "app_ADMIN_TOKEN": app.BIKENGBAO_ADMIN_CONFIRM_TOKEN,
            "payment_PAYMENT_PROVIDER": payment.PAYMENT_PROVIDER,
            "payment_QR": payment.MANUAL_PAYMENT_QR_IMAGE_URL,
            "payment_ALIPAY_QR": payment.MANUAL_PAYMENT_ALIPAY_QR_IMAGE_URL,
            "payment_WECHAT_QR": payment.MANUAL_PAYMENT_WECHAT_QR_IMAGE_URL,
            "payment_ALIPAY_ACCOUNT_NAME": payment.MANUAL_PAYMENT_ALIPAY_ACCOUNT_NAME,
            "payment_WECHAT_ACCOUNT_NAME": payment.MANUAL_PAYMENT_WECHAT_ACCOUNT_NAME,
            "payment_NOTE_PREFIX": payment.MANUAL_PAYMENT_NOTE_PREFIX,
            "payment_EXPIRES": payment.MANUAL_PAYMENT_EXPIRES_MINUTES,
            "storage_DB_PROVIDER": storage.DB_PROVIDER,
            "storage_DATABASE_URL": storage.DATABASE_URL,
            "storage_DATA_DIR": storage.DATA_DIR,
            "storage_DB_PATH": storage.DB_PATH,
            "storage_UPLOAD_DIR": storage.UPLOAD_DIR,
        }
        self.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self.temp_dir.name)
        storage.DB_PROVIDER = "json"
        storage.DATABASE_URL = ""
        storage.DATA_DIR = data_dir
        storage.DB_PATH = data_dir / "db.json"
        storage.UPLOAD_DIR = data_dir / "uploads"

        app.PAYMENT_PROVIDER = "manual_qr"
        app.BIKENGBAO_ADMIN_CONFIRM_TOKEN = "admin-secret"
        payment.PAYMENT_PROVIDER = "manual_qr"
        payment.MANUAL_PAYMENT_QR_IMAGE_URL = ""
        payment.MANUAL_PAYMENT_ALIPAY_QR_IMAGE_URL = "https://example.com/alipay-qr.png"
        payment.MANUAL_PAYMENT_WECHAT_QR_IMAGE_URL = "https://example.com/wechat-qr.png"
        payment.MANUAL_PAYMENT_ALIPAY_ACCOUNT_NAME = "支付宝测试收款"
        payment.MANUAL_PAYMENT_WECHAT_ACCOUNT_NAME = "微信测试收款"
        payment.MANUAL_PAYMENT_NOTE_PREFIX = "BKB"
        payment.MANUAL_PAYMENT_EXPIRES_MINUTES = 30

        storage.ensure_json_storage()
        db = storage.load_db()
        db["reports"]["rep_manual"] = self.report_fixture()
        storage.save_db(db)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.BikengbaoHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.server_port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()
        app.PAYMENT_PROVIDER = self.originals["app_PAYMENT_PROVIDER"]
        app.BIKENGBAO_ADMIN_CONFIRM_TOKEN = self.originals["app_ADMIN_TOKEN"]
        payment.PAYMENT_PROVIDER = self.originals["payment_PAYMENT_PROVIDER"]
        payment.MANUAL_PAYMENT_QR_IMAGE_URL = self.originals["payment_QR"]
        payment.MANUAL_PAYMENT_ALIPAY_QR_IMAGE_URL = self.originals["payment_ALIPAY_QR"]
        payment.MANUAL_PAYMENT_WECHAT_QR_IMAGE_URL = self.originals["payment_WECHAT_QR"]
        payment.MANUAL_PAYMENT_ALIPAY_ACCOUNT_NAME = self.originals["payment_ALIPAY_ACCOUNT_NAME"]
        payment.MANUAL_PAYMENT_WECHAT_ACCOUNT_NAME = self.originals["payment_WECHAT_ACCOUNT_NAME"]
        payment.MANUAL_PAYMENT_NOTE_PREFIX = self.originals["payment_NOTE_PREFIX"]
        payment.MANUAL_PAYMENT_EXPIRES_MINUTES = self.originals["payment_EXPIRES"]
        storage.DB_PROVIDER = self.originals["storage_DB_PROVIDER"]
        storage.DATABASE_URL = self.originals["storage_DATABASE_URL"]
        storage.DATA_DIR = self.originals["storage_DATA_DIR"]
        storage.DB_PATH = self.originals["storage_DB_PATH"]
        storage.UPLOAD_DIR = self.originals["storage_UPLOAD_DIR"]

    def test_create_manual_qr_order_returns_payment_instructions(self):
        status, payload = self.request("POST", "/v1/orders", {"reportId": "rep_manual", "amount": 59})

        self.assertEqual(status, 201)
        self.assertEqual(payload["order"]["provider"], "manual_qr")
        self.assertEqual(payload["payment"]["mode"], "manual_qr")
        self.assertEqual(payload["payment"]["qrImageUrl"], "https://example.com/alipay-qr.png")
        self.assertEqual(payload["payment"]["accountName"], "支付宝测试收款")
        self.assertEqual(
            payload["payment"]["channels"],
            [
                {
                    "id": "alipay",
                    "label": "支付宝",
                    "qrImageUrl": "https://example.com/alipay-qr.png",
                    "accountName": "支付宝测试收款",
                    "accountHint": "支付宝收款码",
                },
                {
                    "id": "wechat",
                    "label": "微信支付",
                    "qrImageUrl": "https://example.com/wechat-qr.png",
                    "accountName": "微信测试收款",
                    "accountHint": "微信收款码",
                },
            ],
        )
        self.assertTrue(payload["payment"]["reference"].startswith("BKB-"))
        self.assertIn(payload["payment"]["reference"], payload["payment"]["instructions"][2])

    def test_legacy_manual_qr_url_is_used_for_alipay_channel(self):
        payment.MANUAL_PAYMENT_ALIPAY_QR_IMAGE_URL = ""
        payment.MANUAL_PAYMENT_WECHAT_QR_IMAGE_URL = ""
        payment.MANUAL_PAYMENT_QR_IMAGE_URL = "https://example.com/legacy-qr.png"

        result = payment.create_manual_qr_payment({"id": "ord_legacy", "amount": 59})

        self.assertEqual(result["channels"][0]["qrImageUrl"], "https://example.com/legacy-qr.png")
        self.assertEqual(result["channels"][1]["qrImageUrl"], "")

    def test_admin_confirm_requires_token_and_unlocks_report(self):
        _, order_payload = self.request("POST", "/v1/orders", {"reportId": "rep_manual", "amount": 59})
        order_id = order_payload["order"]["id"]

        status, denied = self.request(
            "POST",
            f"/v1/admin/orders/{order_id}/confirm-payment",
            {"paidAmount": 59},
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)
        self.assertIn("密钥", denied["message"])

        status, confirmed = self.request(
            "POST",
            f"/v1/admin/orders/{order_id}/confirm-payment",
            {"paidAmount": 59, "transactionId": "ali_001", "note": "到账备注匹配"},
            headers={"Authorization": "Bearer admin-secret"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(confirmed["order"]["status"], "paid")
        self.assertEqual(confirmed["order"]["paymentStatus"], "MANUAL_CONFIRMED")
        self.assertTrue(confirmed["report"]["unlocked"])
        self.assertEqual(len(confirmed["report"]["risks"]), 4)

    def test_admin_confirm_rejects_amount_mismatch(self):
        _, order_payload = self.request("POST", "/v1/orders", {"reportId": "rep_manual", "amount": 59})
        order_id = order_payload["order"]["id"]

        status, payload = self.request(
            "POST",
            f"/v1/admin/orders/{order_id}/confirm-payment",
            {"paidAmount": 29},
            headers={"X-Admin-Token": "admin-secret"},
        )
        self.assertEqual(status, 400)
        self.assertIn("金额", payload["message"])

        status, report_payload = self.request("GET", "/v1/reports/rep_manual")
        self.assertEqual(status, 200)
        self.assertFalse(report_payload["report"]["unlocked"])
        self.assertEqual(len(report_payload["report"]["risks"]), 3)

    def request(self, method, path, payload=None, headers=None):
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", self.server_port, timeout=5)
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        raw = response.read().decode("utf-8") or "{}"
        connection.close()
        return response.status, json.loads(raw)

    def report_fixture(self):
        risks = [
            {
                "id": f"risk_{index}",
                "level": "高" if index == 0 else "中",
                "category": "报价",
                "title": f"风险 {index + 1}",
                "reason": "测试风险原因",
                "ask": "请商家书面确认。",
            }
            for index in range(4)
        ]
        return {
            "id": "rep_manual",
            "userId": app.DEFAULT_USER_ID,
            "title": "人工收款测试报告",
            "docType": "报价单",
            "fileSummary": "测试报价单",
            "conclusion": "建议谨慎",
            "score": 68,
            "total": 128000,
            "unitPrice": 1438,
            "createdAt": "2026-06-14 12:00:00",
            "createdAtMs": 1,
            "vendor": "测试装修公司",
            "risks": risks,
            "items": [],
            "questions": [],
            "nextSteps": [],
            "scripts": [],
            "familySummary": "测试总结",
            "disclaimer": "仅供消费决策辅助。",
            "unlocked": False,
            "deleted": False,
            "fileIds": [],
        }


if __name__ == "__main__":
    unittest.main()
