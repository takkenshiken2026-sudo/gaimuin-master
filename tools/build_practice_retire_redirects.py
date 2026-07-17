#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ドメイン切替前に公開・インデックスされた練習問題ページへ noindex リダイレクトを書く。

現テンプレートには実体が無い q/practice/p*/ の URL（GSC で表示のある旧 URL）に対し、
演習ハブ q/practice/index.html への noindex リダイレクト HTML を生成し、404 を解消して
検索評価と流入を生きたハブへ集約する。build_practice_ichimon_pages.py は q/practice/ を
毎回作り直すため、そのあとに実行する（build_all.py の順序参照）。実体のある生成ページ
（practice_questions.csv 由来の p001/p002 等）は上書きしない。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED_JSON = ROOT / "data" / "practice_retired.json"
PRACTICE_DIR = ROOT / "q" / "practice"

REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<title>ページ移動中…</title>
<script>location.replace({url_js});</script>
</head>
<body>
<p>演習ページへ移動します。<a href="{url}">こちら</a></p>
</body>
</html>
"""


def load_ids() -> tuple[list[str], str]:
    if not RETIRED_JSON.is_file():
        return [], "../index.html"
    data = json.loads(RETIRED_JSON.read_text(encoding="utf-8"))
    ids = [str(i).strip() for i in (data.get("ids") or []) if str(i).strip()]
    target = str(data.get("target_rel") or "../index.html").strip()
    return ids, target


def main() -> int:
    ids, target_rel = load_ids()
    if not ids:
        print("build_practice_retire_redirects: no ids, nothing to do")
        return 0

    written = 0
    skipped = 0
    for pid in ids:
        out_dir = PRACTICE_DIR / pid
        index = out_dir / "index.html"
        # 実体のある生成ページは上書きしない
        if index.is_file():
            skipped += 1
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        index.write_text(
            REDIRECT_HTML.format(url=target_rel, url_js=repr(target_rel)),
            encoding="utf-8",
        )
        written += 1

    print(
        f"Wrote {written} practice retire redirect(s) under q/practice/"
        f" (skipped {skipped} existing page(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
