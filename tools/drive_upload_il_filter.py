"""Drive に train_il_filter_colab.ipynb を追加 upload (= 既存 token 流用)。

Usage:
    .venv/bin/python tools/drive_upload_il_filter.py

前提: tools/drive_upload_for_colab.py で OAuth consent 完了済
      (= ~/.config/orbit_wars_google_token.json 存在)
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    pass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path.home() / ".config" / "orbit_wars_google_token.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO_ROOT / "notebooks" / "train_il_filter_colab.ipynb"
FOLDER_NAME = "orbit-wars"


def main() -> int:
    if not TOKEN_PATH.exists():
        print(f"ERROR: token not found at {TOKEN_PATH}. Run drive_upload_for_colab.py first.", file=sys.stderr)
        return 1
    if not NOTEBOOK.exists():
        print(f"ERROR: notebook not found at {NOTEBOOK}", file=sys.stderr)
        return 1

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build("drive", "v3", credentials=creds)

    # Find existing orbit-wars folder
    resp = service.files().list(
        q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
    ).execute()
    items = resp.get("files", [])
    if not items:
        print(f"ERROR: folder '{FOLDER_NAME}' not found in Drive", file=sys.stderr)
        return 1
    folder_id = items[0]["id"]

    # Upload (or update) notebook
    name = NOTEBOOK.name
    q = f"name='{name}' and '{folder_id}' in parents and trashed=false"
    existing = service.files().list(q=q, fields="files(id, name)").execute().get("files", [])
    media = MediaFileUpload(str(NOTEBOOK), mimetype="application/x-ipynb+json", resumable=True)
    if existing:
        fid = existing[0]["id"]
        result = service.files().update(fileId=fid, media_body=media, fields="id, webViewLink").execute()
    else:
        body = {"name": name, "parents": [folder_id]}
        result = service.files().create(body=body, media_body=media, fields="id, webViewLink").execute()

    colab_url = f"https://colab.research.google.com/drive/{result['id']}"
    print(f"\nIL filter notebook uploaded")
    print(f"★ Open in Colab: {colab_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
