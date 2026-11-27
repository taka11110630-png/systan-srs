# TEST_INFRA.md — `systan-srs` Opaque-Box E2E Testing Track (Tiers 1–4)

## 1. Test Philosophy & Hard Constraints

1. **Opaque-Box & Requirement-Driven**:
   - Every test assertion is derived strictly from `.agents/teamwork/ORIGINAL_REQUEST.md`, `PROJECT.md` (§ Feature Inventory & § Interface Contracts), and `.agents/teamwork/spec_miner_survey_2/handoff.md` (pedagogy & acceptance criteria).
   - Tests interact with the application exclusively through the rendered DOM, documented selectors in `PROJECT.md § Interface Contracts`, file uploads, clicks/keyboard events, Web APIs (`localStorage`, `IndexedDB`, `serviceWorker`), and visible UI output.
   - Tests MUST NOT read or depend on internal JavaScript variable names, closures, or private implementation details inside `index.html`.
2. **Strict BYO & Zero-Copyright Policy**:
   - NEVER copy copyrighted vocabulary or private generated packs (`systan_data.json`, `ext_hooks.json`, `ext_cloze.json`, `systan_ai_pack.json`) into `tests/`.
   - All files in `tests/fixtures/` MUST be 100% synthetic, small, self-contained, non-copyrighted test data covering every required schema feature and edge case.
   - Only one optional read-only integration test in Tier 4 (`T4-08`) inspects `/tmp/drive_notes/systan_data.json` and `/home/antigravity/private/systan_ai_pack.json` directly from their external paths if present on disk (skipping cleanly when absent in CI).
3. **Genuine Assertions Only (No Weakening / No Cheating)**:
   - Because Milestone 2 (`index.html` hardening & 旧帝大 upgrade) runs in parallel with this E2E track, tests MUST enforce the full `PROJECT.md` Interface Contracts without weakening assertions to make unimplemented features pass.
   - Unimplemented or buggy behavior MUST cause the corresponding E2E test to fail clearly with actionable diagnostics.
   - Zero `assert True` placeholders, zero mocked-out browser assertions, zero silent exception swallowing.
4. **Isolation, Determinism & Performance**:
   - A local Python `ThreadingHTTPServer` bound to `127.0.0.1:0` serves `/home/antigravity/taka11110630-png/systan-srs`.
   - A single headless Chromium browser (`/usr/bin/google-chrome` via Playwright Python) is shared per run, while every test executes inside a fresh `BrowserContext` (`localStorage`, `IndexedDB`, Service Worker registrations, and viewport completely isolated per test).
   - Every test attaches `pageerror` and `console` (`error`) listeners and fails on unexpected uncaught errors.

---

## 2. Test Architecture & File Layout

```text
/home/antigravity/taka11110630-png/systan-srs/tests/
├── run_e2e.py                   # Unified CLI runner (`python3 tests/run_e2e.py [--tier 1|2|3|4|all]`)
├── harness.py                   # Local HTTP server, Playwright lifecycle, synthetic bundle/pack loaders, assertions
├── fixtures/                    # 100% synthetic, non-copyrighted fixtures
│   ├── synthetic_bundle.json    # 36 synthetic words (Stages 1–5), 2 synonym groups, missing_stage1, meta, base hooks/patterns
│   ├── minimal_bundle_no_meta.json # Minimal BYO JSON without `meta` key (B6)
│   ├── synthetic_ai_pack.json   # v1.1 AI pack: 3-axis hooks + cloze covering all 13 canonical families, 3 levels, & legacy aliases
│   ├── edge_ai_packs.json       # Prose-wrapped fenced JSON, Japanese level labels, invalid/empty answer, malformed JSON
│   └── xss_bundle.json          # Synthetic bundle & pack containing <img onerror=...>, <script> payloads in word/phrase/cloze/hooks
├── test_tier1_features.py       # Tier 1: Feature Coverage (isolated happy-path tests across F1–F16)
├── test_tier2_boundaries.py     # Tier 2: Boundary & Corner Cases (B1–B18, malformed inputs, XSS, mobile viewport)
├── test_tier3_interactions.py   # Tier 3: Cross-Feature Pairwise Interactions
└── test_tier4_scenarios.py      # Tier 4: Real-World Imperial University (旧帝大) Student Journeys
```

