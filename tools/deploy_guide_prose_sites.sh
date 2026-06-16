#!/usr/bin/env bash
# ガイド prose 修復済み CSV をビルドし、本番リポジトリへ push する。
set -euo pipefail
SHELL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECTS="${HOME}/Projects"
SITES=(
  chintaikanrishi-master
  eisei1shu-master
  eisei2shu-master
  kangyou-master
  kikenbutsu-master
  mankan-master
  mentalhealth-master
  takken-master
  unkan-master
  boiler-master.jp
)

SYNC_TOOLS=(
  internal_links.py
  build_past_question_pages.py
  build_glossary_pages.py
  build_practice_ichimon_pages.py
  build_article_pages.py
  fix_guide_prose_quality.py
  fix_guide_coherence_gaps.py
  fix_guide_week_template_prose.py
  guide_prose_patterns.py
  guide_coherence_rules.py
  guide_slug_prose.py
  guide_field_prose.py
  strip_generic_guide_padding.py
  fix_guide_duplicate_bodies.py
  guide_content_shared.py
)

ok=()
fail=()

for name in "${SITES[@]}"; do
  site="${PROJECTS}/${name}"
  [ -d "${site}/data" ] || { echo "skip missing ${name}"; continue; }
  echo "======== ${name} ========"
  mkdir -p "${site}/tools"
  for f in "${SYNC_TOOLS[@]}"; do
    cp "${SHELL_ROOT}/tools/${f}" "${site}/tools/${f}"
  done
  if [ "${name}" = "mankan-master" ] && [ -f "${site}/data/glossary_terms.csv" ]; then
    (cd "${site}" && git checkout -- data/glossary_terms.csv 2>/dev/null || true)
  fi
  # テンプレ PYTHONPATH は使わない（用語 auto-link が別サイト CSV を読むため）
  if ! (cd "${site}" && python3 tools/build_all.py); then
    fail+=("${name}")
    continue
  fi
  ok+=("${name}")
done

echo "BUILD OK: ${ok[*]:-none}"
echo "BUILD FAIL: ${fail[*]:-none}"
[ "${#fail[@]}" -eq 0 ]
