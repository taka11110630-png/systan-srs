# GAS CLI (`@google/clasp`) 運用ガイド

このディレクトリ (`gas/`) は、Google公式 CLI **`@google/clasp`** を使って既存の Google Apps Script (GAS) プロジェクトをローカル／CLI から自動操作（取得・反映・再デプロイ・ログ確認）するためのワークスペースです。

## 構成

- `gas/src/` — GAS のソースコード（`*.js` / `*.gs` / `appsscript.json`）格納先
- `gas/.claspignore` — `src/` 配下の GAS ファイルのみを push 対象にする設定
- `gas/.clasp.json.example` — `.clasp.json` のテンプレート（実ファイルは `.gitignore` 済み）
- `gas/.env.example` — 既存ウェブアプリ再デプロイ用 `GAS_DEPLOYMENT_ID` のテンプレート（`.env` は `.gitignore` 済み）
- `gas/scripts/setup.mjs` — 既存 GAS のスクリプト ID を `.clasp.json` に紐づけるヘルパー
- `gas/scripts/redeploy.mjs` — `push` → 既存デプロイ ID を維持したまま再デプロイするヘルパー

---

## 初回セットアップ（既存 GAS プロジェクト連携）

### 1. Google Apps Script API を有効化（初回のみ）
Google アカウントで以下を開き、**「Google Apps Script API」をオン** にします。  
https://script.google.com/home/usersettings

### 2. Google アカウントへログイン
`gas/` ディレクトリで実行します。

- **ローカル PC（ブラウザが開ける環境）**:
  ```bash
  cd gas
  npm run login
  ```
- **リモート環境 / ブラウザがない環境**:
  ```bash
  cd gas
  npm run login:remote
  ```
  表示された URL をブラウザで開いて認証し、返ってきた認証コードを貼り付けます。

ログイン確認:
```bash
npm run whoami
```

### 3. 既存 GAS プロジェクトのスクリプト ID を連携
GAS エディタの **プロジェクトの設定（歯車アイコン）→ スクリプト ID** をコピーして実行します。

```bash
npm run setup -- <YOUR_SCRIPT_ID> --pull
```

これで `gas/.clasp.json` が作成され、既存 GAS のコードが `gas/src/` にダウンロードされます。

---

## 日常の自動操作コマンド

| コマンド | 動作 |
|---|---|
| `npm run status` | push 対象ファイル一覧を確認 |
| `npm run pull` | リモート GAS の最新コードを `gas/src/` に取得 |
| `npm run push` | `gas/src/` の変更をリモート GAS へ反映 |
| `npm run deployments` | 既存のデプロイ ID 一覧を表示 |
| `npm run redeploy -- <DEPLOYMENT_ID> "変更メモ"` | `push` 後、**ウェブアプリ URL を変えずに**本番デプロイを更新 |
| `npm run versions` | バージョン履歴を表示 |
| `npm run logs` | 実行ログを表示 |

### ウェブアプリ URL を変えずに再デプロイするコツ
`systan-srs` の自動同期設定では GAS のウェブアプリ URL を固定で使うため、毎回 `clasp deploy`（新規デプロイ）するのではなく **既存のデプロイ ID を指定して更新** します。

1. `npm run deployments` で本番用の `AKfycb...`（`@HEAD` ではない方）を確認
2. `gas/.env.example` をコピーして `gas/.env` を作成し、`GAS_DEPLOYMENT_ID=AKfycb...` を記入
3. 以降は `npm run redeploy` だけで `push` → 本番反映まで一括実行できます

---

## セキュリティ上の注意

- `.clasp.json`（個人スクリプト ID）、`.clasprc.json`（OAuth 認証トークン）、`.env`（デプロイ ID 等）はルート `.gitignore` で除外されています。絶対に Git へコミットしないでください。
- `SYNC_KEY` などの合言葉や秘密情報はコードに直書きせず、GAS の **スクリプト プロパティ (`PropertiesService.getScriptProperties()`)** に保存する運用を推奨します。
