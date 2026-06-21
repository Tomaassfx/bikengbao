import cgi
import hmac
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .adapters.file_storage import active_file_storage_provider, delete_upload, save_upload
from .adapters.ocr import extract_text
from .adapters.payment import create_payment, parse_alipay_notification, parse_wechat_notification
from .adapters.wechat_auth import resolve_wechat_session
from .config import (
    AI_PROVIDER,
    AUTH_PROVIDER,
    BIKENGBAO_ADMIN_CONFIRM_TOKEN,
    BIKENGBAO_ASSET_UPLOAD_TOKEN,
    HOST,
    MAX_UPLOAD_BYTES,
    OCR_PROVIDER,
    PAYMENT_PROVIDER,
    PORT,
)
from .rules import generate_report
from .storage import active_db_provider, ensure_storage, load_db, now_ms, now_text, reports_for_user, save_db

DEFAULT_USER_ID = "demo_user"


class BikengbaoHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_json({"ok": True})

    def do_GET(self) -> None:
        route, params = self.route()
        user_id = self.current_user_id()

        if route == "/health":
            self.send_json(
                {
                    "ok": True,
                    "service": "bikengbao-api",
                    "aiProvider": AI_PROVIDER,
                    "authProvider": AUTH_PROVIDER,
                    "ocrProvider": OCR_PROVIDER,
                    "paymentProvider": PAYMENT_PROVIDER,
                    "dbProvider": active_db_provider(),
                    "fileStorageProvider": active_file_storage_provider(),
                }
            )
            return

        if route == "/v1/reports":
            reports = [self.public_report(report) for report in reports_for_user(user_id)]
            self.send_json({"reports": reports})
            return

        order_id = self.match_order_id(route)
        if order_id:
            self.handle_get_order(user_id, order_id)
            return

        report_id = self.match_report_id(route)
        if report_id:
            db = load_db()
            report = db["reports"].get(report_id)
            if not report or report.get("deleted") or report.get("userId") != user_id:
                self.send_error_json(404, "报告不存在")
                return
            self.send_json({"report": self.public_report(report)})
            return

        self.send_error_json(404, "接口不存在")

    def do_POST(self) -> None:
        route, params = self.route()
        user_id = self.current_user_id()

        if route == "/v1/auth/wechat":
            self.handle_auth()
            return

        if route == "/v1/files":
            self.handle_file_upload(user_id)
            return

        if route == "/v1/audits":
            self.handle_create_audit(user_id)
            return

        if route == "/v1/orders":
            self.handle_create_order(user_id)
            return

        payment_asset_match = re.fullmatch(r"/v1/admin/payment-assets/(alipay|wechat)", route)
        if payment_asset_match:
            self.handle_payment_asset_upload(payment_asset_match.group(1))
            return

        admin_confirm_match = re.fullmatch(r"/v1/admin/orders/([^/]+)/confirm-payment", route)
        if admin_confirm_match:
            self.handle_admin_confirm_payment(admin_confirm_match.group(1))
            return

        if route == "/v1/payments/wechat/notify":
            self.handle_wechat_pay_notify()
            return

        if route == "/v1/payments/alipay/notify":
            self.handle_alipay_notify()
            return

        order_match = re.fullmatch(r"/v1/orders/([^/]+)/mock-pay", route)
        if order_match:
            self.handle_mock_pay(user_id, order_match.group(1))
            return

        self.send_error_json(404, "接口不存在")

    def do_DELETE(self) -> None:
        route, params = self.route()
        report_id = self.match_report_id(route)
        if not report_id:
            self.send_error_json(404, "接口不存在")
            return

        user_id = self.current_user_id()
        db = load_db()
        report = db["reports"].get(report_id)
        if not report or report.get("userId") != user_id:
            self.send_error_json(404, "报告不存在")
            return

        report["deleted"] = True
        report["deletedAt"] = now_text()
        for file_id in report.get("fileIds", []):
            file_record = db["files"].get(file_id)
            if not file_record:
                continue
            file_record["deleted"] = True
            delete_upload(file_record)
        save_db(db)
        self.send_json({"ok": True})

    def handle_auth(self) -> None:
        payload = self.read_json()
        code = payload.get("code", "")
        try:
            session = resolve_wechat_session(code)
        except RuntimeError as error:
            self.send_error_json(502, str(error))
            return
        user_id = session["userId"]
        token = f"demo-token-{user_id}"
        db = load_db()
        db["users"][user_id] = {
            "id": user_id,
            "nickname": "避坑宝用户",
            "openid": session.get("openid", ""),
            "unionid": session.get("unionid", ""),
            "authProvider": session.get("provider", "mock"),
            "createdAt": db["users"].get(user_id, {}).get("createdAt") or now_text(),
            "lastLoginAt": now_text(),
        }
        save_db(db)
        self.send_json({"token": token, "user": db["users"][user_id]})

    def handle_file_upload(self, user_id: str) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error_json(400, "请使用 multipart/form-data 上传文件")
            return
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > MAX_UPLOAD_BYTES:
            self.send_error_json(413, "文件过大，请压缩后再上传")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            self.send_error_json(400, "未收到文件")
            return

        file_id = uuid.uuid4().hex
        filename = file_item.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        file_body = file_item.file.read()
        storage_record = save_upload(
            file_id,
            filename,
            file_body,
            getattr(file_item, "type", "") or "",
        )

        file_record = {
            "id": file_id,
            "userId": user_id,
            "filename": filename,
            "docType": form.getvalue("docType") or "",
            "createdAt": now_text(),
            "createdAtMs": now_ms(),
            "deleted": False,
            **storage_record,
        }
        try:
            file_record["ocrText"] = extract_text(file_record)
        except RuntimeError as error:
            delete_upload(file_record)
            self.send_error_json(502, str(error))
            return

        db = load_db()
        db["files"][file_id] = file_record
        save_db(db)
        self.send_json({"file": self.public_file(file_record)}, status=201)

    def handle_create_audit(self, user_id: str) -> None:
        payload = self.read_json()
        db = load_db()
        files = [
            db["files"][file_id]
            for file_id in payload.get("fileIds", [])
            if file_id in db["files"] and db["files"][file_id].get("userId") == user_id
        ]
        report = generate_report(user_id, payload, files)
        report["createdAtMs"] = now_ms()
        db["reports"][report["id"]] = report
        save_db(db)
        self.send_json({"report": self.public_report(report)}, status=201)

    def handle_create_order(self, user_id: str) -> None:
        payload = self.read_json()
        db = load_db()
        report_id = payload.get("reportId")
        report = db["reports"].get(report_id)
        if not report or report.get("userId") != user_id or report.get("deleted"):
            self.send_error_json(404, "报告不存在")
            return

        amount = int(payload.get("amount") or 59)
        if amount not in [29, 59, 99, 199, 499]:
            self.send_error_json(400, "价格档位不合法")
            return

        order = {
            "id": uuid.uuid4().hex,
            "userId": user_id,
            "reportId": report_id,
            "amount": amount,
            "status": "pending",
            "createdAt": now_text(),
            "createdAtMs": now_ms(),
            "paidAt": "",
            "description": "避坑宝装修审核报告",
            "clientType": payload.get("clientType") or "web",
            "openid": db["users"].get(user_id, {}).get("openid", ""),
            "provider": PAYMENT_PROVIDER,
        }
        try:
            payment = create_payment(order)
        except RuntimeError as error:
            self.send_error_json(502, str(error))
            return
        order["paymentId"] = payment.get("paymentId", "")
        if payment.get("mode") == "manual_qr":
            order["manualReference"] = payment.get("reference", "")
            order["paymentExpiresInMinutes"] = payment.get("expiresInMinutes", 0)
        db["orders"][order["id"]] = order
        save_db(db)
        self.send_json({"order": order, "payment": payment}, status=201)

    def handle_mock_pay(self, user_id: str, order_id: str) -> None:
        if PAYMENT_PROVIDER != "mock":
            self.send_error_json(403, "当前环境不允许模拟支付")
            return

        db = load_db()
        order = db["orders"].get(order_id)
        if not order or order.get("userId") != user_id:
            self.send_error_json(404, "订单不存在")
            return
        if order.get("status") == "paid":
            self.send_json({"order": order})
            return

        report = db["reports"].get(order["reportId"])
        if not report:
            self.send_error_json(404, "报告不存在")
            return

        order["status"] = "paid"
        order["paidAt"] = now_text()
        report["unlocked"] = True
        report["unlockedAt"] = now_text()
        save_db(db)
        self.send_json({"order": order, "report": self.public_report(report)})

    def handle_admin_confirm_payment(self, order_id: str) -> None:
        if not self.admin_authorized():
            self.send_error_json(401, "后台确认密钥无效")
            return

        payload = self.read_json()
        db = load_db()
        order = db["orders"].get(order_id)
        if not order:
            self.send_error_json(404, "订单不存在")
            return
        if order.get("provider") not in {"manual", "manual_qr"}:
            self.send_error_json(400, "该订单不是人工确认支付订单")
            return

        expected_amount = int(order.get("amount") or 0)
        try:
            paid_amount = int(payload.get("paidAmount") or expected_amount)
        except (TypeError, ValueError):
            self.send_error_json(400, "付款金额格式不正确")
            return
        if paid_amount != expected_amount:
            self.send_error_json(400, f"付款金额不匹配，应为 {expected_amount} 元")
            return

        report = db["reports"].get(order["reportId"])
        if not report:
            self.send_error_json(404, "报告不存在")
            return

        if order.get("status") != "paid":
            order["status"] = "paid"
            order["paidAt"] = now_text()
        order["manualConfirmedAt"] = order.get("manualConfirmedAt") or now_text()
        order["manualConfirmedBy"] = str(payload.get("confirmedBy") or "admin")[:80]
        order["transactionId"] = str(payload.get("transactionId") or order.get("manualReference") or "")[:120]
        order["paymentStatus"] = "MANUAL_CONFIRMED"
        order["paymentNote"] = str(payload.get("note") or "")[:240]
        report["unlocked"] = True
        report["unlockedAt"] = report.get("unlockedAt") or now_text()
        save_db(db)
        self.send_json({"order": self.public_order(order), "report": self.public_report(report)})

    def handle_payment_asset_upload(self, channel: str) -> None:
        if not self.asset_upload_authorized():
            self.send_error_json(401, "付款资产上传密钥无效")
            return

        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error_json(400, "请使用 multipart/form-data 上传图片")
            return
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > MAX_UPLOAD_BYTES:
            self.send_error_json(413, "图片过大，请压缩后再上传")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
        )
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            self.send_error_json(400, "未收到图片")
            return
        image_type = getattr(file_item, "type", "") or ""
        if not image_type.startswith("image/"):
            self.send_error_json(400, "付款资产必须是图片")
            return

        filename = file_item.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        file_body = file_item.file.read()
        storage_record = save_upload(
            f"payment-{channel}-{uuid.uuid4().hex}",
            filename,
            file_body,
            image_type,
        )
        if storage_record.get("storage") != "blob" or not storage_record.get("blobUrl"):
            delete_upload(storage_record)
            self.send_error_json(502, "付款资产必须上传到 Vercel Blob")
            return
        self.send_json(
            {
                "channel": channel,
                "url": storage_record["blobUrl"],
                "contentType": storage_record.get("contentType", image_type),
            },
            status=201,
        )

    def handle_get_order(self, user_id: str, order_id: str) -> None:
        db = load_db()
        order = db["orders"].get(order_id)
        if not order or order.get("userId") != user_id:
            self.send_error_json(404, "订单不存在")
            return
        payload: Dict[str, Any] = {"order": self.public_order(order)}
        report = db["reports"].get(order.get("reportId", ""))
        if report:
            payload["report"] = self.public_report(report)
        self.send_json(payload)

    def handle_wechat_pay_notify(self) -> None:
        raw_body = self.read_raw_body()
        try:
            transaction = parse_wechat_notification(self.headers, raw_body)
        except Exception as error:
            self.send_json({"code": "FAIL", "message": str(error)}, status=400)
            return

        order_id = transaction.get("out_trade_no", "")
        trade_state = transaction.get("trade_state", "")
        db = load_db()
        order = db["orders"].get(order_id)
        if not order:
            self.send_json({"code": "FAIL", "message": "订单不存在"}, status=404)
            return
        if trade_state != "SUCCESS":
            order["status"] = "failed"
            order["paymentError"] = trade_state or "UNKNOWN"
            save_db(db)
            self.send_json({"code": "SUCCESS", "message": "忽略非成功支付"})
            return

        report = db["reports"].get(order["reportId"])
        if not report:
            self.send_json({"code": "FAIL", "message": "报告不存在"}, status=404)
            return

        order["status"] = "paid"
        order["paidAt"] = now_text()
        order["transactionId"] = transaction.get("transaction_id", "")
        report["unlocked"] = True
        report["unlockedAt"] = now_text()
        save_db(db)
        self.send_json({"code": "SUCCESS", "message": "成功"})

    def handle_alipay_notify(self) -> None:
        raw_body = self.read_raw_body()
        try:
            notification = parse_alipay_notification(raw_body)
        except Exception as error:
            self.send_text("fail", status=400)
            print(f"[api] 支付宝回调验签失败：{error}")
            return

        order_id = notification.get("out_trade_no", "")
        trade_status = notification.get("trade_status", "")
        db = load_db()
        order = db["orders"].get(order_id)
        if not order:
            self.send_text("fail", status=404)
            return
        if trade_status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
            order["status"] = "failed" if trade_status == "TRADE_CLOSED" else "pending"
            order["paymentStatus"] = trade_status or "UNKNOWN"
            save_db(db)
            self.send_text("success")
            return

        report = db["reports"].get(order["reportId"])
        if not report:
            self.send_text("fail", status=404)
            return

        order["status"] = "paid"
        order["paidAt"] = order.get("paidAt") or now_text()
        order["transactionId"] = notification.get("trade_no", "")
        order["buyerId"] = notification.get("buyer_id", "")
        order["paymentStatus"] = trade_status
        report["unlocked"] = True
        report["unlockedAt"] = report.get("unlockedAt") or now_text()
        save_db(db)
        self.send_text("success")

    def route(self) -> Tuple[str, Dict[str, Any]]:
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)

    def match_report_id(self, route: str) -> Optional[str]:
        match = re.fullmatch(r"/v1/reports/([^/]+)", route)
        return match.group(1) if match else None

    def match_order_id(self, route: str) -> Optional[str]:
        match = re.fullmatch(r"/v1/orders/([^/]+)", route)
        return match.group(1) if match else None

    def current_user_id(self) -> str:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer demo-token-"):
            return auth.replace("Bearer demo-token-", "", 1)
        return DEFAULT_USER_ID

    def admin_authorized(self) -> bool:
        if not BIKENGBAO_ADMIN_CONFIRM_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        provided = ""
        if auth.startswith("Bearer "):
            provided = auth.replace("Bearer ", "", 1)
        provided = provided or self.headers.get("X-Admin-Token", "")
        return hmac.compare_digest(provided, BIKENGBAO_ADMIN_CONFIRM_TOKEN)

    def asset_upload_authorized(self) -> bool:
        if not BIKENGBAO_ASSET_UPLOAD_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        provided = auth.replace("Bearer ", "", 1) if auth.startswith("Bearer ") else ""
        return hmac.compare_digest(provided, BIKENGBAO_ASSET_UPLOAD_TOKEN)

    def read_json(self) -> Dict[str, Any]:
        body = self.read_raw_body().decode("utf-8")
        try:
            return json.loads(body or "{}")
        except json.JSONDecodeError:
            return {}

    def read_raw_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def public_file(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": file_record["id"],
            "filename": file_record["filename"],
            "docType": file_record.get("docType", ""),
            "ocrText": file_record.get("ocrText", ""),
            "createdAt": file_record.get("createdAt", ""),
        }

    def public_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        public = dict(report)
        public.pop("userId", None)
        public.pop("deleted", None)
        if not public.get("unlocked"):
            public["risks"] = report.get("risks", [])[:3]
        return public

    def public_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": order.get("id", ""),
            "reportId": order.get("reportId", ""),
            "amount": order.get("amount", 0),
            "status": order.get("status", ""),
            "provider": order.get("provider", ""),
            "paymentId": order.get("paymentId", ""),
            "manualReference": order.get("manualReference", ""),
            "paymentStatus": order.get("paymentStatus", ""),
            "createdAt": order.get("createdAt", ""),
            "paidAt": order.get("paidAt", ""),
        }

    def send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"message": message}, status=status)

    def send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[api] {self.address_string()} {fmt % args}")


def run() -> None:
    ensure_storage()
    server = ThreadingHTTPServer((HOST, PORT), BikengbaoHandler)
    print(f"Bikengbao API listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
