"""Build lightweight sb3 zip from full PPO zip (= optimizer 削除 + FP16 cast)

sb3 zip 内訳 (= 例 ppo_v4_theta4.zip 495 MB):
  - data                       3.3 MB  (JSON metadata, keep)
  - policy.pth               164 MB  (policy weights, FP16 cast → 82 MB)
  - policy.optimizer.pth     328 MB  (DROP, 推論不要)
  - pytorch_variables.pth     <1 KB  (ent_coef tensor 等、 keep)
  - _stable_baselines3_version <1 KB  (keep)
  - system_info.txt           <1 KB  (keep)

Output sb3 zip:
  - data                       3.3 MB
  - policy.pth                ~82 MB  (FP16 cast、 sb3 load 互換)
  - pytorch_variables.pth     <1 KB
  - version + system_info     <1 KB
  Total: ~85 MB (= 100 MB cap 余裕クリア)

Compatible with existing ppo_inference.py weights-only load path
(= submissions/build_ppo_*/ppo_inference.py:42-46).
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import torch


def build_lightweight_zip(src: Path, dst: Path, fp16: bool = True) -> tuple[float, float]:
    """Read src sb3 zip → write dst with FP16 policy + no optimizer.

    Returns (src_mb, dst_mb).
    """
    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        data_bytes = zin.read("data")
        policy_bytes = zin.read("policy.pth")
        # optional members
        pv_bytes = zin.read("pytorch_variables.pth") if "pytorch_variables.pth" in names else None
        version_bytes = (
            zin.read("_stable_baselines3_version")
            if "_stable_baselines3_version" in names
            else b"2.8.0"
        )
        sysinfo_bytes = zin.read("system_info.txt") if "system_info.txt" in names else b""

    # Cast policy state_dict to FP16
    state_dict = torch.load(io.BytesIO(policy_bytes), map_location="cpu", weights_only=True)
    if fp16:
        state_dict = {
            k: v.half()
            if (
                hasattr(v, "is_floating_point")
                and v.is_floating_point()
                and v.dtype == torch.float32
            )
            else v
            for k, v in state_dict.items()
        }

    buf = io.BytesIO()
    torch.save(state_dict, buf)
    new_policy_bytes = buf.getvalue()

    # Write lightweight zip (= DROP optimizer.pth)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as zout:
        zout.writestr("data", data_bytes)
        zout.writestr("policy.pth", new_policy_bytes)
        if pv_bytes is not None:
            zout.writestr("pytorch_variables.pth", pv_bytes)
        zout.writestr("_stable_baselines3_version", version_bytes)
        zout.writestr("system_info.txt", sysinfo_bytes)

    src_mb = src.stat().st_size / 1024 / 1024
    dst_mb = dst.stat().st_size / 1024 / 1024
    return src_mb, dst_mb


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lightweight sb3 zip builder (= drop optimizer + FP16 cast)"
    )
    ap.add_argument("--src", required=True, type=Path, help="Source sb3 zip (= full)")
    ap.add_argument("--dst", required=True, type=Path, help="Output sb3 zip (= lightweight)")
    ap.add_argument("--fp32", action="store_true", help="Keep FP32 (= no half cast)")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"error: src not found: {args.src}", file=sys.stderr)
        return 1

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    src_mb, dst_mb = build_lightweight_zip(args.src, args.dst, fp16=not args.fp32)
    reduction = (1 - dst_mb / src_mb) * 100
    print(f"src: {args.src} ({src_mb:.1f} MB)")
    print(f"dst: {args.dst} ({dst_mb:.1f} MB) → {reduction:.1f}% reduction")
    if dst_mb > 100:
        print(f"WARNING: dst {dst_mb:.1f} MB > 100 MB cap", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
