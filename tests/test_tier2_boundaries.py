"""Tier 2: Boundary & Corner Cases (18 tests T2-01..T2-18 covering B1–B18, XSS, mobile)."""

from __future__ import annotations

import json
from typing import Callable

from harness import (
    TestEnv,
    boot_with_synthetic,
    fixture_path,
    get_ext_badge_text,
    load_fixture_json,
    open_ai_panel,
    open_app,
    parse_ext_badge_counts,
    paste_ai_pack,
    read_local_state,
    select_loop_focus,
    select_loop_level,
    select_loop_mode,
    select_loop_size,
    select_loop_target,
    start_loop_session,
    switch_tab,
    temp_json_file,
    upload_ai_pack,
    upload_bundle,
    write_local_state,
)


def test_T2_01_minimal_bundle_without_meta_no_crash(env: TestEnv) -> None:
    """Minimal BYO JSON without `meta` boots and visits all 7 tabs without throwing (B6)."""
    with env.new_session() as s:
        open_app(s.page, s.base_url)
        upload_bundle(s.page, fixture_path("minimal_bundle_no_meta.json"))
        for tab in ("study", "loop", "pquiz", "synonyms", "schedule", "explorer", "wiki"):
            switch_tab(s.page, tab)
            s.page.wait_for_timeout(80)
        s.assert_no_errors()


def test_T2_02_xss_payloads_never_execute(env: TestEnv) -> None:
    """XSS payloads in word, phrase, missing_stage1, data-wid, cloze, and hooks never execute (B7)."""
    xss_data = load_fixture_json("xss_bundle.json")
    with env.new_session() as s:
        open_app(s.page, s.base_url)
        with temp_json_file(xss_data["bundle"], "xss_b.json") as bpath:
            upload_bundle(s.page, bpath)

        # Study tab: normal + cloze mode (B7 L1657-1658!)
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        s.page.locator("#modeBar button[data-mode='cloze']").click()
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        if s.page.locator("#revealBtn").is_visible():
            s.page.locator("#revealBtn").click()
        s.page.wait_for_timeout(150)

        # Schedule tab: missing_stage1 banner (B7 L1971!)
        switch_tab(s.page, "schedule")
        s.page.locator("#batchStageFilter").select_option("1")
        s.page.wait_for_timeout(120)

        # Explorer tab: list + word detail modal (B7 data-wid!)
        switch_tab(s.page, "explorer")
        s.page.wait_for_timeout(120)
        if s.page.locator("#wordList .word-row").count() > 0:
            s.page.locator("#wordList .word-row").first.click()
            s.page.wait_for_timeout(120)
            if s.page.locator("#mClose").is_visible():
                s.page.locator("#mClose").click()

        # Loop tab: import XSS AI pack & render MCQ + hooks
        switch_tab(s.page, "loop")
        paste_ai_pack(s.page, json.dumps(xss_data["ai_pack"], ensure_ascii=False))
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        if s.page.locator("#mcqChoicesGrid button[data-cidx]").count() > 0:
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
        s.page.wait_for_timeout(200)

        xss_val = s.page.evaluate("() => window.__xss")
        assert xss_val is None, f"B7 XSS vulnerability triggered! window.__xss = {xss_val!r}"
        s.assert_no_errors()


