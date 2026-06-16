#!/usr/bin/env python3
"""375px/768px overflow smoke test for static pages (Playwright required).

Usage:
  python3 -m http.server 8766   # in site root
  python3 tools/audit_responsive_overflow.py --base http://127.0.0.1:8766

See docs/responsive-layout.md §6.2.
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urljoin

DEFAULT_PATHS = [
    "/articles/index.html",
    "/articles/shiken-guide/index.html",
    "/terms/index.html",
    "/q/index.html",
    "/about.html",
]

OVERFLOW_JS = """
() => {
  const vw = document.documentElement.clientWidth;
  const sw = document.documentElement.scrollWidth;
  function inHScroll(el) {
    let p = el;
    while (p) {
      const cs = getComputedStyle(p);
      if ((cs.overflowX === 'auto' || cs.overflowX === 'scroll') && p.scrollWidth > p.clientWidth + 1) return true;
      if (p.classList && (p.classList.contains('site-footer-scroll') || p.classList.contains('topnav-links'))) return true;
      p = p.parentElement;
    }
    return false;
  }
  let bad = 0;
  const samples = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    if (r.right > vw + 2 && !inHScroll(el)) {
      bad++;
      if (samples.length < 3) {
        samples.push({tag: el.tagName, cls: String(el.className||'').slice(0, 60), right: Math.round(r.right)});
      }
    }
  });
  return {path: location.pathname, vw, sw, bodyOverflow: sw > vw + 1, bad, samples};
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8766", help="Site origin (local server)")
    parser.add_argument("--width", type=int, action="append", default=[375, 768])
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("error: pip install playwright && python3 -m playwright install chromium", file=sys.stderr)
        return 2

    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width in args.width:
            page = browser.new_page(viewport={"width": width, "height": max(812, width)})
            print(f"=== {width}px ===")
            for rel in args.paths:
                url = urljoin(args.base.rstrip("/") + "/", rel.lstrip("/"))
                page.goto(url, wait_until="networkidle", timeout=30000)
                r = page.evaluate(OVERFLOW_JS)
                ok = not r["bodyOverflow"] and r["bad"] == 0
                if not ok:
                    failures += 1
                status = "ok" if ok else "FAIL"
                print(f"  [{status}] {r['path']} sw={r['sw']} offenders={r['bad']}")
                for s in r.get("samples") or []:
                    print(f"        {s['tag']}.{s['cls'][:50]} right={s['right']}")
        browser.close()

    if failures:
        print(f"audit_responsive_overflow: {failures} failure(s)", file=sys.stderr)
        return 1
    print("audit_responsive_overflow: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
