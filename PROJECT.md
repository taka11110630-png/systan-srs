# Project: systan-srs — 周回特訓 PWA（仕様案C＋AIハイブリッド・旧帝国大学入試対応）

## Architecture
- **Frontend PWA Shell (`/home/antigravity/taka11110630-png/systan-srs/`)**: Single-file HTML/CSS/JS Progressive Web App (`index.html`, `manifest.json`, `icon.svg`, `sw.js`, `README.md`, `.gitignore`) hosted on GitHub Pages. Strict BYO (Bring Your Own data) architecture: `const EMBEDDED_BUNDLE = null;`, zero copyrighted vocabulary or generated JSON packs in the repository. User data is persisted locally in IndexedDB (`systan_srs_db`) + `localStorage` (`systan_srs_state_v2`), with optional Google Apps Script (GAS) auto-sync.
- **Private Generated Data Packs (`/home/antigravity/private/`, outside git repo)**:
  - `ext_hooks.json`: 220 audited Stage 1–2 3-axis memory hooks (`mp`, `co`, `et`, `kn`, `mn`, `cf`, `src`).
  - `ext_cloze.json`: 211 existing audited 4-choice cloze MCQs (`Q-0001..Q-0211`) + 72 new audited 旧帝国大学 (`level: "national"`) MCQs (`Q-0212..Q-0283`) = **283 total MCQs** (`common: 99`, `march: 78`, `national: 106`).
  - `systan_ai_pack.json`: Unified importable bundle (`version: "1.1"`, `hooks`: 220, `cloze`: 283) strictly matching `ext_hooks.json` and `ext_cloze.json`.
- **Opaque-Box E2E Test Suite (`/home/antigravity/taka11110630-png/systan-srs/tests/`)**: Python + Playwright headless Chrome (`/usr/bin/google-chrome`) 4-tier test suite (Tier 1 Feature Coverage, Tier 2 Boundary & Corner Cases, Tier 3 Cross-Feature Pairwise, Tier 4 Real-World Application Scenarios) using synthetic non-copyrighted fixtures in `tests/fixtures/` plus optional read-only validation against external `/tmp/drive_notes/systan_data.json` & `/home/antigravity/private/systan_ai_pack.json` when present.

## Code Layout
```
/home/antigravity/taka11110630-png/systan-srs/   (Public GitHub Pages Repo — BYO strictly enforced)
├── index.html          # Single-file PWA shell (Study, Loop Drill, Pattern SRS, Synonyms, Schedule, Explorer, Wiki)
├── sw.js               # Versioned Service Worker caching app shell (./, index.html, manifest.json, icon.svg)
├── manifest.json       # PWA manifest
├── icon.svg            # App icon
├── README.md           # Documentation (BYO policy, Loop Mode, 9+4 families, 旧帝大対応, AI integration)
├── .gitignore          # Ignores .agents/, private *.json packs, backups, TSVs, caches
├── PROJECT.md          # Project architecture, Feature Inventory, Milestones, Interface Contracts
├── TEST_INFRA.md       # E2E Testing Track architecture & coverage targets
├── TEST_READY.md       # Published by E2E Testing Track upon completion
└── tests/              # Opaque-box E2E test suite (synthetic fixtures only; zero copyrighted data)
    ├── run_e2e.py      # Unified test runner (`python3 tests/run_e2e.py [--tier 1|2|3|4|all]`)
    ├── fixtures/       # Minimal synthetic BYO bundle & AI pack fixtures
    └── ...             # Tier 1–4 test modules

/home/antigravity/private/                       (Private Data — NEVER committed to git)
├── ext_hooks.json      # 220 audited Stage 1–2 hooks (preserved intact)
├── ext_cloze.json      # 283 audited 4-choice cloze MCQs (Q-0001..Q-0283; 106 national)
└── systan_ai_pack.json # Integrated v1.1 pack (220 hooks + 283 cloze)
```

