from typing import Dict

from ..config import OCR_PROVIDER


def extract_text(file_record: Dict) -> str:
    """OCR adapter placeholder.

    Replace this function when Tencent Cloud/Baidu/Ali/Volcengine OCR credentials
    are available. The current mock keeps the request path real while using user
    supplied text as the primary source for report generation.
    """
    if OCR_PROVIDER != "mock":
      raise NotImplementedError(f"OCR provider {OCR_PROVIDER} is not configured yet.")
    filename = file_record.get("filename", "上传文件")
    doc_type = file_record.get("docType", "资料")
    return f"{doc_type} {filename} 已上传，等待真实 OCR 识别。"
