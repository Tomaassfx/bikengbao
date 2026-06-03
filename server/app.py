import cgi
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .adapters.file_storage import active_file_storage_provider, delete_upload, save_upload
from .adapters.ocr import extract_text
from .adapters.payment import create_payment
from .config import AI_PROVIDER, HOST, OCR_PROVIDER, PAYMENT_PROVIDER, PORT
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
        user_id = DEFAULT_USER_ID if not code else f"wx_{abs(hash(code)) % 100000000}"
        token = f"demo-token-{user_id}"
        db = load_db()
        db["users"][user_id] = {
            "id": user_id,
            "nickname": "避坑宝用户",
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
        file_record["ocrText"] = extract_text(file_record)

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
            "paidAt": "",
        }
        payment = create_payment(order)
        order["paymentId"] = payment.get("paymentId", "")
        db["orders"][order["id"]] = order
        save_db(db)
        self.send_json({"order": order, "payment": payment}, status=201)

    def handle_mock_pay(self, user_id: str, order_id: str) -> None:
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

    def route(self) -> Tuple[str, Dict[str, Any]]:
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)

    def match_report_id(self, route: str) -> Optional[str]:
        match = re.fullmatch(r"/v1/reports/([^/]+)", route)
        return match.group(1) if match else None

    def current_user_id(self) -> str:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer demo-token-"):
            return auth.replace("Bearer demo-token-", "", 1)
        return DEFAULT_USER_ID

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body or "{}")

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

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[api] {self.address_string()} {fmt % args}")


def run() -> None:
    ensure_storage()
    server = ThreadingHTTPServer((HOST, PORT), BikengbaoHandler)
    print(f"Bikengbao API listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