## Feature Inventory
Every Survey feature and verified bug is assigned a milestone (zero unassigned entries):

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Kioku-hakase 5 Common Non-Negotiable Rules | Enforce no answer-leak before user response, non-blaming tone, textbook evidence, learner agency, partial praise + 1 focus point across all AI prompts. | M2 | `spec_miner_survey_2` |
| F2 | Kioku-hakase Tab 1: AI Mistake Review (`mistake_review`) | Add Tab 1 prompt template: 6-category error classification + 8-item initial analysis + 1 hidden-answer similar Q + 5-item post-answer + canonical closing phrase. | M2 | `spec_miner_survey_2` |
| F3 | Kioku-hakase Tab 3: 10-Second AI Pretest (`pretest_chat`) | Align Tab 3 prompt to 3 Qs (10s/Q, choice + own-words mix), canonical closing phrase, and full 6 post-answer items, tuned for 旧帝大 focus. | M2 | `spec_miner_survey_2` |
| F4 | Kioku-hakase Tab 5: AI Solo Lecture (`teach_chat`) | Align Tab 5 prompt to full 7 initial items + 1 hidden-answer check Q + 4 post-answer items + full canonical closing phrase. | M2 | `spec_miner_survey_2` |
| F5 | Kioku-hakase Prompt Focus & Ephemeral Chat Policy | Keep exploratory AI prompts clean/focused (no Wiki pollution); align JSON expansion prompt (`json_pack`) to canonical `family` (9+4) & `level` (`common`/`march`/`national`) with 旧帝大 focus. | M2 | `spec_miner_survey_2` |
| F6 | 6-Category Mistake Tagging & Diagnostics | Support canonical 6 error tags (`knowledge_gap`, `misunderstanding`, `misreading`, `careless`, `confusion`, `order_error`) + backward compatibility with existing tags (`prep_pattern`, `confusable`, `slow`, `unlearned`), persisted across reloads and surfaced in weakness diagnostics & AI prompts. | M2 | `spec_miner_survey_2`, `explorer_survey_1` |
| F7 | Spaced Practice, SRS Ladder & Traffic Brake Fix (B8) | Maintain SRS ladder (`10m→1h→1d..120d`), Leech detection, and fix B8 (compute uncapped `totalDueCount` so `>100` red Traffic Brake is reachable). | M2 | `spec_miner_survey_2`, `explorer_survey_1` |
| F8 | Recall-Speed Measurement, Timer-OFF Fix (B1) & Visibility Pause (B5) | Measure recall time (ms) with `≤1.2s`/`≤2.0s`/`>2.0s` & custom thresholds; fix B1 (Timer-OFF allows Round 1 fast-clear/Round 2 skip without fake ms logs); fix B5 (`visibilitychange` timer pause/outlier cap + `pagehide` cloud flush). | M2 | `explorer_survey_1`, `spec_miner_survey_2` |
| F9 | 4-Step Fast Loop, Single-Focus, Interleaving & MCQ Double-Grade Fix (B2, B9, B10, B14, B15) | Fix B2 (MCQ pause/tab-switch/settings cannot double-grade); fix B9 (inflected VT regex, `survive in` guard, distractor/custom-word 4-choice guarantee); fix B10 (`ja2en` respects `autoAudioChk`); fix B14 (3-step hint step-lock); fix B15 (stage change resets range). | M2 | `explorer_survey_1`, `spec_miner_survey_2` |
| F10 | 3-Axis Memory Hooks (Dual Coding & Elaboration) | Render & edit `userHooks > extPack.hooks > w.hk` (`kn`, `mp`+`et`, `mn`, `co`, `cf`) hidden strictly until reveal; debounce input saves (B16). | M2 | `explorer_survey_1`, `spec_miner_survey_2` |
| F11 | StudySapuri 9 Verb Families + 4 旧帝大 Categories Alignment (B4) | Unify family IDs with bi-directional alias map (`transitive_trap`↔`vt_trap`, `intrans_prep`↔`vi_prep`, `svoo_vs_to`↔`svoo_to`, `svoc`↔`svoc_that`, `from_family`↔`from_prevent`, `with_family`↔`with_provide`, `of_family`↔`of_rob`, `as_family`↔`as_regard`, `vocab_confusable`, `inanimate_subject`, `stage5_polysemy`, `stage3_usage`, `composition_trap`↔`writing_trap`); include `VT_TRAP_MAP` words even when `w.pt` is empty and consult `extPack.cloze[].family`; fix `qType` attribution (`vocab_confusable`/`stage5_polysemy` → `"confusable"`). | M2 | `explorer_survey_1`, `spec_miner_survey_2`, `explorer_survey_3` |
| F12 | 旧帝国大学 Level Filter, AI Cloze Drill Target & Badges | Add `#loopLevelSel` (`all`/`common`/`march`/`national`), `#loopTargetSel` option `"ext_cloze"` (`🤖 AI実戦4択 / 旧帝大特訓`) so all imported `extPack.cloze` items (incl. Stage 3–5 & unmarked words) are directly drillable, plus level & family/category badges on MCQ cards. | M2 | `explorer_survey_1`, `spec_miner_survey_2`, `explorer_survey_3` |
| F13 | 72 New Audited `level: "national"` Cloze Questions & Pack v1.1 Integration | Generate, independently audit, and integrate 72 new `level: "national"` MCQs (`Q-0212..Q-0283`; 18 each of `inanimate_subject`, `stage5_polysemy`, `stage3_usage`, `composition_trap`) into `/home/antigravity/private/ext_cloze.json` (283 total, 106 `national`) and rebuild `/home/antigravity/private/systan_ai_pack.json` (v1.1: 220 hooks + 283 cloze). | M1 | `explorer_survey_3`, `spec_miner_survey_2` |
| F14 | Resilient AI JSON Pack Import/Export & Reload Safety (B6, B11, B12) | Fix B12 (extract JSON from prose-wrapped code fences, normalize Japanese level labels, guard empty/invalid `answer`, reset file input `value=""`, distinguish added vs updated); fix B6 (`BUNDLE.meta?.` optional chaining); fix B11 (clear `patPairs`/`loopState` on bundle reload). | M2 | `explorer_survey_1`, `explorer_survey_3` |
| F15 | BYO Privacy, `.gitignore`, Offline Service Worker (`sw.js`), XSS & UX Polish (B3, B7, B13, B17, B18) | Add `.gitignore` (protect BYO & `.agents/`); add & register `sw.js` for offline app-shell caching (B3); fix XSS/escaping in Study cloze, `missing_stage1`, `data-wid` (B7); guard keydown behind open modal (B13); compact mobile sticky topbar (B17); sync `README.md` (B18). | M2 | `explorer_survey_1`, `spec_miner_survey_2` |
| F16 | Existing Tabs Regression-Free + Opaque-Box E2E Suite & Tier 5 Hardening | Verify Study, Pattern SRS, 24 Synonym Groups, Schedule, Explorer, Wiki/GAS config, plus full 4-tier E2E test suite (`TEST_INFRA.md` + `TEST_READY.md`) and Tier 5 white-box adversarial hardening & whole-project Forensic Audit. | E2E Track + M3 | `explorer_survey_1`, `spec_miner_survey_2` |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Private 旧帝大 Cloze Pack (`Q-0212..Q-0283`) | Generate, audit (10-point linguistic + schema + referential rubric), and integrate 72 new `level: "national"` MCQs into `/home/antigravity/private/ext_cloze.json` (283 total) & `systan_ai_pack.json` (v1.1, 220 hooks + 283 cloze). | none | IN_PROGRESS (`c3c6ff8e0485197b6f620fad0b5f50d8`) |
| M2 | `systan-srs` PWA Hardening & 旧帝大 Upgrade | Implement F1–F12, F14–F15 in `/home/antigravity/taka11110630-png/systan-srs/` (`index.html`, `sw.js`, `.gitignore`, `README.md`), fixing B1–B18 and aligning schema/prompts/UI. | none | IN_PROGRESS (`0c6824883920897711d0e629a563cddd`) |
| E2E | E2E Testing Track (Opaque-Box Tiers 1–4) | Design & build `TEST_INFRA.md`, `tests/run_e2e.py`, synthetic `tests/fixtures/`, and 4-tier Playwright E2E tests covering F1–F16; publish `TEST_READY.md`. | none (runs parallel against Interface Contracts) | IN_PROGRESS (`e19e1dcdf818bccba3c543d7749ef515`) |
| M3 | Final Milestone (E2E Pass + Tier 5 Hardening + Whole-Project Audit) | Phase 1: Pass 100% of E2E Tiers 1–4 (incl. live integration check with private v1.1 pack). Phase 2: Tier 5 white-box adversarial hardening (`2 Challengers → Worker → Reviewer`). Final whole-project Forensic Audit + BYO git hygiene check. | M1, M2, E2E (`TEST_READY.md`) | PLANNED |