### Canonical Execution Command
```bash
python3 tests/run_e2e.py --tier all
# Or scoped by tier:
python3 tests/run_e2e.py --tier 1
python3 tests/run_e2e.py --tier 2
python3 tests/run_e2e.py --tier 3
python3 tests/run_e2e.py --tier 4
```
- Exit code `0` iff all executed tests pass (skipped optional external-file test counts as SKIP, not FAIL).
- Exit code `1` if any test fails, errors, or if zero tests are collected.

---

## 3. Feature Inventory Coverage Matrix (F1–F16)

| Feature | Description | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---|---|---|---|---|
| **F1** | Kioku-hakase 5 Common Non-Negotiable Rules (no answer leak, non-blaming, textbook evidence, agency, 1 focus point) | `T1-31..T1-34` | `T2-14` | `T3-03` | `T4-03` |
| **F2** | Kioku-hakase Tab 1: AI Mistake Review (`mistake_review`, 6 categories + 8 items + canonical closing) | `T1-31` | — | `T3-03` | `T4-03` |
| **F3** | Kioku-hakase Tab 3: 10-Second AI Pretest (`pretest_chat`, 3 Qs, choice+own-words, 6 post-items, canonical closing) | `T1-32` | — | `T3-03` | `T4-03` |
| **F4** | Kioku-hakase Tab 5: AI Solo Lecture (`teach_chat`, 7 items + 4 post-items + full canonical closing) | `T1-33` | — | `T3-03` | `T4-03` |
| **F5** | Prompt Focus & Ephemeral Policy + JSON Pack Prompt (`json_pack` canonical 13 families & `common/march/national`) | `T1-34` | — | `T3-03` | `T4-03` |
| **F6** | 6-Category Mistake Tagging (`knowledge_gap`..`order_error`) + Legacy Compatibility + Persistence + Diagnostics | `T1-27..T1-30` | `T2-15` | `T3-03`, `T3-09` | `T4-01`, `T4-03` |
| **F7** | Spaced Practice, SRS Ladder & Traffic Brake Fix (B8 `>100` due red alert) | `T1-39` | `T2-12` | `T3-05` | `T4-04`, `T4-07` |
| **F8** | Recall-Speed Measurement, Timer-OFF Fix (B1) & Visibility Pause/Outlier Cap (B5) | `T1-09..T1-12` | `T2-04`, `T2-05` | `T3-02`, `T3-09` | `T4-01` |
| **F9** | 4-Step Fast Loop, Single-Focus, Interleaving & MCQ Double-Grade Fix (B2, B9, B10, B14, B15) | `T1-05..T1-08` | `T2-03`, `T2-09`, `T2-11`, `T2-16` | `T3-01`, `T3-02`, `T3-06` | `T4-01`, `T4-06` |
| **F10** | 3-Axis Memory Hooks (`kn`, `mp`+`et`, `mn`, `co`, `cf`) hidden until reveal + editing | `T1-13..T1-16` | `T2-02` | `T3-04` | `T4-01`, `T4-06` |
| **F11** | StudySapuri 9 Verb Families + 4 旧帝大 Categories Alignment & Alias Map (B4) | `T1-17..T1-20` | `T2-08` | `T3-01`, `T3-08` | `T4-02`, `T4-08` |
| **F12** | 旧帝国大学 Level Filter (`#loopLevelSel`), `ext_cloze` Target Mode & MCQ Level/Family Badges | `T1-21..T1-26` | `T2-08` | `T3-01`, `T3-07`, `T3-10` | `T4-02`, `T4-08` |
| **F13** | External v1.1 Pack Integration Check (220 hooks, >=271 cloze, >=94 `national`, 4 categories, 0 broken `wid`s) | `T1-35` | — | `T3-07` | `T4-08` (read-only external) |
| **F14** | Resilient AI JSON Pack Import/Export, Deduplication & Reload Safety (B6, B11, B12) | `T1-35..T1-38` | `T2-01`, `T2-06`, `T2-07`, `T2-13` | `T3-05`, `T3-07` | `T4-03`, `T4-07` |
| **F15** | BYO Privacy, `.gitignore`, Offline Service Worker (`sw.js`, B3), XSS (B7), Modal Keydown (B13), Mobile (B17) | `T1-01..T1-04`, `T1-44..T1-45` | `T2-02`, `T2-10`, `T2-17`, `T2-18` | `T3-05` | `T4-05` |
| **F16** | Existing Tabs Regression-Free (Study, Pattern SRS, Synonyms, Schedule, Explorer, Wiki/GAS) | `T1-39..T1-43` | `T2-09`, `T2-10`, `T2-12`, `T2-13` | `T3-05`, `T3-06` | `T4-06`, `T4-07` |

