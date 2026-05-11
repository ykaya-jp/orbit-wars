"""Drive API で train_ppo_colab.ipynb + ppo_v3_theta3.zip を upload + Colab share link 生成。

WSL2 friendly: OAuth `run_local_server(open_browser=False)` で URL print のみ、
user が手動で Windows browser で開いて consent → localhost に redirect 受信。

Usage:
    .venv/bin/python tools/drive_upload_for_colab.py

初回: OAuth consent (= browser で URL 開いて Google account 認可)
2 回目以降: ~/.config/orbit_wars_google_token.json で自動認証

出力: Colab で開く URL (= https://colab.research.google.com/drive/<file_id>)
    user は URL を click → Colab 起動 → Runtime > Change runtime type で A100 + High-RAM 選択
    → Runtime > Run all で 200k step training 開始
"""

from __future__ import annotations

import sys
from pathlib import Path

# Force unbuffered output for background-task visibility (= WSL2 background)
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    pass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

CLIENT_SECRET = (
    "/mnt/c/Users/yusuke kaya/Downloads/"
    "client_secret_757799584676-gmb117cjvjg22nhevvgc3mcihvk4pe7u.apps.googleusercontent.com.json"
)
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path.home() / ".config" / "orbit_wars_google_token.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO_ROOT / "notebooks" / "train_ppo_colab.ipynb"
WARM_START_ZIP = REPO_ROOT / "agents" / "proxy" / "ppo_v3_theta3.zip"
FOLDER_NAME = "orbit-wars"


def get_creds():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("\n=== OAuth consent required (= 初回のみ) ===")
            print(
                "ブラウザで URL が表示されます。 Google account で許可して redirect を待ってください。"
            )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            # Web-type OAuth client requires the EXACT redirect URI registered in
            # Google Cloud Console. Use fixed port 8080 and ask user to register
            # `http://localhost:8080/` in their OAuth client's Authorized redirect URIs.
            creds = flow.run_local_server(port=8080, open_browser=False)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"token saved: {TOKEN_PATH}")
    return creds


def find_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    resp = service.files().list(q=query, fields="files(id, name)").execute()
    items = resp.get("files", [])
    if items:
        print(f"folder '{name}' exists: {items[0]['id']}")
        return items[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    folder = service.files().create(body=body, fields="id").execute()
    print(f"folder '{name}' created: {folder['id']}")
    return folder["id"]


def upload_file(service, local_path: Path, parent_id: str, mime: str) -> dict:
    name = local_path.name
    # 既存ファイルがあれば update (= 同名複数 file 防止)
    query = f"name='{name}' and '{parent_id}' in parents and trashed=false"
    resp = service.files().list(q=query, fields="files(id, name)").execute()
    existing = resp.get("files", [])
    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)
    if existing:
        fid = existing[0]["id"]
        print(f"updating existing '{name}' ({fid})")
        result = (
            service.files()
            .update(fileId=fid, media_body=media, fields="id, webViewLink, name, size")
            .execute()
        )
    else:
        body = {"name": name, "parents": [parent_id]}
        print(f"uploading new '{name}' ({local_path.stat().st_size / 1024**2:.1f} MB) ...")
        result = (
            service.files()
            .create(
                body=body,
                media_body=media,
                fields="id, webViewLink, name, size",
            )
            .execute()
        )
    print(f"  done: id={result['id']} size={int(result.get('size', 0)) / 1024**2:.1f} MB")
    return result


def main() -> int:
    if not Path(CLIENT_SECRET).exists():
        print(f"ERROR: client_secret.json not found at {CLIENT_SECRET}", file=sys.stderr)
        return 1
    if not NOTEBOOK.exists():
        print(f"ERROR: notebook not found at {NOTEBOOK}", file=sys.stderr)
        return 1
    if not WARM_START_ZIP.exists():
        print(f"ERROR: warm-start zip not found at {WARM_START_ZIP}", file=sys.stderr)
        return 1

    try:
        creds = get_creds()
    except Exception as exc:
        print(f"OAuth failed: {exc}", file=sys.stderr)
        return 1

    service = build("drive", "v3", credentials=creds)

    try:
        folder_id = find_or_create_folder(service, FOLDER_NAME)
    except HttpError as exc:
        print(f"folder error: {exc}", file=sys.stderr)
        return 1

    print("\n=== Upload ppo_v3_theta3.zip (= 518 MB warm-start weight) ===")
    upload_file(service, WARM_START_ZIP, folder_id, "application/zip")

    print("\n=== Upload train_ppo_colab.ipynb ===")
    nb_result = upload_file(service, NOTEBOOK, folder_id, "application/x-ipynb+json")

    colab_url = f"https://colab.research.google.com/drive/{nb_result['id']}"
    drive_folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"\nDrive folder: {drive_folder_url}")
    print(f"\n★ Open in Colab: {colab_url}")
    print("\nNext steps (= user manual):")
    print("  1. Click the Colab URL above")
    print("  2. Runtime → Change runtime type → A100 GPU + High-RAM")
    print("  3. Runtime → Run all (= cells 1-4 が順次 execute、 200k step ≈ 4-6h)")
    print("  4. cell 4 完了後、 ppo_v4_theta4.zip が Drive `/MyDrive/orbit-wars/` に保存される")
    print(
        "  5. user が local に pull: `.venv/bin/python tools/drive_download.py` (= 別 script で実装)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
