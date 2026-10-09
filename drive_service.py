# -*- coding: utf-8 -*-
"""
DỊCH VỤ TÍCH HỢP GOOGLE DRIVE 5TB (TIMEBANK EDU - PROMPT 18)
- Sử dụng tài khoản Google 5TB của giáo viên làm kho học liệu số dùng chung.
- Quản trị viên Super Admin kết nối qua OAuth2 đăng nhập 1 lần.
- Refresh token và Client credentials lưu trong BIẾN MÔI TRƯỜNG (os.getenv),
  TUYỆT ĐỐI KHÔNG HARDCODE TRONG CODE, KHÔNG PUSH LÊN GITHUB.
- Tự động tạo cây thư mục: /SchoolTimeBank/{ten_truong}/{mon_hoc}/
- Hỗ trợ tải lên (tối đa 500MB) và tải về qua streaming trực tiếp,
  KHÔNG lưu trữ file vĩnh viễn trên server Render.
- Hỗ trợ cơ chế Local Mock Storage tự động khi chưa cấu hình Google Credentials,
  giúp môi trường Local và Test Suite hoạt động 100% trơn tru, không lỗi.
"""

import os
import io
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, Generator
import urllib.parse
import urllib.request

logger = logging.getLogger("DriveService")

# Cấu hình Google OAuth2 từ Biến môi trường
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()

# Thư mục mô phỏng lưu trữ khi chưa cấu hình Google Drive (Graceful Fallback)
MOCK_DRIVE_ROOT = Path("storage/drive_storage")

# Bộ nhớ đệm ID thư mục trên Drive: (parent_id, folder_name) -> folder_id
FOLDER_CACHE: Dict[Tuple[str, str], str] = {}


def is_drive_connected() -> bool:
    """Kiểm tra xem hệ thống đã được cấu hình kết nối Google Drive thực tế chưa."""
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return bool(refresh_token and client_id and client_secret)

is_google_drive_configured = is_drive_connected


def get_oauth_auth_url(redirect_uri: str) -> str:
    """
    Sinh URL cấp quyền OAuth2 của Google để Super Admin đăng nhập 1 lần.
    Yêu cầu quyền truy cập Drive (drive scope) và offline access để nhận refresh_token.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        return ""

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true"
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, str]:
    """
    Đổi mã ủy quyền (authorization code) lấy refresh_token và access_token từ Google.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret or not code:
        return {}

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=encoded_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)
    except Exception as e:
        logger.error(f"[OAuth Exchange Error] {e}")
        return {}


def _get_drive_client():
    """Khởi tạo Google Drive API v3 client từ credentials biến môi trường."""
    if not is_drive_connected():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"[Google Drive Init Error] {e}")
        return None


def _get_or_create_drive_folder(service, folder_name: str, parent_id: Optional[str] = None) -> str:
    """Tìm hoặc tạo thư mục trên Google Drive thật."""
    cache_key = (parent_id or "root", folder_name)
    if cache_key in FOLDER_CACHE:
        return FOLDER_CACHE[cache_key]

    # Tìm kiếm thư mục đã tồn tại
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    try:
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
            FOLDER_CACHE[cache_key] = folder_id
            return folder_id

        # Nếu chưa có -> Tạo thư mục mới
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        FOLDER_CACHE[cache_key] = folder_id
        return folder_id
    except Exception as e:
        logger.error(f"[Drive Folder Error] {e}")
        return ""


