#!/usr/bin/env bash
# 汎用解説テンプレ除去 + SPA fork 修正を全本番サイトへ展開
set -uo pipefail

SHELL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
TEMPLATE="$SHELL_ROOT"

SITES=(
  mentalhealth-master
  takken-master
  kikenbutsu-master
  eisei1shu-master
  chintaikanrishi-master
  eisei2shu-master
  kangyou-master
  mankan-master
  unkan-master
  fp-master
)

COMMIT_MSG='fix: 汎用解説テンプレ除去とSPAの他試験fork残骸を修正

誤答肢解説の自動生成テンプレを廃止し、正答との対比ベースに差し替え。トップSPAの分野ツールチップ・法令ハイライト・未使用メッセージも各試験向けに統一する。'

for site in "${SITES[@]}"; do
  target="$HOME/Projects/$site"
  if [[ ! -f "$target/site-config.json" ]]; then
    echo "SKIP $site (no site-config.json)"
    continue
  fi
  echo "========== $site =========="
  "$PY" "$TEMPLATE/tools/sync_from_template.py" --target "$target"
  (
    cd "$target"
    "$PY" tools/apply_site_config.py
    if ! "$PY" tools/build_all.py; then
      echo "BUILD_FAILED $site" >&2
      exit 1
    fi
    if [[ -n "$(git status --porcelain)" ]]; then
      git add -A
      git commit -m "$COMMIT_MSG"
      git push origin HEAD
      echo "PUSHED $site"
    else
      echo "NO_CHANGES $site"
    fi
  ) || echo "SKIP_AFTER_FAIL $site"
done
echo "ROLLOUT_DONE"