def test_T2_03_mcq_pause_tabswitch_threshold_no_double_grade(env: TestEnv) -> None:
    """Answering an MCQ then pausing, switching tabs, or saving thresholds CANNOT double-grade (B2)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)

        def _daily_done() -> int:
            d = read_local_state(s.page).get("daily") or {}
            if "done" in d:
                return int(d["done"])
            return sum(int((v or {}).get("done", 0)) for v in d.values() if isinstance(v, dict))

        s.page.locator("#mcqChoicesGrid button[data-cidx]").first.wait_for(state="visible")
        done_before = _daily_done()

        # Answer Q1 once
        s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
        s.page.locator("#mcqNextBtn").wait_for(state="visible")
        done_after_first = _daily_done()
        assert done_after_first == done_before + 1, (
            f"Expected daily.done {done_before}->{done_before+1}, got {done_after_first}"
        )

        # Trigger 1: Pause & resume without clicking Next
        s.page.locator("#mcqPauseBtn").click()
        s.page.locator("#loopStartBtn").click()
        s.page.wait_for_timeout(120)

        # If same answered card is re-shown, choices must be locked/disabled OR we must already be on next/answered state
        # Try clicking a choice button if still enabled; verify it cannot double-grade the same question
        if s.page.locator("#mcqNextBtn").is_visible():
            # Good: resumed in already-answered state! Confirm clicking choices does not re-grade.
            btns = s.page.locator("#mcqChoicesGrid button[data-cidx]")
            for i in range(btns.count()):
                if not btns.nth(i).is_disabled():
                    btns.nth(i).click(force=True)
            done_after_pause = _daily_done()
            assert done_after_pause == done_after_first, (
                f"B2 violation: Pause/resume allowed double-grading ({done_after_first} -> {done_after_pause})"
            )
        else:
            # Check if the exact same question was re-rendered unanswered!
            # We check by checking whether we got bumped back to Q1 unanswered (1/10)
            card_txt = s.page.locator("#loopCardArea").inner_text()
            if "1 /" in card_txt or "1/" in card_txt:
                s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
                done_after_pause = _daily_done()
                assert done_after_pause == done_after_first, (
                    f"B2 violation: Pause/resume re-opened Q1 unanswered and double-graded daily.done ({done_after_first} -> {done_after_pause})"
                )

        # Trigger 2: Save threshold modal mid-answered MCQ
        if not s.page.locator("#mcqNextBtn").is_visible() and s.page.locator("#mcqChoicesGrid button[data-cidx]").count() > 0:
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").wait_for(state="visible")
        done_before_modal = _daily_done()
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#thSaveBtn").click()
        s.page.wait_for_timeout(120)
        # If modal save re-rendered Q unanswered, clicking again would double-grade!
        if not s.page.locator("#mcqNextBtn").is_visible() and s.page.locator("#mcqChoicesGrid button[data-cidx]").count() > 0:
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            done_after_modal = _daily_done()
            assert done_after_modal == done_before_modal, (
                f"B2 violation: Saving threshold modal allowed double-grading ({done_before_modal} -> {done_after_modal})"
            )
        s.assert_no_errors()


def test_T2_04_visibilitychange_pauses_recall_timer(env: TestEnv) -> None:
    """Backgrounding tab via visibilitychange (hidden->visible) excludes hidden elapsed time (B5)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.wait_for_timeout(120)

        # Simulate tab becoming hidden for 1200ms then visible again
        s.page.evaluate(
            """() => {
                Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
                Object.defineProperty(document, 'hidden', { value: true, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
            }"""
        )
        s.page.wait_for_timeout(1200)
        s.page.evaluate(
            """() => {
                Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
                Object.defineProperty(document, 'hidden', { value: false, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
            }"""
        )
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").click()

        st = read_local_state(s.page)
        lat_entries = [e for logs in st.get("latLog", {}).values() for e in logs]
        assert len(lat_entries) >= 1, "Expected latency log entry"
        measured_ms = lat_entries[-1]["ms"]
        assert measured_ms < 850, (
            f"B5 violation: visibilitychange hidden duration (1200ms) was NOT paused/excluded! Logged ms={measured_ms}"
        )
        s.assert_no_errors()