---

## 4. Tier Specifications & Coverage Thresholds

### Tier 1 — Feature Coverage (Target: >= 40 tests)
Isolated happy-path verification covering every major user-facing feature group (>= 5 cases per major group):
- **Group A — Onboarding, BYO Privacy & Service Worker (`T1-01..T1-04`, `T1-44..T1-45`)**:
  - Empty onboarding screen renders cleanly without embedded words (`EMBEDDED_BUNDLE === null`), zero console errors.
  - Synthetic BYO bundle upload boots app and hides onboarding.
  - Reloading page persists bundle via IndexedDB/localStorage without re-prompting onboarding.
  - Service Worker (`sw.js`) registers cleanly on `127.0.0.1`.
  - Repo BYO hygiene check: no copyrighted `systan_data.json` / `ext_hooks.json` / `ext_cloze.json` / `systan_ai_pack.json` in repo root, `.gitignore` ignores `.agents/` and private JSON packs.
- **Group B — 4-Step Spiral, Single-Focus & Recall-Speed Timing (`T1-05..T1-12`)**:
  - 4-Step Spiral Round 1 (`en2ja`) displays word & verb skeletons while hiding answer/hooks until reveal.
  - 4-Step Spiral progresses cleanly across Round 1 → Round 2 (`workshop`) → Round 3 (`ja2en`) → Round 4 (`mcq`) → Summary.
  - Single-Focus modes (`en2ja`, `ja2en`, `mcq`, `workshop`) launch and complete cleanly.
  - Recall timer measures positive latency (ms) and displays automaticity feedback after reveal.
  - Timer-OFF (`#loopTimerChk` unchecked) allows fast progression in Round 1 and skips Round 2 when all cards are OK without logging fake latencies.
  - Custom latency threshold modal (`#loopThresholdBtn`) saves updated thresholds and persists across reload.
- **Group C — 3-Axis Memory Hooks (`T1-13..T1-16`)**:
  - Revealed card shows all 3 axes (`kn` loanword, `mp`/`et` etymology, `mn` visual mnemonic) + `co` + `cf`.
  - 3-axis hooks are strictly hidden prior to reveal (Retrieval Practice / Rule 1).
  - User hook editing in Hook Workshop (`userHooks`) persists across reload and overrides AI/base hooks.
  - Imported AI hooks (`extPack.hooks`) override base bundle hooks (`w.hk`) for words without user hooks.
