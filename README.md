# systan-srs

Tablet-ready single-file PWA shell for spaced-repetition English vocabulary & grammar-pattern mastery aimed at **旧帝国大学入試（二次和訳・英作文・長文精読＋共通テスト）**.  
(**Bring-Your-Own private data JSON** — no copyrighted textbook/word data or generated packs are embedded in this repository.)

## Key Features
- **今日の復習 (`tab-study`)**: 自動間隔管理（SRS）・渋滞ブレーキ（100語超で自動警告）・2秒即答バー・3軸記憶フック・単語の型表示
- **🔁 周回特訓 (`tab-loop`)**: PWA高速周回 × 旧帝大・AI弱点特訓ハイブリッド
  - **🅰 おまかせ4周スパイラル**: `Round 1 ⚡10秒仕分け(英[型]→日)` → `Round 2 🧩3軸記憶フック工房` → `Round 3 🔄逆引きアウトプット(日→英＋動詞の型・交互配置)` → `Round 4 📝入試4択穴埋め`
  - **🅱 単発フォーカス演習**: 英(型)→日 / 日→英(型) / 入試4択道場 / フック工房を1形式だけでも即座に演習
  - **柔軟ターゲット＆旧帝大レベル絞り込み**:
    - 出題ターゲット：今日の要特訓 / **🤖 AI実戦4択・旧帝大特訓（`ext_cloze`）** / 誤答原因別（記憶博士6分類＋自動タグ） / スタサプ動詞の型＆旧帝大カテゴリ / Stage・50語バッチ・番号範囲指定
    - 入試レベル絞り込み：`全レベル` / `共通テスト (common)` / `MARCH・関関同立 (march)` / **`🏛 旧帝大・難関国立 (national)`**
    - 13系統カテゴリ：スタサプ動詞の型9系統（他動詞の罠・自動詞＋前置詞・SVOO vs to・SVOC・from・with・of・as・紛らわしい語彙）＋ **旧帝大4カテゴリ**（無生物主語×動詞の型・Stage 5 多義語文脈・Stage 3 難関語法・英作文減点トラップ）
  - **精密想起時間（Latency）計測＆分析**: 形式別基準秒カスタマイズ、バックグラウンドタブ時の一時停止＆外れ値キャップ、直近15件ログ記録、想起遅延語の控えめSRS間隔調整、「正解したけど遅かった危険語 TOP5」サマリー
  - **3軸記憶フック（答え先出し禁止＋段階ヒント）**: 🔗外来語・既知語 / 🌱語源分解 / 💡イメージ語呂を回答前非表示＆3段階ヒント化。自分用フックメモは最優先表示（`userHooks > AI拡張フック > 基本フック`）
  - **🤖 AI弱点特訓アシスタント**:
    - 記憶博士ルール準拠の4モードプロンプト出力（`json_pack` 3軸フック＋入試4択一括生成 / タブ1 AIミス整理 / タブ3 10秒プレテスト対話 / タブ5 AI一人講義）
    - AI生成JSON（`ext_hooks.json` / `ext_cloze.json` / 統合パック `systan_ai_pack.json`、前後説明文付きコードブロックも自動抽出）をファイル選択・ペースト両対応で IndexedDB へ永続マージ
- **📐 型⇔日本語 (`tab-pquiz`)**: 動詞・重要表現の型と日本語訳の双方向SRSトレーニング
- **🔗 意味グループ＆型 (`tab-synonyms`)**: 類義語のニュアンス比較と語法整理
- **間隔 & 50語 (`tab-schedule`) / 単語帳 (`tab-explorer`) / Wiki連携 (`tab-wiki`)**: 7日間予測・ヒートマップ・GAS Google Drive自動同期・LLM Wiki還元Markdown出力・Anki TSV出力
- **オフライン PWA 対応 (`sw.js`)**: Service Worker によるアプリシェルキャッシュでオフライン起動・復習に対応

## Running E2E Tests
Requires Python 3.12+, Playwright, and Chromium/Chrome:
```bash
python3 tests/run_e2e.py --tier all
```
All fixtures in `tests/fixtures/` are synthetic and non-copyrighted.
