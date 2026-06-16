#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全サイト試験ガイドの1本ずつ目視確認キュー。

使い方:
  # 初回: キューCSVを生成（または更新）
  python3 tools/guide_review_queue.py --init

  # 次に確認する1本
  python3 tools/guide_review_queue.py --next

  # 確認済みにする
  python3 tools/guide_review_queue.py --mark-reviewed --site eisei2shu-master --slug kanto-center --notes "禁止句修正要"

  # 進捗サマリー
  python3 tools/guide_review_queue.py --summary

確認チェックリスト: docs/guide-expert-rewrite-program.md §12
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_guide_rewrite_inventory import DEFAULT_SITES, PROSE_COLS, reader_text  # noqa: E402
from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_prose_patterns import scan_prose_text  # noqa: E402
from tools.guide_rewrite_quality import prose_quality_status  # noqa: E402

TRACKER = ROOT / "data" / "guide_review_tracker.csv"
QUEUE_FIELDS = (
    "seq",
    "site_id",
    "brand_short",
    "slug",
    "genre",
    "title",
    "article_url",
    "machine_status",
    "expert_label",
    "audit_ok",
    "audit_patterns",
    "review_priority",
    "reviewed",
    "reviewed_at",
    "review_notes",
)

# guide-expert-rewrite-program.md §7.2 の推奨順 + 残タスク優先
SITE_ORDER = {
    "eisei2shu-master": 0,
    "eisei1shu-master": 1,
    "boiler-master.jp": 2,
    "takken-master": 3,
    "mankan-master": 4,
    "chintaikanrishi-master": 5,
    "kikenbutsu-master": 6,
    "kangyou-master": 7,
    "unkan-master": 8,
    "mentalhealth-master": 9,
}

BRAND_SHORT = {
    "takken-master": "宅建",
    "mankan-master": "マン管",
    "chintaikanrishi-master": "賃管",
    "kikenbutsu-master": "乙4",
    "kangyou-master": "管業",
    "unkan-master": "運管",
    "mentalhealth-master": "メンヘル",
    "eisei1shu-master": "一衛",
    "eisei2shu-master": "二衛",
    "boiler-master.jp": "ボイラー",
}

CHECKLIST = (
    "表が読みやすい（枠・見出し色）",
    "数字に「要項で再確認」がある",
    "他記事とリードが似ていない",
    "FAQ がこの slug だけの内容",
    "関連リンク先が存在し、ラベルが自然",
    "当該試験の分野数・機関名が正しい",
    "演習・用語への導線が具体的",
)


def site_origin(site_root: Path) -> str:
    cfg = site_root / "site-config.json"
    if cfg.is_file():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        origin = norm(data.get("siteOrigin"))
        if origin:
            return origin.rstrip("/")
    name = site_root.name
    if name.endswith(".jp"):
        return f"https://{name}"
    return f"https://{name.replace('-master', '-master')}.jp"


def site_slug_audit_map(site_root: Path) -> dict[str, list[str]]:
    """サイト内 published slug → audit パターン一覧。"""
    csv_path = site_root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        return {}
    try:
        from tools.fix_guide_duplicate_bodies import load_site_lib

        lib = load_site_lib(site_root)
        exam, exam_short = getattr(lib, "EXAM", ""), getattr(lib, "EXAM_SHORT", "")
    except Exception:
        exam, exam_short = "", ""
    slug_hits: dict[str, list[str]] = {}
    for row in csv.DictReader(csv_path.open(encoding="utf-8-sig")):
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        for col in PROSE_COLS:
            raw = norm(row.get(col))
            if not raw:
                continue
            text = reader_text(row, col, slug)
            for hit in scan_prose_text(text, column=col, exam=exam, exam_short=exam_short):
                if hit.pattern not in slug_hits.setdefault(slug, []):
                    slug_hits[slug].append(hit.pattern)
    return slug_hits