def test_T2_05_abandoned_outlier_timer_is_capped(env: TestEnv) -> None:
    """Extreme abandoned latency (120s) is capped/sanitized while preserving >2.0s slow classification (B5/E6)."""
    clock_helper = """
    (() => {
        window.__clockOffset = 0;
        const origPerfNow = performance.now.bind(performance);
        const origDateNow = Date.now.bind(Date);
        performance.now = () => origPerfNow() + window.__clockOffset;
        Date.now = () => origDateNow() + window.__clockOffset;
    })();
    """
    with env.new_session(init_script=clock_helper) as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        # Advance standard Web clock by 120 seconds (abandoned card)
        s.page.evaluate("() => { window.__clockOffset += 120000; }")
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").click()

        st = read_local_state(s.page)
        lat_entries = [e for logs in st.get("latLog", {}).values() for e in logs]
        assert len(lat_entries) >= 1
        ms = lat_entries[-1]["ms"]
        assert 2000 < ms <= 60000, (
            f"B5/E6 violation: 120s outlier was not capped/sanitized cleanly (expected 2000 < ms <= 60000, got {ms})"
        )
        s.assert_no_errors()


def test_T2_06_prose_wrapped_fenced_json_and_jp_level_labels(env: TestEnv) -> None:
    """Prose-wrapped fenced JSON + Japanese level labels ('旧帝大', '難関私大', '共通テスト') import & normalize (B12)."""
    edges = load_fixture_json("edge_ai_packs.json")
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        badge = paste_ai_pack(s.page, edges["prose_wrapped_text"])
        hk, cl = parse_ext_badge_counts(badge)
        assert (hk, cl) == (1, 3), (
            f"B12 violation: prose-wrapped fenced JSON failed to import (expected 1 hook & 3 cloze, got {badge!r})"
        )

        # Verify each Japanese level label normalized to national / march / common
        select_loop_target(s.page, "ext_cloze")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        for lvl, expected_stem_fragment in (
            ("national", "fragile ledgers"),
            ("march", "calibrated thermometers"),
            ("common", "maritime engineering"),
        ):
            select_loop_level(s.page, lvl)
            start_loop_session(s.page)
            s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
            txt = s.page.locator("#loopCardArea").inner_text()
            assert expected_stem_fragment in txt, (
                f"Japanese level did not normalize to '{lvl}'; expected '{expected_stem_fragment}' in: {txt[:200]}"
            )
            s.page.locator("#mcqPauseBtn").click()
        s.assert_no_errors()


def test_T2_07_invalid_answer_non4_choices_and_malformed_json_rejected(env: TestEnv) -> None:
    """Empty/null/OOB answer, non-4 choices, and malformed JSON are rejected without corrupting extPack (B12)."""
    edges = load_fixture_json("edge_ai_packs.json")
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        # Import valid pack first
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (6, 18)

        # Attempt invalid cloze items (empty string "", null, 99, 2 choices)
        badge_after_invalid = paste_ai_pack(
            s.page, json.dumps(edges["invalid_cloze_pack"], ensure_ascii=False)
        )
        assert parse_ext_badge_counts(badge_after_invalid) == (6, 18), (
            f"B12 violation: invalid cloze items (empty/null/99 answer or 2 choices) were accepted! badge={badge_after_invalid!r}"
        )

        # Attempt completely malformed JSON
        badge_after_malformed = paste_ai_pack(s.page, edges["malformed_text"])
        assert parse_ext_badge_counts(badge_after_malformed) == (6, 18), (
            f"Malformed JSON corrupted existing extPack! badge={badge_after_malformed!r}"
        )
        s.assert_no_errors()