- **Group D — 9 StudySapuri + 4 旧帝大 Families, Level Filter & Badges (`T1-17..T1-26`)**:
  - `#loopVerbFamilySel` offers `"all"` plus all 13 canonical families (9 StudySapuri + 4 旧帝大).
  - Filtering by a StudySapuri family (e.g., `transitive_trap`, including VT-trap verbs lacking `w.pt`) surfaces matching words.
  - Filtering by each of the 4 旧帝大 categories (`inanimate_subject`, `stage5_polysemy`, `stage3_usage`, `composition_trap`) surfaces matching imported questions.
  - `#loopLevelSel` offers `"all"`, `"common"`, `"march"`, `"national"`.
  - `#loopTargetSel` offers `"today_weak"`, `"ext_cloze"`, `"err_reason"`, `"verb_family"`, `"stage_batch"`.
  - Selecting `ext_cloze` + `national` delivers strictly `level === "national"` MCQs, including Stage 3–5 unmarked words.
  - MCQ cards display `data-testid="mcq-level-badge"` and `data-testid="mcq-family-badge"` with accurate labels.
  - MCQ `vocab_confusable` / `stage5_polysemy` items are attributed accurately (not misclassified as `prep_pattern`).
- **Group E — 6-Category Error Tagging & Diagnostics (`T1-27..T1-30`)**:
  - All 6 canonical error tag buttons (`data-errtag="knowledge_gap"`, `"misunderstanding"`, `"misreading"`, `"careless"`, `"confusion"`, `"order_error"`) are selectable on Loop review/miss cards.
  - Selected error tags persist across page reload.
  - Weakness diagnostics display per-tag counts and allow filtering via `err_reason`.
  - Legacy error tags (`prep_pattern`, `confusable`, `slow`, `unlearned`) pre-seeded in `localStorage` remain readable without crashing.
- **Group F — Kioku-hakase AI Prompts & JSON Pack Import/Export (`T1-31..T1-38`)**:
  - Tab 1 (`mistake_review`): includes 6 categories, 8 initial items, 5 post-answer items, no-answer-leak rule, and exact canonical closing phrase (`まずは自分で解いてください。あなたの回答後に、同じミスが残っているかを確認します。`).
  - Tab 3 (`pretest_chat`): specifies 3 Qs, 10s/Q, choice + own-words mix, 6 post-answer items, 旧帝大 focus, and exact canonical closing phrase (`まずは正解を気にせず、10秒だけ考えて答えてください。あなたの回答後に、正解とズレを整理します。`).
  - Tab 5 (`teach_chat`): includes 7 initial items, 4 post-answer items, and exact full canonical closing phrase (`まずは自分の力で答えてください。あなたの回答後に、どの知識を使えばよかったかを整理します。`).
  - JSON Expansion Prompt (`json_pack`): includes canonical `family` (9+4) & `level` (`common`/`march`/`national`) schema with 旧帝大 focus and clean ephemeral scope.
  - Importing `synthetic_ai_pack.json` via file upload updates `#loopExtBadge` with exact hook & cloze counts and persists across reload.
  - Importing JSON via `#loopExtJsonInput` textarea paste merges hooks & cloze cleanly.
  - Re-importing duplicate cloze/hooks deduplicates by `id` / `(wid, stem)` without inflating counts.
  - Export & Reset AI pack work cleanly without corrupting SRS state.
- **Group G — Existing Tabs Regression Suite (`T1-39..T1-43`)**:
  - Study tab (`#tab-study`): card reveal, SRS grading, daily counter increment, undo.
  - Pattern SRS tab (`#tab-pquiz`): bidirectional Pattern ↔ JP card reveal and grading.
  - Synonyms tab (`#tab-synonyms`): renders synthetic synonym groups with nuances and traps.
  - Schedule tab (`#tab-schedule`): displays stage progress & 50-word batch breakdown.
  - Explorer (`#tab-explorer`) & Wiki (`#tab-wiki`): search/filter words, open word detail modal, generate Wiki markdown / backup JSON.

