# fp-master — サイト運用メモ

## 本番

| 項目 | 値 |
|------|-----|
| サイトID | `fp-master` |
| ブランド名 | FPマスター |
| 試験名 | ファイナンシャル・プランナー試験（FP2級・FP3級） |
| 公開 URL | `https://fp-master.jp` |
| Git | https://github.com/takkenshiken2026-sudo/fp-master |
| ローカル | `/Users/otedaiki/Projects/fp-master` |

## デプロイ

| 項目 | 値 |
|------|-----|
| 方式 | GitHub Actions（[DEPLOY.md](../../docs/DEPLOY.md) 標準） |
| ワークフロー | `.github/workflows/deploy-pages.yml` |
| トリガー | `main` push / `workflow_dispatch` |
| GitHub 設定 | Settings → Pages → **Source: GitHub Actions** |
| ビルド | `python3 tools/build_all.py` → `public_site/` |

## 新規サイト初回セットアップ

2026-06-07: `exam-site-shell` からコピーして初期化。

```bash
cd ~/Projects/fp-master
python3 tools/generate_brand_assets.py
python3 tools/apply_site_config.py
python3 tools/build_all.py
python3 tools/validate_site_integration.py
```

## 同期（テンプレ root で実行）

```bash
cd ~/Projects/exam-site-shell
python3 tools/check_template_drift.py --target ~/Projects/fp-master
python3 tools/sync_from_template.py --target ~/Projects/fp-master --dry-run
python3 tools/sync_from_template.py --target ~/Projects/fp-master --build
```

## サイト固有メモ

- FP技能検定の6分野（ライフプランニング・リスク管理・金融資産運用・タックスプランニング・不動産・相続・事業承継）を `site-config.json` の `fields` に設定済み
- `extendedCorrectAnswers: true`（三答択・正誤式対応）
- FP3級過去問取り込み: `python3 tools/import_fp3_past_questions.py` → `data/source/fp3/`
  - 学科正誤式90 → `ichimon_questions.csv`
  - 学科三答択90 + 実技60 → `past_questions.csv`（年度内 問1-30 学科 / 問31-50 実技）
- 実技図表: `preamble` にテキスト、`diagram_manifest.json` で HTML 再現予定（6件 needs_svg）

## 最終同期

- 日付: 2026-06-07
- テンプレ commit: （初回コピー時点）
- 備考: 新規サイト立ち上げ