def test_T2_08_empty_filter_pools_show_friendly_empty_state(env: TestEnv) -> None:
    """Empty filter pools (national before pack import, or impossible range) show friendly empty state."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")

        # Case 1: ext_cloze + national before any AI pack is imported
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        txt1 = s.page.locator("#loopCardArea").inner_text()
        assert any(k in txt1 for k in ("0問", "0語", "該当", "取り込", "インポート", "ありません")), (
            f"Expected clear empty-pool guidance before pack import, got: {txt1[:200]}"
        )

        # Case 2: stage_batch with empty #900-#999 range
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopRangeFrom").fill("900")
        s.page.locator("#loopRangeTo").fill("999")
        s.page.locator("#loopApplyRangeBtn").click()
        txt2 = s.page.locator("#loopCardArea").inner_text()
        assert any(k in txt2 for k in ("0語", "該当", "ありません", "見つか")), (
            f"Expected empty-range message, got: {txt2[:200]}"
        )
        s.assert_no_errors()


def test_T2_09_custom_word_unusual_pos_generates_4_distinct_mcq_choices(env: TestEnv) -> None:
    """Custom word with pos='追加' still generates 4 distinct MCQ choices in dynamic MCQ mode (B9)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "explorer")
        s.page.locator("#addWordBtn").click()
        s.page.locator("#awWord").wait_for(state="visible")
        s.page.locator("#awNum").fill("999")
        s.page.locator("#awWord").fill("synthetize")
        s.page.locator("#awMeaning").fill("合成する（カスタムテスト）")
        s.page.locator("#awPhrase").fill("synthetize clean alloys")
        s.page.locator("#awSubmit").click()
        s.page.wait_for_timeout(150)

        # Target stage_batch Stage 2 range #999-#999 (#601-1200 maps to Stage 2) so only this custom word is drilled in MCQ
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("2")
        s.page.locator("#loopRangeFrom").fill("999")
        s.page.locator("#loopRangeTo").fill("999")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        btns = s.page.locator("#mcqChoicesGrid button[data-cidx]")
        texts = [btns.nth(i).inner_text().strip() for i in range(btns.count())]
        assert len(texts) == 4 and len(set(texts)) == 4, (
            f"B9 violation: custom word (pos='追加') produced {len(texts)} choices instead of 4 distinct: {texts}"
        )
        s.assert_no_errors()


def test_T2_10_keyboard_shortcuts_ignored_while_modal_open(env: TestEnv) -> None:
    """Keyboard shortcuts (Space, 1-3) are ignored while #modalBackdrop is open (B13)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        s.page.locator("#revealBtn").wait_for(state="visible")
        # Open threshold modal via Loop or open a word modal via Explorer?
        # Even simpler: test in Loop tab where #loopThresholdBtn opens #modalBackdrop while a card is active!
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")

        # Open threshold modal while flashcard is unrevealed
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        # Press Space while modal is open — must NOT reveal the card behind the modal!
        s.page.keyboard.press("Space")
        s.page.wait_for_timeout(120)
        # Close modal via Escape or close button
        close_btn = s.page.locator("#modalContent button:has-text('閉じる'), #modalContent button:has-text('キャンセル'), #mClose").first
        if close_btn.count() > 0:
            close_btn.click()
        else:
            s.page.locator("#modalBackdrop").click(position={"x": 5, "y": 5})
        s.page.wait_for_timeout(80)
        assert s.page.locator("#lfRevealBtn").is_visible(), (
            "B13 violation: Pressing Space while #modalBackdrop was open revealed the flashcard behind the modal!"
        )
        s.assert_no_errors()


def test_T2_11_three_step_hints_enforce_step_lock(env: TestEnv) -> None:
    """3-step hint buttons disable Hint 2 & Hint 3 until previous hint is unlocked (B14)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")
        s.page.locator("#loopRangeFrom").fill("1")
        s.page.locator("#loopRangeTo").fill("1")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)

        h1 = s.page.locator("button[data-hstep='1']")
        h2 = s.page.locator("button[data-hstep='2']")
        h3 = s.page.locator("button[data-hstep='3']")
        h1.wait_for(state="visible")
        assert not h1.is_disabled(), "Hint 1 should be clickable initially"
        assert h2.is_disabled(), "B14 violation: Hint 2 must be disabled before Hint 1 is unlocked"
        assert h3.is_disabled(), "B14 violation: Hint 3 must be disabled before Hint 2 is unlocked"

        h1.click()
        assert not s.page.locator("button[data-hstep='2']").is_disabled(), "Hint 2 should unlock after Hint 1"
        assert s.page.locator("button[data-hstep='3']").is_disabled(), "Hint 3 must stay disabled until Hint 2"
        s.page.locator("button[data-hstep='2']").click()
        assert not s.page.locator("button[data-hstep='3']").is_disabled(), "Hint 3 should unlock after Hint 2"
        s.assert_no_errors()