### Tier 2 — Boundary & Corner Cases (Target: >= 18 tests)
- `T2-01`: Minimal BYO JSON without `meta` (`minimal_bundle_no_meta.json`) boots and opens all tabs without throwing (B6).
- `T2-02`: XSS payloads (`<img src=x onerror="window.__xss=1">`, `<script>window.__xss=2</script>`) in word, phrase, `missing_stage1`, cloze stem, and 3-axis hooks never execute (`window.__xss` stays undefined) across Study, Explorer, and Loop (B7).
- `T2-03`: MCQ pause (`⏸ 待機へ`), tab-switch, and threshold-modal save after answering a question CANNOT double-grade or double-increment `daily.done` (B2).
- `T2-04`: `visibilitychange` (hidden → visible) pauses/excludes backgrounded elapsed time so returning after hidden delay does not log bogus multi-minute latency (B5).
- `T2-05`: Abandoned/outlier timer cap sanitizes extreme durations while preserving `>2.0s` slow classification (B5/E6).
- `T2-06`: Prose-wrapped fenced AI JSON (`Here is your pack:\n```json\n{...}\n```\nHope this helps!`) + Japanese level labels (`旧帝大`, `難関私大`, `共通テスト`) import and normalize to `national`/`march`/`common` (B12).
- `T2-07`: Invalid/empty `answer` (`""`, `null`, `99`), non-4 choices, and completely malformed JSON are safely rejected/ignored without corrupting existing `extPack` (B12).
- `T2-08`: Empty filter pools (e.g., `national` before pack import, or narrow empty range) display a clear user-friendly empty state without crashing.
- `T2-09`: Custom word with unusual POS (`pos: "追加"`) still generates 4 distinct MCQ choices in dynamic MCQ mode (B9).
- `T2-10`: Keyboard shortcuts (`Space`, `1`–`4`, `Enter`, etc.) are ignored while `#modalBackdrop` is open (B13).
- `T2-11`: 3-step hint buttons enforce step-lock (Hint 2 & Hint 3 disabled until previous hint is unlocked) (B14).
- `T2-12`: Traffic Brake `>100` due count triggers the red brake alert (`🔴` / congestion brake) even when due queue exceeds 80 (B8).
- `T2-13`: Reloading a different BYO bundle via `#reloadBundleInput` resets stale `patPairs` and `loopState` caches cleanly (B11).
- `T2-14`: Re-uploading the same filename into `#loopExtFileInput` (resetting `input.value = ""`) triggers import again (B12).
- `T2-15`: Stage selector change (`#loopStageSel`) resets stale `#from–#to` range filter inputs (B15).
- `T2-16`: Dynamic VT-trap MCQ handles inflected verbs and avoids mislabeling intransitive `survive in ...` as a transitive trap (B9).
- `T2-17`: Mobile viewport (`390x844`) exhibits zero horizontal overflow (`scrollWidth <= innerWidth`) and compact sticky `.topbar` height (`<= 125px`) (B17).
- `T2-18`: Rapid typing into hook/note editor inputs debounces/persists cleanly without losing final value across reload (B16).

### Tier 3 — Cross-Feature Pairwise Interactions (Target: >= 10 tests)
- `T3-01`: Level Filter (`national`) × Family Filter (`inanimate_subject` / `all`) × Interleaving across multiple families.
- `T3-02`: Timer-OFF × 4-Step Spiral (all-OK Round 1 skips Round 2 Workshop cleanly, proceeds to Round 3 & 4).
- `T3-03`: 6-Category Error Tagging × Weakness Diagnostics × Tab 1 AI Mistake Review Prompt (tagged words & error reasons flow into prompt output).
- `T3-04`: Precedence Chain: Custom User Hooks (`userHooks`) > Imported AI Hooks (`extPack.hooks`) > Base Bundle Hooks (`w.hk`) across Study, Loop, and Explorer Modal.
- `T3-05`: Bundle Reload (`#reloadBundleInput`) × Persistent `extPack` & SRS State (progress and AI pack survive bundle refresh).
- `T3-06`: `#autoAudioChk` unchecked vs checked × `ja2en` reveal (never calls `speechSynthesis.speak` when unchecked) (B10).
- `T3-07`: Re-importing duplicate cloze with updated `why`/`level` × `#loopExtBadge` counts & MCQ badge accuracy (no duplicate inflation).
- `T3-08`: Legacy Family Alias (`vt_trap`, `svoo_to`, `writing_trap`) × Canonical Family Filter (`transitive_trap`, `svoo_vs_to`, `composition_trap`) (bi-directional normalization).
- `T3-09`: Custom Latency Thresholds (`#loopThresholdBtn`) × Slow-Word Detection × SRS Grade Downgrade (`ok` → `tri` + `slow` tag).
- `T3-10`: Stage 3 & Stage 5 Unmarked Words (`mk === ""`) × `ext_cloze` Target Mode × `national` Level Filter (directly drillable even when not in `today_weak`).