def build_queue_rows(sites_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for site_id in DEFAULT_SITES:
        site_root = sites_root / site_id
        csv_path = site_root / "data" / "guide_articles.csv"
        if not csv_path.is_file():
            continue
        origin = site_origin(site_root)
        slug_audit = site_slug_audit_map(site_root)
        for row in csv.DictReader(csv_path.open(encoding="utf-8-sig")):
            if not is_published_guide(row):
                continue
            slug = norm(row.get("slug"))
            parts = [reader_text(row, c, slug) for c in PROSE_COLS]
            combined = "\n".join(p for p in parts if p)
            machine = prose_quality_status(row, combined)
            rn = norm(row.get("revision_note"))
            expert = "yes" if "編集合格" in rn else "no"
            patterns = slug_audit.get(slug, [])
            audit_ok = "no" if patterns else "yes"
            priority = "A" if audit_ok == "no" or machine == "needs_rewrite" else "B"
            rows.append(
                {
                    "site_id": site_id,
                    "brand_short": BRAND_SHORT.get(site_id, site_id),
                    "slug": slug,
                    "genre": norm(row.get("genre")),
                    "title": norm(row.get("title")),
                    "article_url": f"{origin}/articles/{slug}/",
                    "machine_status": machine,
                    "expert_label": expert,
                    "audit_ok": audit_ok,
                    "audit_patterns": ";".join(patterns),
                    "review_priority": priority,
                    "reviewed": "no",
                    "reviewed_at": "",
                    "review_notes": "",
                }
            )

    def sort_key(r: dict[str, str]) -> tuple:
        pri = 0 if r["review_priority"] == "A" else 1
        site = SITE_ORDER.get(r["site_id"], 99)
        return (pri, site, r["genre"], r["slug"])

    rows.sort(key=sort_key)
    for i, r in enumerate(rows, start=1):
        r["seq"] = str(i)
    return rows


def load_tracker() -> dict[tuple[str, str], dict[str, str]]:
    if not TRACKER.is_file():
        return {}
    out: dict[tuple[str, str], dict[str, str]] = {}
    with TRACKER.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (norm(row.get("site_id")), norm(row.get("slug")))
            if key[0] and key[1]:
                out[key] = row
    return out


def merge_tracker(queue: list[dict[str, str]], tracker: dict[tuple[str, str], dict[str, str]]) -> None:
    for row in queue:
        key = (row["site_id"], row["slug"])
        prev = tracker.get(key)
        if prev:
            row["reviewed"] = prev.get("reviewed") or "no"
            row["reviewed_at"] = prev.get("reviewed_at") or ""
            row["review_notes"] = prev.get("review_notes") or ""


def write_tracker(rows: list[dict[str, str]]) -> None:
    TRACKER.parent.mkdir(parents=True, exist_ok=True)
    with TRACKER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=QUEUE_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def print_checklist() -> None:
    print("目視チェックリスト（§12）:")
    for i, item in enumerate(CHECKLIST, 1):
        print(f"  {i}. {item}")


def print_article(row: dict[str, str], *, total: int, done: int) -> None:
    print_checklist()
    print()
    print(f"進捗: {done}/{total} 確認済み（残り {total - done}）")
    print(f"順番: #{row['seq']}  [{row['review_priority']}] {row['brand_short']} / {row['genre']}")
    print(f"slug: {row['slug']}")
    print(f"title: {row['title']}")
    print(f"機械: status={row['machine_status']}  編集合格={row['expert_label']}  audit={row['audit_ok']}")
    if row["audit_patterns"]:
        print(f"audit_patterns: {row['audit_patterns']}")
    print(f"URL: {row['article_url']}")
    print()
    print("確認後:")
    print(
        f"  python3 tools/guide_review_queue.py --mark-reviewed "
        f"--site {row['site_id']} --slug {row['slug']} --notes \"OK\""
    )


def cmd_init(sites_root: Path) -> int:
    tracker = load_tracker()
    queue = build_queue_rows(sites_root)
    merge_tracker(queue, tracker)
    write_tracker(queue)
    done = sum(1 for r in queue if r["reviewed"] == "yes")
    pri_a = sum(1 for r in queue if r["review_priority"] == "A")
    print(f"wrote {TRACKER} ({len(queue)} articles, {done} reviewed, {pri_a} priority-A)")
    return 0


def cmd_summary() -> int:
    if not TRACKER.is_file():
        print(f"missing {TRACKER} — run --init first", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(TRACKER.open(encoding="utf-8-sig")))
    total = len(rows)
    done = sum(1 for r in rows if r.get("reviewed") == "yes")
    by_site: Counter[str] = Counter()
    by_site_done: Counter[str] = Counter()
    for r in rows:
        by_site[r["site_id"]] += 1
        if r.get("reviewed") == "yes":
            by_site_done[r["site_id"]] += 1
    print(f"全体: {done}/{total} 確認済み（{100 * done // total if total else 0}%）")
    print()
    for site_id in sorted(by_site, key=lambda s: SITE_ORDER.get(s, 99)):
        t = by_site[site_id]
        d = by_site_done[site_id]
        short = BRAND_SHORT.get(site_id, site_id)
        bar = "✓" if d == t else "…"
        print(f"  {bar} {short:<6} {d:3}/{t:3}")
    pending_a = [r for r in rows if r.get("reviewed") != "yes" and r.get("review_priority") == "A"]
    if pending_a:
        print(f"\n優先A 未確認: {len(pending_a)} 本（audit FAIL / needs_rewrite）")
    return 0


def cmd_next(*, site_filter: str | None) -> int:
    if not TRACKER.is_file():
        print(f"missing {TRACKER} — run --init first", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(TRACKER.open(encoding="utf-8-sig")))
    total = len(rows)
    done = sum(1 for r in rows if r.get("reviewed") == "yes")
    pending = [
        r
        for r in rows
        if r.get("reviewed") != "yes"
        and (not site_filter or r.get("site_id") == site_filter)
    ]
    if not pending:
        print("未確認の記事はありません。")
        return 0
    print_article(pending[0], total=total, done=done)
    return 0


def cmd_mark(site_id: str, slug: str, notes: str, *, ok: bool) -> int:
    if not TRACKER.is_file():
        print(f"missing {TRACKER} — run --init first", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(TRACKER.open(encoding="utf-8-sig")))
    found = False
    today = date.today().isoformat()
    for row in rows:
        if row.get("site_id") == site_id and row.get("slug") == slug:
            row["reviewed"] = "yes" if ok else "no"
            row["reviewed_at"] = today if ok else ""
            if notes:
                row["review_notes"] = notes
            found = True
            break
    if not found:
        print(f"not found: {site_id} / {slug}", file=sys.stderr)
        return 1
    write_tracker(rows)
    status = "確認済み" if ok else "未確認に戻しました"
    print(f"{status}: {site_id} / {slug}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="全サイトガイド1本ずつ目視確認キュー")
    ap.add_argument("--sites-root", type=Path, default=Path.home() / "Projects")
    ap.add_argument("--init", action="store_true", help="キューCSVを生成・更新")
    ap.add_argument("--summary", action="store_true", help="進捗サマリー")
    ap.add_argument("--next", action="store_true", help="次に確認する1本を表示")
    ap.add_argument("--site", help="--next / --mark-reviewed 用サイトID")
    ap.add_argument("--slug", help="--mark-reviewed 用 slug")
    ap.add_argument("--notes", default="", help="確認メモ")
    ap.add_argument("--mark-reviewed", action="store_true", help="確認済みにする")
    ap.add_argument("--unmark", action="store_true", help="未確認に戻す")
    args = ap.parse_args()

    if args.init:
        return cmd_init(args.sites_root)
    if args.summary:
        return cmd_summary()
    if args.next:
        return cmd_next(site_filter=args.site)
    if args.mark_reviewed or args.unmark:
        if not args.site or not args.slug:
            ap.error("--mark-reviewed には --site と --slug が必要です")
        return cmd_mark(args.site, args.slug, args.notes, ok=not args.unmark)

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