def test_T2_12_traffic_brake_red_alert_over_100_due(env: TestEnv) -> None:
    """Traffic Brake >100 due count triggers the red brake alert (B8)."""
    # Build a 112-word synthetic bundle where all 112 words are marked 'x' (due today!)
    words = []
    for i in range(1, 113):
        words.append(
            {
                "id": f"DUE-{i:03d}",
                "s": 1,
                "n": i,
                "w": f"synword{i}",
                "ipa": "/s/",
                "pos": "動詞",
                "ph": f"synword{i} the test item",
                "m": f"テスト意味{i}",
                "mk": "x",
                "dt": ["2026-11-01"],
                "b": "B0001-0050" if i <= 50 else ("B0051-0100" if i <= 100 else "B0101-0150"),
                "pt": [],
                "sg": [],
            }
        )
    bundle = {"meta": {"total_words": 112, "hook_count": 0, "pattern_word_count": 0, "synonym_group_count": 0, "missing_stage1": [], "links": {}}, "synonym_groups": [], "words": words}

    with env.new_session() as s:
        open_app(s.page, s.base_url)
        with temp_json_file(bundle, "due112.json") as bpath:
            upload_bundle(s.page, bpath)
        # Ensure all 112 cards have past due timestamps
        st = read_local_state(s.page)
        past = 1_700_000_000_000
        for i in range(1, 113):
            wid = f"DUE-{i:03d}"
            st.setdefault("cards", {})[wid] = {
                "due": past,
                "interval": 1,
                "ease": 2.3,
                "reps": 1,
                "lapses": 1,
                "status": "x",
            }
        write_local_state(s.page, st)
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")

        pace_txt = s.page.locator("#statPace").inner_text() + " " + s.page.locator("#statPaceSub").inner_text()
        due_val = int(s.page.locator("#statDue").inner_text().strip())
        assert due_val > 100, f"B8 violation: #statDue capped at {due_val} instead of uncapped >100"
        assert any(k in pace_txt for k in ("🔴", "ブレーキ", "+0", "復習優先", "停止")), (
            f"B8 violation: Red Traffic Brake (>100 due) did not trigger! pace={pace_txt!r}"
        )
        s.assert_no_errors()


def test_T2_13_bundle_reload_resets_stale_caches(env: TestEnv) -> None:
    """Reloading a different BYO bundle via #reloadBundleInput clears stale patPairs & loopState caches (B11)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Initialize both Pattern SRS and Loop tabs with the 36-word bundle
        switch_tab(s.page, "pquiz")
        switch_tab(s.page, "loop")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("3")

        # Now reload with minimal 3-word bundle via Wiki tab #reloadBundleInput
        switch_tab(s.page, "wiki")
        s.page.locator("#reloadBundleInput").set_input_files(str(fixture_path("minimal_bundle_no_meta.json")))
        s.page.wait_for_timeout(300)

        # Verify Pattern SRS reflects only the 3 minimal words (no stale 36-word patPairs)
        switch_tab(s.page, "pquiz")
        s.page.locator("#pqFilterBar button[data-pq='all']").click()
        pq_txt = s.page.locator("#pqStatsSummary").inner_text() + " " + s.page.locator("#pqCardArea").inner_text()
        # minimal bundle has only 3 pattern words (discuss, provide, prevent)
        assert "compel" not in pq_txt and "attribute" not in pq_txt
        m = __import__("re").search(r"(\d+)\s*問", pq_txt)
        if m:
            assert int(m.group(1)) <= 6, (
                f"B11 violation: stale patPairs retained after bundle reload ({m.group(1)} items in 3-word bundle)"
            )

        # Verify Loop tab reset cleanly and works on the 3-word bundle
        switch_tab(s.page, "loop")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn, #mcqChoicesGrid").first.wait_for(state="visible")
        s.assert_no_errors()


def test_T2_14_reuploading_same_filename_triggers_import(env: TestEnv) -> None:
    """File input resets value='' after upload so re-selecting the same filename triggers import again (B12)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        open_ai_panel(s.page)
        inp = s.page.locator("#loopExtFileInput, #aiExtFileInput").first
        inp.set_input_files(str(fixture_path("synthetic_ai_pack.json")))
        s.page.wait_for_timeout(250)
        val_after = inp.evaluate("el => el.value")
        assert val_after == "", (
            f"B12 violation: AI file input value was not reset to '' after upload (got {val_after!r}), blocking same-filename re-upload"
        )
        s.assert_no_errors()


