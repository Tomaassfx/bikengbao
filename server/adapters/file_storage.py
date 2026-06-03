import mimetypes
from pathlib import Path
from typing import Any, Dict

from ..config import (
    BLOB_ACCESS,
    BLOB_READ_WRITE_TOKEN,
    FILE_STORAGE_PROVIDER,
    UPLOAD_DIR,
)


def save_upload(file_id: str, filename: str, body: bytes, content_type: str = "") -> Dict[str, Any]:
    if use_blob_storage():
        return save_blob_upload(file_id, filename, body, content_type)
    return save_local_upload(file_id, filename, body)


def delete_upload(file_record: Dict[str, Any]) -> None:
    if file_record.get("storage") == "blob":
        delete_blob_upload(file_record)
        return
    delete_local_upload(file_record)


def use_blob_storage() -> bool:
    return FILE_STORAGE_PROVIDER == "blob" and bool(BLOB_READ_WRITE_TOKEN)


def active_file_storage_provider() -> str:
    return "blob" if use_blob_storage() else "local"


def save_local_upload(file_id: str, filename: str, body: bytes) -> Dict[str, Any]:
    suffix = Path(filename).suffix or ".upload"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / f"{file_id}{suffix}"
    with saved_path.open("wb") as output:
        output.write(body)
    return {
        "storage": "local",
        "path": str(saved_path),
    }


def save_blob_upload(file_id: str, filename: str, body: bytes, content_type: str = "") -> Dict[str, Any]:
    try:
        from vercel.blob import BlobClient
    except ImportError as exc:
        raise RuntimeError("Blob storage requires the vercel Python SDK. Install requirements.txt first.") from exc

    suffix = Path(filename).suffix or ".upload"
    safe_name = Path(filename).name.replace("/", "_")
    blob_path = f"uploads/{file_id}{suffix}"
    resolved_content_type = content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

    client = BlobClient(token=BLOB_READ_WRITE_TOKEN)
    result = client.put(
        blob_path,
        body,
        access=BLOB_ACCESS if BLOB_ACCESS == "public" else "public",
        content_type=resolved_content_type,
        overwrite=False,
    )
    return {
        "storage": "blob",
        "path": result.pathname,
        "blobUrl": result.url,
        "blobDownloadUrl": result.download_url,
        "contentType": result.content_type,
    }


def delete_local_upload(file_record: Dict[str, Any]) -> None:
    path = Path(file_record.get("path", ""))
    if path.exists() and path.is_file():
        path.unlink()


def delete_blob_upload(file_record: Dict[str, Any]) -> None:
    url_or_path = file_record.get("blobUrl") or file_record.get("path")
    if not url_or_path:
        return
    try:
        from vercel.blob import BlobClient
    except ImportError:
        return

    client = BlobClient(token=BLOB_READ_WRITE_TOKEN)
    client.delete(url_or_path)