### Tier 4 — Real-World Imperial University (旧帝大) Application Scenarios (Target: >= 8 scenarios)
- `T4-01`: **Full 4-Step Spiral Student Session**: Onboard synthetic bundle + AI pack → run 4-Step Spiral → deliberately miss/hesitate on 2 words & ace others → verify missed/slow words populate Round 2 Hook Workshop → edit a personal hook → complete Round 3 (`ja2en`) & Round 4 (`mcq`) → verify summary shows latency stats, slow dangerous words, and updated SRS state after reload.
- `T4-02`: **旧帝大 `national` 4-Category Exam Cram Session**: Filter `ext_cloze` + `national` across all 4 旧帝大 categories (`inanimate_subject`, `stage5_polysemy`, `stage3_usage`, `composition_trap`), verify every rendered MCQ has `national` badge and matching family badge, answer mix of right/wrong, verify explanations (`why`) & `⚠️` traps render cleanly.
- `T4-03`: **End-to-End AI Weakness Loop**: Miss target words in Loop → tag with 6-category error tags (`misunderstanding`, `confusion`) → generate all 4 AI prompts (Tab 1 `mistake_review`, Tab 3 `pretest_chat`, Tab 5 `teach_chat`, `json_pack`) verifying canonical closing phrases & zero answer leakage → paste back an AI-generated prose-wrapped JSON pack with new `national` cloze + hooks → verify import count & immediately drill the newly imported question.
- `T4-04`: **100+ Due Congestion Recovery**: Seed >105 due SRS cards in `localStorage` → load Study tab → verify red Traffic Brake alert triggers (`>100` due) → complete study reviews → verify due count decreases and state persists across reload.
- `T4-05`: **Offline PWA Reload after Service Worker Activation**: Load app on `127.0.0.1` → import synthetic bundle → wait for `navigator.serviceWorker.ready` and controller activation → switch browser context to offline (`context.set_offline(True)`) → reload page → verify app shell boots cleanly offline with persisted bundle and zero uncaught errors.
- `T4-06`: **Custom Learner Study & Backup Workflow**: Add a custom word via Explorer (`pos: "追加"`) + edit 3-axis personal hooks → drill it in Loop MCQ (verifying 4 distinct choices) → export backup JSON / inspect Wiki markdown → reload and confirm full state persistence.
- `T4-07`: **Multi-Tab Cross-Session Journey**: Traverse all 7 tabs (`study` → `loop` → `pquiz` → `synonyms` → `schedule` → `explorer` → `wiki`) performing real interactions in each, toggling dark/light theme, verifying zero console/page errors and persistent theme + progress across reload.
- `T4-08`: **Optional Read-Only Real Pack Integration Check**: If `/tmp/drive_notes/systan_data.json` and `/home/antigravity/private/systan_ai_pack.json` exist on disk (read-only, never copied into repo), upload both into the PWA in headless Chrome, verify `220` hooks, `>=271` cloze, `>=94` `national` cloze, `0` broken `wid`s, all 13 families reachable in `#loopVerbFamilySel`, `national` filter yields exclusively `national` items, and `0` console/page errors. (Skips gracefully if external private files are absent.)