## Interface Contracts

### 1. Private JSON Pack ↔ `index.html` Importer (`ext_cloze.json` / `ext_hooks.json` / `systan_ai_pack.json`)
- **`systan_ai_pack.json` top-level**:
  ```json
  { "version": "1.1", "generated_at": "2026-11-27", "hooks": { "<wid>": { ... } }, "cloze": [ { ... } ] }
  ```
- **Cloze item (exact 11 keys, no extra/missing keys)**:
  - `id`: `"Q-0001"`..`"Q-0283"` (contiguous; `Q-0001..Q-0211` untouched, `Q-0212..Q-0283` new `level: "national"`)
  - `wid`: exact word ID in `systan_data.json` (never missing Stage 1 IDs)
  - `family`: canonical enum (13 values):
    - Core 9: `"transitive_trap"`, `"intrans_prep"`, `"svoo_vs_to"`, `"svoc"`, `"from_family"`, `"with_family"`, `"of_family"`, `"as_family"`, `"vocab_confusable"`
    - 旧帝大 4: `"inanimate_subject"`, `"stage5_polysemy"`, `"stage3_usage"`, `"composition_trap"`
  - `stem`: English sentence with single `(    )` blank (4 spaces inside parentheses)
  - `ja`: natural Japanese translation
  - `choices`: array of 4 distinct strings
  - `answer`: integer `0 | 1 | 2 | 3`
  - `why`: concise Japanese explanation of correct answer and key distractor failure
  - `trap`: single-line warning starting with `"⚠️ "`
  - `level`: `"common" | "march" | "national"`
  - `confusable_wids`: array of valid `wid` strings in `systan_data.json` (or `[]`)