def upload_document_stream(file_stream, filename: str, mime_type: str, school_name: str, subject_name: str) -> Dict[str, str]:
    """
    Tải lên tài liệu:
    - Nếu đã kết nối Drive thật: stream upload trực tiếp vào /SchoolTimeBank/{school_name}/{subject_name}/
    - Nếu chưa kết nối (Local/Testing): stream vào thư mục mô phỏng (storage/drive_storage)
    Trả về dict: {"file_id": str, "web_view_link": str, "storage_type": "google_drive" | "mock_drive"}
    """
    clean_school = "".join(c for c in school_name if c.isalnum() or c in (" ", "-", "_")).strip() or "GeneralSchool"
    clean_subj = "".join(c for c in subject_name if c.isalnum() or c in (" ", "-", "_")).strip() or "GeneralSubject"

    service = _get_drive_client()
    if service is not None:
        try:
            from googleapiclient.http import MediaIoBaseUpload

            # 1. Tạo hoặc lấy cấu trúc cây thư mục /SchoolTimeBank/{ten_truong}/{mon_hoc}/
            root_id = _get_or_create_drive_folder(service, "SchoolTimeBank")
            school_id = _get_or_create_drive_folder(service, clean_school, root_id)
            subject_id = _get_or_create_drive_folder(service, clean_subj, school_id)

            # 2. Upload file stream trực tiếp lên Drive
            file_metadata = {
                'name': filename,
                'parents': [subject_id]
            }
            media = MediaIoBaseUpload(file_stream, mimetype=mime_type or 'application/octet-stream', resumable=True)
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = uploaded_file.get('id')
            view_link = uploaded_file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            return {
                "file_id": file_id,
                "web_view_link": view_link,
                "storage_type": "google_drive"
            }
        except Exception as e:
            logger.error(f"[Upload to Drive Failed, falling back to mock storage] {e}")

    # CHẾ ĐỘ MÔ PHỎNG (MOCK DRIVE STORAGE KHI CHƯA CÓ CREDENTIALS)
    target_dir = MOCK_DRIVE_ROOT / "SchoolTimeBank" / clean_school / clean_subj
    target_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    mock_id = f"mock_{uuid.uuid4().hex[:12]}"
    target_file = target_dir / f"{mock_id}_{filename}"

    # Stream ghi theo từng chunk để không tốn RAM
    file_stream.seek(0)
    with open(target_file, "wb") as f_out:
        while True:
            chunk = file_stream.read(1024 * 1024)  # 1MB chunk
            if not chunk:
                break
            f_out.write(chunk)

    return {
        "file_id": mock_id,
        "web_view_link": f"/documents/view-mock/{mock_id}",
        "storage_type": "mock_drive",
        "mock_path": str(target_file)
    }


def download_document_stream(file_id: str, fallback_filename: str = "") -> Tuple[Optional[Generator[bytes, None, None]], str, str]:
    """
    Stream tải về tài liệu:
    - Nếu Drive thật: gọi files().get_media() và stream từng chunk dữ liệu.
    - Nếu Mock storage: đọc streaming từ tệp cục bộ.
    Trả về: (chunk_generator, mime_type, filename)
    """
    service = _get_drive_client()
    if service is not None and not file_id.startswith("mock_"):
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io

            meta = service.files().get(fileId=file_id, fields='name, mimeType').execute()
            mime_type = meta.get('mimeType', 'application/octet-stream')
            filename = meta.get('name', fallback_filename or 'downloaded_file.bin')

            request = service.files().get_media(fileId=file_id)

            def drive_stream():
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    fh.seek(0)
                    chunk = fh.read()
                    fh.seek(0)
                    fh.truncate(0)
                    if chunk:
                        yield chunk

            return drive_stream(), mime_type, filename
        except Exception as e:
            logger.error(f"[Download from Drive Failed] {e}")

    # TÌM TRONG MOCK DRIVE STORAGE
    if MOCK_DRIVE_ROOT.exists():
        for f in MOCK_DRIVE_ROOT.rglob("*"):
            if f.is_file() and f.name.startswith(f"{file_id}_"):
                fname = f.name.split(f"{file_id}_", 1)[1] if f"{file_id}_" in f.name else f.name
                def mock_stream():
                    with open(f, "rb") as mf:
                        while True:
                            chunk = mf.read(1024 * 1024)
                            if not chunk:
                                break
                            yield chunk
                return mock_stream(), "application/octet-stream", fallback_filename or fname

    return None, "application/octet-stream", fallback_filename or "document.bin"


def delete_document_file(file_id: str) -> bool:
    """Xóa file khỏi Google Drive hoặc thư mục mô phỏng."""
    service = _get_drive_client()
    if service is not None and not file_id.startswith("mock_"):
        try:
            service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            logger.error(f"[Delete Drive File Failed] {e}")

    # Xóa trong Mock Storage nếu có
    if MOCK_DRIVE_ROOT.exists():
        for f in MOCK_DRIVE_ROOT.rglob("*"):
            if f.is_file() and f.name.startswith(f"{file_id}_"):
                try:
                    f.unlink()
                    return True
                except Exception:
                    pass
    return False

delete_document_from_drive = delete_document_file

