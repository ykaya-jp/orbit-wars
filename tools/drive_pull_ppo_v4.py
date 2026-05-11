"""Pull ppo_v4_theta4.zip from Drive after Colab training completion, then build submit package.

Usage:
    .venv/bin/python tools/drive_pull_ppo_v4.py

Output:
- agents/proxy/ppo_v4_theta4.zip
- submissions/build_ppo_v4_theta4/main.py + ppo_inference.py + orbit_wars/ + zip
- submissions/ppo_v4_theta4.tar.gz (= Kaggle submit-ready)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN = Path.home() / ".config" / "orbit_wars_google_token.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
DST_ZIP = REPO_ROOT / "agents/proxy/ppo_v4_theta4.zip"
BUILD_DIR = REPO_ROOT / "submissions/build_ppo_v4_theta4"
TEMPLATE_BUILD = REPO_ROOT / "submissions/build_ppo_v3_theta3"
TARGZ = REPO_ROOT / "submissions/ppo_v4_theta4.tar.gz"


def get_creds():
    if not TOKEN.exists():
        raise SystemExit(f"ERROR: token not found at {TOKEN}. Run drive_upload_for_colab.py first.")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def main() -> int:
    creds = get_creds()
    service = build("drive", "v3", credentials=creds)

    print("=== 1. Pull ppo_v4_theta4.zip from Drive ===")
    resp = service.files().list(
        q="name='ppo_v4_theta4.zip' and trashed=false",
        fields="files(id, size, modifiedTime)",
    ).execute()
    items = resp["files"]
    if not items:
        # Fallback: search highest-step checkpoint in pool dir (= final pool member 同等 weight)
        print("ppo_v4_theta4.zip not found, falling back to highest pool checkpoint...")
        resp2 = service.files().list(
            q="name contains 'ckpt_step_' and trashed=false",
            fields="files(id, name, size, modifiedTime)",
            pageSize=100,
        ).execute()
        ckpts = resp2.get("files", [])
        if not ckpts:
            print("ERROR: no checkpoints found in Drive", file=sys.stderr)
            return 1
        # Pick max step
        def _step(n):
            try:
                return int(n.split("ckpt_step_")[1].split(".zip")[0])
            except Exception:
                return -1
        ckpts.sort(key=lambda c: _step(c["name"]), reverse=True)
        f = ckpts[0]
        print(f"  fallback: using {f['name']} (= step {_step(f['name'])})")
    else:
        f = items[0]
    fid = f["id"]
    size_mb = int(f.get("size", 0)) / 1024**2
    print(f"  found: id={fid} size={size_mb:.1f} MB modified={f['modifiedTime']}")

    import io

    req = service.files().get_media(fileId=fid)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req, chunksize=4 * 1024 * 1024)
    done = False
    while not done:
        progress, done = downloader.next_chunk()
        if progress is not None:
            print(f"    {int(progress.progress() * 100)}% downloaded")
    DST_ZIP.parent.mkdir(parents=True, exist_ok=True)
    DST_ZIP.write_bytes(buf.getvalue())
    print(f"  saved: {DST_ZIP} ({DST_ZIP.stat().st_size / 1024**2:.1f} MB)")

    print("\n=== 2. Build submission package ===")
    if not TEMPLATE_BUILD.exists():
        print(f"ERROR: template {TEMPLATE_BUILD} missing", file=sys.stderr)
        return 1
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    # Copy orbit_wars/ + ppo_inference.py from theta3 template
    shutil.copytree(TEMPLATE_BUILD / "orbit_wars", BUILD_DIR / "orbit_wars")
    shutil.copy(TEMPLATE_BUILD / "ppo_inference.py", BUILD_DIR / "ppo_inference.py")
    # main.py with v4 zip path
    main_py = BUILD_DIR / "main.py"
    main_py.write_text(
        '"""MaskablePPO θ.4 (= 200k step PFSP self-history training, Day 4 candidate)."""\n'
        "\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "_HERE = Path(__file__).resolve().parent\n"
        "if str(_HERE) not in sys.path:\n"
        "    sys.path.insert(0, str(_HERE))\n"
        "\n"
        "from ppo_inference import make_ppo_agent\n"
        "\n"
        '_WEIGHTS = _HERE / "ppo_v4_theta4.zip"\n'
        'agent = make_ppo_agent(_WEIGHTS, device="cpu", deterministic=True)\n'
    )
    # Copy zip into build dir
    shutil.copy(DST_ZIP, BUILD_DIR / "ppo_v4_theta4.zip")
    print(f"  build dir: {BUILD_DIR}")

    print("\n=== 3. Local smoke test (= vs starter 4P 1 ep) ===")
    smoke = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "tools._run_episode",
            "--left",
            str(BUILD_DIR / "main.py"),
            "--right",
            "starter",
            "--p3",
            "starter",
            "--p4",
            "starter",
            "--seed",
            "42",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if smoke.returncode != 0:
        print(f"  SMOKE FAILED (exit {smoke.returncode}):", file=sys.stderr)
        print(smoke.stderr[-2000:], file=sys.stderr)
        return 1
    last_line = smoke.stdout.strip().split("\n")[-1]
    print(f"  smoke output: {last_line[:200]}")

    print("\n=== 4. Tar.gz for Kaggle submit ===")
    if TARGZ.exists():
        TARGZ.unlink()
    subprocess.run(
        [
            "tar",
            "--exclude=__pycache__",
            "-czf",
            str(TARGZ),
            "main.py",
            "ppo_inference.py",
            "orbit_wars/",
            "ppo_v4_theta4.zip",
        ],
        cwd=str(BUILD_DIR),
        check=True,
    )
    print(f"  tar.gz: {TARGZ} ({TARGZ.stat().st_size / 1024**2:.1f} MB)")
    print("\nDONE — Day 4 submit slot 5 candidate ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