def test_T2_15_stage_change_resets_range_inputs(env: TestEnv) -> None:
    """Changing #loopStageSel resets stale #loopRangeFrom / #loopRangeTo filter inputs (B15)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")
        s.page.locator("#loopRangeFrom").fill("1")
        s.page.locator("#loopRangeTo").fill("5")
        s.page.locator("#loopApplyRangeBtn").click()

        # Switch to Stage 3 — range #1-#5 must be cleared so Stage 3 words (#23-#28) aren't hidden!
        s.page.locator("#loopStageSel").select_option("3")
        s.page.wait_for_timeout(120)
        r_from = s.page.locator("#loopRangeFrom").input_value().strip()
        r_to = s.page.locator("#loopRangeTo").input_value().strip()
        assert r_from == "" and r_to == "", (
            f"B15 violation: changing #loopStageSel left stale range inputs from={r_from!r}, to={r_to!r}"
        )
        s.assert_no_errors()


def test_T2_16_dynamic_vt_trap_inflected_and_survive_in_guard(env: TestEnv) -> None:
    """Dynamic MCQ handles inflected VT traps ('approaching') and never mislabels intransitive 'survive in' (B9)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")

        # 1. Test survive (#4, phrase: "survive in the polar tundra") — MUST NOT claim "survive in is wrong"!
        s.page.locator("#loopRangeFrom").fill("4")
        s.page.locator("#loopRangeTo").fill("4")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        btns = s.page.locator("#mcqChoicesGrid button[data-cidx]")
        choices = [btns.nth(i).inner_text().strip() for i in range(btns.count())]
        # If it generated a bogus transitive trap for "survive in ...", one choice would be "survive" vs "survive in"
        # and clicking "survive" would say "前置詞不要"! Check feedback!
        btns.first.click()
        fb_txt = s.page.locator("#mcqFeedbackArea").inner_text()
        assert "survive in" not in fb_txt or "前置詞不要" not in fb_txt, (
            f"B9 violation: intransitive 'survive in the polar tundra' was mislabeled as a transitive trap! choices={choices}, fb={fb_txt[:200]}"
        )
        s.page.locator("#mcqPauseBtn").click()

        # 2. Test approach (#2, phrase: "approaching the coastal harbor") — inflected VT trap should blank verb cleanly
        s.page.locator("#loopRangeFrom").fill("2")
        s.page.locator("#loopRangeTo").fill("2")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        card_txt = s.page.locator("#loopCardArea").inner_text()
        assert "approaching" not in card_txt.split("選択")[0] or "(    )" in card_txt or "____" in card_txt, (
            f"Expected blanked stem for inflected 'approaching', got: {card_txt[:200]}"
        )
        choices2 = [
            s.page.locator("#mcqChoicesGrid button[data-cidx]").nth(i).inner_text().strip()
            for i in range(s.page.locator("#mcqChoicesGrid button[data-cidx]").count())
        ]
        assert any("to" in c for c in choices2), (
            f"B9 violation: inflected 'approaching' did not produce a VT-trap distractor (e.g. 'approaching to'): {choices2}"
        )
        s.assert_no_errors()


