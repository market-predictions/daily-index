#!/usr/bin/env python3
"""
Run the first live AEX input producers in sequence.

Outputs:
- output_aex/aex_primary_technical_snapshot.json
- output_aex/aex_cross_market_confirmation.json
- output_aex/aex_option_surface_snapshot.json
"""

from __future__ import annotations

import subprocess
import sys

SCRIPTS = [
    "build_aex_primary_technical_snapshot.py",
    "build_aex_cross_market_confirmation.py",
    "build_aex_option_surface_snapshot.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"RUNNING | {script}")
        completed = subprocess.run([sys.executable, script], check=False)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
    print("AEX_SNAPSHOT_SUITE_OK")


if __name__ == "__main__":
    main()
