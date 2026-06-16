#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演習画面「中断」→ 解答済み分の結果画面を表示（interruptQuiz）。

index.html は site-only のため template_sync では届かない。本パッチを各本番で実行する。

  python3 tools/patch_quiz_interrupt.py
  python3 tools/patch_quiz_interrupt.py --root ~/Projects/eisei1shu-master
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INTERRUPT_FN = """function interruptQuiz(){
  if(quizState.scoreReplayMode){
    backToScoreFromReplay();
    return;
  }
  if(timer) clearInterval(timer);
  timer=null;
  showNextBtn(false,null);
  const res=quizState.sessionResults||[];
  if(!res.length){
    if(!confirm('まだ1問も解答していません。中断してよいですか？')) return;
    gotoPage('quiz-start');
    return;
  }
  quizState.scoreReplayMode=false;
  quizState.fromReview=false;
  showScore();
}

"""

_BTN_OLD = re.compile(
    r'<button class="btn-ghost" onclick="gotoPage\(\'quiz-start\'\)">中断</button>'
)
_BTN_NEW = '<button class="btn-ghost" onclick="interruptQuiz()">中断</button>'

_FN_MARKER = "function interruptQuiz()"


def patch_index_html(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []

    if _FN_MARKER not in text:
        anchor = "function showScore(){"
        if anchor not in text:
            raise ValueError("function showScore(){ not found — index.html SPA が想定外です")
        text = text.replace(anchor, INTERRUPT_FN + anchor, 1)
        changes.append("added interruptQuiz()")

    if _BTN_OLD.search(text):
        text = _BTN_OLD.sub(_BTN_NEW, text, count=1)
        changes.append("interrupt button → interruptQuiz()")
    elif _BTN_NEW in text and _FN_MARKER in text:
        if not changes:
            changes.append("already patched")
    else:
        raise ValueError("中断ボタンの HTML が見つかりません（btn-ghost + 中断）")

    return text, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="サイト root（既定: テンプレ自身）",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    index_path = args.root.resolve() / "index.html"
    if not index_path.is_file():
        print(f"error: {index_path} がありません", file=sys.stderr)
        return 1

    original = index_path.read_text(encoding="utf-8")
    try:
        patched, changes = patch_index_html(original)
    except ValueError as exc:
        print(f"error: {index_path}: {exc}", file=sys.stderr)
        return 1

    if changes == ["already patched"]:
        print(f"ok (no change): {index_path}")
        return 0

    if args.dry_run:
        print(f"dry-run: {index_path}: {', '.join(changes)}")
        return 0

    index_path.write_text(patched, encoding="utf-8")
    print(f"patched {index_path}: {', '.join(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
