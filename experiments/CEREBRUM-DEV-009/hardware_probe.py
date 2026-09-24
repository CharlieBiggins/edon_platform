#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path


def probe() -> dict:
    report = {
        "python": platform.python_version(),
        "cuda_available": False,
        "recommended_profile": "cpu-preflight-only",
    }
    try:
        import torch
        report.update({"torch": torch.__version__, "cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available()})
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram = props.total_memory / (1024 ** 3)
            if vram < 12:
                profile = "insufficient-for-default-4b-qlora"
            elif vram < 24:
                profile = "4b-eventnet-qlora-4096"
            elif vram < 48:
                profile = "4b-eventnet-repair-qlora-4096"
            else:
                profile = "4b-eventnet-repair-qlora-4096"
            report.update({
                "gpu": torch.cuda.get_device_name(0),
                "vram_gib": round(vram, 2),
                "bf16_supported": bool(torch.cuda.is_bf16_supported()),
                "recommended_profile": profile,
            })
    except ImportError:
        report["torch"] = None
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = probe()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())