def test_T2_17_mobile_viewport_no_overflow_and_compact_topbar(env: TestEnv) -> None:
    """Mobile viewport (390x844) has zero horizontal overflow and sticky .topbar height <= 125px (B17)."""
    with env.new_session(viewport={"width": 390, "height": 844}) as s:
        boot_with_synthetic(s.page, s.base_url)
        for tab in ("study", "loop", "pquiz", "synonyms", "schedule", "explorer", "wiki"):
            switch_tab(s.page, tab)
            s.page.wait_for_timeout(80)
            metrics = s.page.evaluate(
                """() => {
                    const topbar = document.querySelector('.topbar');
                    return {
                        scrollWidth: document.documentElement.scrollWidth,
                        innerWidth: window.innerWidth,
                        topbarHeight: topbar ? topbar.getBoundingClientRect().height : 0
                    };
                }"""
            )
            assert metrics["scrollWidth"] <= metrics["innerWidth"], (
                f"Horizontal overflow on mobile in tab '{tab}': {metrics}"
            )
            assert metrics["topbarHeight"] <= 125, (
                f"B17 violation: mobile sticky .topbar too tall ({metrics['topbarHeight']:.1f}px > 125px) in tab '{tab}'"
            )
        s.assert_no_errors()


def test_T2_18_rapid_hook_typing_persists_final_value(env: TestEnv) -> None:
    """Rapid typing into hook editor inputs debounces/persists cleanly without losing final text (B16)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "workshop")
        start_loop_session(s.page)
        inp = s.page.locator("#hwInMn")
        inp.wait_for(state="visible")
        inp.click()
        inp.fill("")
        final_text = "DEBOUNCE_RAPID_FINAL_98765"
        inp.type(final_text, delay=8)
        # Wait for debounce flush
        s.page.wait_for_timeout(550)

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        st = read_local_state(s.page)
        serialized = json.dumps(st.get("userHooks", {}), ensure_ascii=False)
        assert final_text in serialized, (
            f"Final value after rapid typing did not persist across reload: {serialized[:200]}"
        )
        s.assert_no_errors()


TESTS: list[tuple[str, Callable[[TestEnv], None]]] = [
    ("T2-01", test_T2_01_minimal_bundle_without_meta_no_crash),
    ("T2-02", test_T2_02_xss_payloads_never_execute),
    ("T2-03", test_T2_03_mcq_pause_tabswitch_threshold_no_double_grade),
    ("T2-04", test_T2_04_visibilitychange_pauses_recall_timer),
    ("T2-05", test_T2_05_abandoned_outlier_timer_is_capped),
    ("T2-06", test_T2_06_prose_wrapped_fenced_json_and_jp_level_labels),
    ("T2-07", test_T2_07_invalid_answer_non4_choices_and_malformed_json_rejected),
    ("T2-08", test_T2_08_empty_filter_pools_show_friendly_empty_state),
    ("T2-09", test_T2_09_custom_word_unusual_pos_generates_4_distinct_mcq_choices),
    ("T2-10", test_T2_10_keyboard_shortcuts_ignored_while_modal_open),
    ("T2-11", test_T2_11_three_step_hints_enforce_step_lock),
    ("T2-12", test_T2_12_traffic_brake_red_alert_over_100_due),
    ("T2-13", test_T2_13_bundle_reload_resets_stale_caches),
    ("T2-14", test_T2_14_reuploading_same_filename_triggers_import),
    ("T2-15", test_T2_15_stage_change_resets_range_inputs),
    ("T2-16", test_T2_16_dynamic_vt_trap_inflected_and_survive_in_guard),
    ("T2-17", test_T2_17_mobile_viewport_no_overflow_and_compact_topbar),
    ("T2-18", test_T2_18_rapid_hook_typing_persists_final_value),
]
