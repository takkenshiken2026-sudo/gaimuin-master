#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全本番クローンへ GA4 修正済み apply_site_config を反映する。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1]
SITES = [
    Path.home() / "Projects" / "takken-master",
    Path.home() / "Projects" / "mentalhealth-master",
    Path.home() / "Projects" / "kikenbutsu-master",
    Path.home() / "Projects" / "eisei1shu-master",
    Path.home() / "Projects" / "chintaikanrishi-master",
    Path.home() / "Projects" / "eisei2shu-master",
    Path.home() / "Projects" / "kangyou-master",
    Path.home() / "Projects" / "mankan-master",
    Path.home() / "Projects" / "unkan-master",
    Path.home() / "Projects" / "boiler-master.jp",
    Path.home() / "Projects" / "fp-master",
]

SYNC_TOOLS = (
    "apply_site_config.py",
    "validate_site_integration.py",
)


def main() -> int:
    py = sys.executable
    errors = 0
    for site in SITES:
        if not site.is_dir():
            print(f"skip (missing): {site}")
            continue
        print(f"\n=== {site.name} ===")
        for name in SYNC_TOOLS:
            src = TEMPLATE / "tools" / name
            dst = site / "tools" / name
            if src.is_file():
                shutil.copy2(src, dst)
        # site-analytics.js はテンプレから同期（fp 等で欠落している場合に備える）
        sa_src = TEMPLATE / "site-analytics.js"
        sa_dst = site / "site-analytics.js"
        if sa_src.is_file():
            shutil.copy2(sa_src, sa_dst)

        proc = subprocess.run(
            [py, "tools/apply_site_config.py"],
            cwd=site,
            capture_output=True,
            text=True,
        )
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.returncode != 0:
            print(proc.stderr.strip(), file=sys.stderr)
            errors += 1
            continue

        vproc = subprocess.run(
            [py, "tools/validate_site_integration.py"],
            cwd=site,
            capture_output=True,
            text=True,
        )
        if vproc.returncode == 0:
            print("validate_site_integration: OK")
        else:
            print(vproc.stderr.strip() or vproc.stdout.strip(), file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n{errors} site(s) had errors", file=sys.stderr)
        return 1
    print("\nAll sites updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