- **Family Alias Normalization in `index.html`**:
  - `vt_trap` → `transitive_trap`, `vi_prep` → `intrans_prep`, `svoo_to` → `svoo_vs_to`, `svoc_that` → `svoc`, `from_prevent` → `from_family`, `with_provide` → `with_family`, `of_rob` → `of_family`, `as_regard` → `as_family`, `writing_trap` → `composition_trap`.
- **Level Normalization in `index.html` Importer**:
  - Strings matching `national` / `旧帝` / `国公立` / `難関国立` / `東大` / `京大` → `"national"`.
  - Strings matching `march` / `早慶` / `関関同立` / `私大` → `"march"`.
  - Strings matching `common` / `共通` / `標準` / `基本` → `"common"`.

### 2. `index.html` DOM / UI Contract (For M2 Implementation & E2E Opaque-Box Tests)
- **Existing preserved selectors**: `#onboardingScreen`, `#bundleFileInput`, `#tab-study`, `#tab-loop`, `#tab-pquiz`, `#tab-synonyms`, `#tab-schedule`, `#tab-explorer`, `#tab-wiki`, `#loopTargetSel`, `#loopModeSel`, `#loopFocusSel`, `#loopSizeSel`, `#loopTimerChk`, `#loopStartBtn`, `#loopVerbFamilySel`, `#loopStageSel`, `#loopAiPromptType`, `#loopAiPromptOut`, `#loopExtFileInput`, `#loopExtJsonInput`, `#loopExtImportBtn`, `#loopExtBadge`, `#loopThresholdBtn`, `#modalBackdrop`, `#autoAudioChk`, `#reloadBundleInput`.
- **New / standardized selectors in `#tab-loop`**:
  - `#loopTargetSel` options MUST include: `"today_weak"`, `"ext_cloze"` (AI実戦4択 / 旧帝大特訓), `"err_reason"`, `"verb_family"`, `"stage_batch"`.
  - `#loopLevelSel`: `<select id="loopLevelSel">` with values `"all"`, `"common"`, `"march"`, `"national"`.
  - `#loopVerbFamilySel`: includes `"all"` + all 13 canonical `family` values above.
  - `#loopAiPromptType`: includes `"json_pack"`, `"mistake_review"` (Tab 1 AIミス整理), `"pretest_chat"` (Tab 3 10秒AIプレテスト), `"teach_chat"` (Tab 5 AI一人講義).
  - MCQ card badges: `data-testid="mcq-level-badge"` and `data-testid="mcq-family-badge"`.
  - 6-category error tag buttons: `data-errtag="knowledge_gap"`, `"misunderstanding"`, `"misreading"`, `"careless"`, `"confusion"`, `"order_error"` (preserving display/migration compatibility with legacy tags `"prep_pattern"`, `"confusable"`, `"slow"`, `"unlearned"`).
- **Kioku-hakase Canonical Closing Phrases (exact strings)**:
  - Tab 1 (`mistake_review`): `まずは自分で解いてください。あなたの回答後に、同じミスが残っているかを確認します。`
  - Tab 3 (`pretest_chat`): `まずは正解を気にせず、10秒だけ考えて答えてください。あなたの回答後に、正解とズレを整理します。`
  - Tab 5 (`teach_chat`): `まずは自分の力で答えてください。あなたの回答後に、どの知識を使えばよかったかを整理します。`

### 3. E2E Runner ↔ Repo Contract
- Command: `python3 tests/run_e2e.py` (optional `--tier 1|2|3|4|all`, default `all`), exit code `0` on 100% pass.
- Serves `/home/antigravity/taka11110630-png/systan-srs` on `127.0.0.1:0` (ephemeral port) and uses Playwright + `/usr/bin/google-chrome` headless.
- Synthetic fixtures only inside `tests/fixtures/` (BYO safe); optional read-only external integration check using `/tmp/drive_notes/systan_data.json` and `/home/antigravity/private/systan_ai_pack.json` when those files exist on disk.
