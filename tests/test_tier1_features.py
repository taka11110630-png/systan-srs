"""Tier 1: Feature Coverage (45 isolated happy-path tests across F1–F16).

Strictly opaque-box tests interacting only through rendered DOM, documented
selectors (PROJECT.md § Interface Contracts), file uploads, clicks/keys,
localStorage/IndexedDB, and navigator.serviceWorker.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from harness import (
    CANONICAL_ERROR_TAGS,
    CANONICAL_FAMILIES,
    CANONICAL_LEVELS,
    CANONICAL_TARGETS,
    CLOSING_TAB1,
    CLOSING_TAB3,
    CLOSING_TAB5,
    IMPERIAL_4_FAMILIES,
    LEGACY_ERROR_TAGS,
    REPO_ROOT,
    TestEnv,
    boot_with_synthetic,
    fixture_path,
    get_ai_prompt_text,
    get_available_levels,
    get_available_loop_targets,
    get_available_verb_families,
    get_ext_badge_text,
    load_fixture_json,
    open_ai_panel,
    open_app,
    parse_ext_badge_counts,
    paste_ai_pack,
    read_local_state,
    select_ai_prompt_type,
    select_loop_focus,
    select_loop_level,
    select_loop_mode,
    select_loop_size,
    select_loop_target,
    select_verb_family,
    start_loop_session,
    switch_tab,
    temp_json_file,
    upload_ai_pack,
    upload_bundle,
    write_local_state,
)


def _complete_flash_round(page, grade_btn_id: str = "#lfGradeOk", max_cards: int = 40) -> int:
    """Reveal and grade flashcard items until the current round transitions."""
    count = 0
    for _ in range(max_cards):
        if page.locator("#lfRevealBtn").count() > 0 and page.locator("#lfRevealBtn").is_visible():
            page.locator("#lfRevealBtn").click()
            page.locator(grade_btn_id).wait_for(state="visible")
            page.locator(grade_btn_id).click()
            count += 1
            page.wait_for_timeout(40)
        else:
            break
    return count


def _complete_mcq_round(page, choice_idx: int = 0, max_cards: int = 40) -> int:
    """Answer MCQ cards until the MCQ round ends."""
    count = 0
    for _ in range(max_cards):
        grid = page.locator("#mcqChoicesGrid")
        if grid.count() > 0 and grid.is_visible():
            btns = grid.locator("button[data-cidx]")
            assert btns.count() == 4, f"Expected 4 MCQ choices, found {btns.count()}"
            btns.nth(choice_idx).click()
            page.locator("#mcqNextBtn").wait_for(state="visible")
            page.locator("#mcqNextBtn").click()
            count += 1
            page.wait_for_timeout(40)
        else:
            break
    return count


# ===========================================================================
# Group A: Onboarding, BYO Privacy & Service Worker (T1-01..T1-04, T1-44..T1-45)
# ===========================================================================


def test_T1_01_onboarding_empty_state_byo(env: TestEnv) -> None:
    """Empty onboarding screen renders cleanly with zero embedded words and zero errors."""
    with env.new_session() as s:
        open_app(s.page, s.base_url)
        assert s.page.locator("#onboardingScreen").is_visible(), "Onboarding screen should be visible on first boot"
        assert not s.page.locator("#appMain").is_visible(), "#appMain must remain hidden before BYO bundle upload"
        html_src = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        assert "const EMBEDDED_BUNDLE = null;" in html_src, "BYO violation: EMBEDDED_BUNDLE must be null"
        s.assert_no_errors()


def test_T1_02_byo_bundle_upload_boots_app(env: TestEnv) -> None:
    """Uploading synthetic BYO bundle hides onboarding and renders Study dashboard."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        assert not s.page.locator("#onboardingScreen").is_visible()
        assert s.page.locator("#appMain").is_visible()
        assert s.page.locator("#tab-study.active").is_visible()
        due_text = s.page.locator("#statDue").inner_text().strip()
        assert due_text.isdigit(), f"Expected numeric due count, got {due_text!r}"
        s.assert_no_errors()


def test_T1_03_bundle_persists_across_reload(env: TestEnv) -> None:
    """Reloading the page restores the BYO bundle via IndexedDB without showing onboarding."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        assert not s.page.locator("#onboardingScreen").is_visible(), (
            "Onboarding re-appeared after reload; IndexedDB/localStorage bundle persistence failed"
        )
        s.assert_no_errors()


def test_T1_04_service_worker_registers_cleanly(env: TestEnv) -> None:
    """sw.js exists in repo root and registers cleanly as a Service Worker on 127.0.0.1 (B3)."""
    sw_file = REPO_ROOT / "sw.js"
    assert sw_file.exists(), "Contract/B3 violation: sw.js does not exist in repo root"
    with env.new_session() as s:
        open_app(s.page, s.base_url)
        sw_info = s.page.evaluate(
            """async () => {
                if (!('serviceWorker' in navigator)) return { supported: false };
                const reg = await Promise.race([
                    navigator.serviceWorker.ready,
                    new Promise((resolve) => setTimeout(() => resolve(null), 3500))
                ]);
                const regs = await navigator.serviceWorker.getRegistrations();
                return {
                    supported: true,
                    ready: Boolean(reg),
                    count: regs.length,
                    scriptURL: reg && reg.active ? reg.active.scriptURL : (regs[0]?.installing?.scriptURL || regs[0]?.waiting?.scriptURL || regs[0]?.active?.scriptURL || '')
                };
            }"""
        )
        assert sw_info.get("supported"), "Browser lacks serviceWorker support"
        assert sw_info.get("count", 0) >= 1 and "sw.js" in sw_info.get("scriptURL", ""), (
            f"Expected sw.js registration, got {sw_info}"
        )
        s.assert_no_errors()


# ===========================================================================
# Group B: 4-Step Spiral, Single-Focus & Recall-Speed Timing (T1-05..T1-12)
# ===========================================================================


def test_T1_05_spiral_round1_hides_answer_and_hooks_before_reveal(env: TestEnv) -> None:
    """4-Step Spiral Round 1 (en2ja) hides Japanese meaning and 3-axis hooks until reveal."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "spiral")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        card_before = s.page.locator("#loopCardArea").inner_text()
        assert "BASE_KN_" not in card_before and "BASE_MN_" not in card_before, (
            "Memory hooks leaked before reveal (violates Retrieval Practice / Rule 1)"
        )
        assert s.page.locator("#lfGradeOk").count() == 0 or not s.page.locator("#lfGradeOk").is_visible(), (
            "Grade buttons should not be visible before revealing answer"
        )
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").wait_for(state="visible")
        s.assert_no_errors()


def test_T1_06_spiral_completes_all_4_rounds_to_summary(env: TestEnv) -> None:
    """4-Step Spiral progresses cleanly across Round 1 -> Round 2 -> Round 3 -> Round 4 -> Summary."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "spiral")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)

        # Round 1: miss the first card so Round 2 Hook Workshop populates, ace the rest
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeX").click()
        r1_rest = _complete_flash_round(s.page, "#lfGradeOk")
        assert r1_rest >= 1, "Expected multiple cards in Round 1"

        # Round 2: Hook Workshop should appear with #hwInKn / #hwSkipRoundBtn
        s.page.locator("#hwInKn, #hwSkipRoundBtn, #r2SkipBtn").first.wait_for(state="visible")
        if s.page.locator("#hwSkipRoundBtn").is_visible():
            s.page.locator("#hwSkipRoundBtn").click()
        elif s.page.locator("#r2SkipBtn").is_visible():
            s.page.locator("#r2SkipBtn").click()

        # Round 3: ja2en reverse flashcard
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        r3_cnt = _complete_flash_round(s.page, "#lfGradeOk")
        assert r3_cnt >= 1, "Expected >=1 card in Round 3 (ja2en)"

        # Round 4: MCQ
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        r4_cnt = _complete_mcq_round(s.page, choice_idx=0)
        assert r4_cnt >= 1, "Expected >=1 MCQ in Round 4"

        # Summary screen
        s.page.locator("#sumNextSetBtn, #loopRestartBtn").first.wait_for(state="visible")
        summary_txt = s.page.locator("#loopCardArea").inner_text()
        assert "セット完了" in summary_txt or "サマリー" in summary_txt or "平均" in summary_txt, (
            f"Expected summary screen after Round 4, got: {summary_txt[:200]}"
        )
        s.assert_no_errors()


def test_T1_07_single_focus_en2ja_and_ja2en(env: TestEnv) -> None:
    """Single-Focus modes en2ja and ja2en launch and complete cleanly to summary."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_size(s.page, 10)

        for fmt in ("en2ja", "ja2en"):
            select_loop_focus(s.page, fmt)
            start_loop_session(s.page)
            s.page.locator("#lfRevealBtn").wait_for(state="visible")
            n = _complete_flash_round(s.page, "#lfGradeOk")
            assert n >= 1, f"Single focus {fmt} rendered 0 cards"
            s.page.locator("#sumNextSetBtn, #loopRestartBtn").first.wait_for(state="visible")
            # Return to waiting state for next focus mode
            s.page.locator("#loopStartBtn, #sumNextSetBtn").first.wait_for(state="visible")
            select_loop_mode(s.page, "single")
        s.assert_no_errors()


def test_T1_08_single_focus_mcq_and_workshop(env: TestEnv) -> None:
    """Single-Focus modes mcq and workshop launch and complete cleanly."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_size(s.page, 10)

        # MCQ single focus
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        n = _complete_mcq_round(s.page, choice_idx=0)
        assert n >= 1, "Single focus MCQ rendered 0 questions"
        s.page.locator("#sumNextSetBtn, #loopRestartBtn").first.wait_for(state="visible")

        # Workshop single focus
        select_loop_focus(s.page, "workshop")
        start_loop_session(s.page)
        s.page.locator("#hwInKn").wait_for(state="visible")
        s.page.locator("#hwSkipRoundBtn").click()
        s.assert_no_errors()


def test_T1_09_recall_timer_measures_positive_latency(env: TestEnv) -> None:
    """Recall timer measures positive latency (ms) and persists it in latLog."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.wait_for_timeout(180)
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").wait_for(state="visible")
        card_txt = s.page.locator("#loopCardArea").inner_text()
        assert re.search(r"\d+\.\d+s", card_txt), f"Expected measured seconds readout after reveal, got: {card_txt[:200]}"
        s.page.locator("#lfGradeOk").click()
        st = read_local_state(s.page)
        lat_entries = [e for logs in st.get("latLog", {}).values() for e in logs]
        assert len(lat_entries) >= 1 and lat_entries[-1]["ms"] >= 100, (
            f"Expected positive measured ms in latLog, got {lat_entries}"
        )
        s.assert_no_errors()


def test_T1_10_timer_off_allows_fast_clear_and_skips_round2_without_fake_ms(env: TestEnv) -> None:
    """Timer-OFF allows Round 1 all-OK to skip Round 2 without logging fake latency ms (B1)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "spiral")
        select_loop_size(s.page, 10)
        # Uncheck timer
        chk = s.page.locator("#loopTimerChk")
        chk.wait_for(state="visible")
        if chk.is_checked():
            chk.uncheck()
        assert not chk.is_checked()
        start_loop_session(s.page)

        # Complete all Round 1 cards with OK
        n = _complete_flash_round(s.page, "#lfGradeOk")
        assert n >= 1

        # B1 assertion: Round 2 must offer skip / zero weak words, NOT populate all cards as weak!
        # And latLog must NOT contain fake latency entries recorded while timer was OFF.
        st = read_local_state(s.page)
        lat_entries = [e for logs in st.get("latLog", {}).values() for e in logs]
        assert len(lat_entries) == 0, (
            f"B1 violation: Timer-OFF logged {len(lat_entries)} fake latency entries: {lat_entries[:3]}"
        )
        # Verify Round 2 skip screen (r2SkipBtn) OR already skipped directly to Round 3 (lfRevealBtn)
        is_skip_or_r3 = (
            s.page.locator("#r2SkipBtn").is_visible()
            or (s.page.locator("#lfRevealBtn").is_visible() and not s.page.locator("#hwInKn").is_visible())
        )
        assert is_skip_or_r3, (
            "B1 violation: Timer-OFF Round 1 all-OK pushed cards into Round 2 Hook Workshop instead of skipping Round 2"
        )
        s.assert_no_errors()


def test_T1_11_custom_latency_threshold_modal_persists(env: TestEnv) -> None:
    """Custom latency thresholds saved via #loopThresholdBtn persist across reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#thEnFast").wait_for(state="visible")
        s.page.locator("#thEnFast").fill("1.4")
        s.page.locator("#thEnPass").fill("2.8")
        s.page.locator("#thSaveBtn").click()

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        switch_tab(s.page, "loop")
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#thEnFast").wait_for(state="visible")
        assert float(s.page.locator("#thEnFast").input_value()) == 1.4
        assert float(s.page.locator("#thEnPass").input_value()) == 2.8
        s.assert_no_errors()


def test_T1_12_recall_automaticity_slow_classification(env: TestEnv) -> None:
    """Recall latency exceeding pass threshold triggers slow classification and warning."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        # Set very tight pass threshold (0.3s) so test runs fast without sleeping seconds
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#thEnFast").fill("0.1")
        s.page.locator("#thEnPass").fill("0.2")
        s.page.locator("#thSaveBtn").click()

        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.wait_for_timeout(320)
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").click()

        st = read_local_state(s.page)
        slow_tagged = [wid for wid, tags in st.get("errTags", {}).items() if "slow" in tags]
        assert len(slow_tagged) >= 1, (
            f"Expected slow latency above 0.2s pass threshold to tag 'slow', errTags={st.get('errTags')}"
        )
        s.assert_no_errors()


# ===========================================================================
# Group C: 3-Axis Memory Hooks (T1-13..T1-16)
# ===========================================================================


def test_T1_13_revealed_card_shows_all_3_hook_axes(env: TestEnv) -> None:
    """Revealed card renders all 3 memory hook axes (kn, mp+et, mn) plus co & cf."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "explorer")
        s.page.locator("#searchInput").fill("discuss")
        s.page.wait_for_timeout(150)
        s.page.locator("#wordList .word-row").first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        modal_txt = s.page.locator("#modalContent").inner_text()
        assert "BASE_KN_DISCUSS" in modal_txt or "BASE_KN_DISCUSS" in s.page.locator("#mHkKn").input_value()
        assert "BASE_ET_DISCUSS" in modal_txt or "BASE_ET_DISCUSS" in s.page.locator("#mHkEt").input_value()
        assert "BASE_MN_DISCUSS" in modal_txt or "BASE_MN_DISCUSS" in s.page.locator("#mHkMn").input_value()
        assert "BASE_CO_DISCUSS" in modal_txt
        assert "dis-" in modal_txt and "cuss" in modal_txt
        assert "talk about" in modal_txt
        s.assert_no_errors()


def test_T1_14_hooks_strictly_hidden_before_reveal_in_study(env: TestEnv) -> None:
    """3-axis memory hooks are strictly hidden before reveal in Study tab."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Start study session
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        s.page.locator("#revealBtn").wait_for(state="visible")
        pre_txt = s.page.locator("#studyCardArea").inner_text()
        assert "BASE_KN_" not in pre_txt and "BASE_ET_" not in pre_txt and "BASE_MN_" not in pre_txt, (
            "3-axis hooks appeared prior to reveal in Study tab!"
        )
        s.assert_no_errors()


def test_T1_15_user_hook_edit_persists_across_reload(env: TestEnv) -> None:
    """Editing 3-axis personal hooks in Hook Workshop persists across page reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "workshop")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)
        s.page.locator("#hwInKn").wait_for(state="visible")
        s.page.locator("#hwInKn").fill("USER_CUSTOM_KN_999")
        s.page.locator("#hwInEt").fill("USER_CUSTOM_ET_999")
        s.page.locator("#hwInMn").fill("USER_CUSTOM_MN_999")
        # Wait for debounce + save
        s.page.wait_for_timeout(450)

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        st = read_local_state(s.page)
        all_user_hooks = json.dumps(st.get("userHooks", {}), ensure_ascii=False)
        assert "USER_CUSTOM_KN_999" in all_user_hooks
        assert "USER_CUSTOM_ET_999" in all_user_hooks
        assert "USER_CUSTOM_MN_999" in all_user_hooks
        s.assert_no_errors()


def test_T1_16_ai_hooks_override_base_bundle_hooks(env: TestEnv) -> None:
    """Imported AI hooks (extPack.hooks) override base bundle hooks (w.hk) when no user hook exists."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))

        switch_tab(s.page, "explorer")
        s.page.locator("#searchInput").fill("discuss")
        s.page.wait_for_timeout(150)
        s.page.locator("#wordList .word-row").first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        modal_txt = s.page.locator("#modalContent").inner_text()
        assert "AI_CO_DISCUSS" in modal_txt or "AI_KN_DISCUSS" in modal_txt, (
            f"Expected imported AI hook for discuss to override base hook; modal had: {modal_txt[:300]}"
        )
        assert "BASE_CO_DISCUSS" not in modal_txt, "Base hook should be overridden by AI hook"
        s.assert_no_errors()


# ===========================================================================
# Group D: 9 StudySapuri + 4 旧帝大 Families, Level Filter & Badges (T1-17..T1-26)
# ===========================================================================


def test_T1_17_verb_family_selector_has_all_13_canonical_families(env: TestEnv) -> None:
    """#loopVerbFamilySel offers 'all' plus all 13 canonical families (9 StudySapuri + 4 旧帝大)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        avail = get_available_verb_families(s.page)
        missing = [f for f in ["all", *CANONICAL_FAMILIES] if f not in avail]
        assert not missing, (
            f"Contract violation: missing canonical families in #loopVerbFamilySel: {missing} (available: {avail})"
        )
        s.assert_no_errors()


def test_T1_18_transitive_trap_includes_empty_pt_verbs(env: TestEnv) -> None:
    """Filtering by transitive_trap includes VT_TRAP_MAP verbs even when w.pt is empty (B4)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_target(s.page, "verb_family")
        select_verb_family(s.page, "transitive_trap")
        # synthetic_bundle has discuss (pt), approach (pt=[]), resemble (pt=[]), survive (pt=[]), reach (pt=[])
        # So filtering by transitive_trap must yield >= 4 words (not just 1!)
        card_txt = s.page.locator("#loopCardArea").inner_text()
        m = re.search(r"(\d+)\s*語", card_txt)
        assert m, f"Expected candidate count in waiting card, got: {card_txt[:200]}"
        count = int(m.group(1))
        assert count >= 4, (
            f"B4 violation: transitive_trap only matched {count} words; empty-pt VT trap verbs (approach/resemble/survive/reach) were dropped!"
        )
        s.assert_no_errors()


def test_T1_19_imperial_4_categories_filter_imported_questions(env: TestEnv) -> None:
    """Filtering by each of the 4 旧帝大 categories surfaces matching imported questions."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "verb_family")

        for fam in IMPERIAL_4_FAMILIES:
            select_verb_family(s.page, fam)
            start_loop_session(s.page)
            s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
            badge = s.page.locator("[data-testid='mcq-family-badge']")
            assert badge.count() >= 1 and badge.first.is_visible(), (
                f"Expected data-testid='mcq-family-badge' for category {fam}"
            )
            # Pause/return to waiting screen
            s.page.locator("#mcqPauseBtn").click()
        s.assert_no_errors()


def test_T1_20_loop_level_selector_contract(env: TestEnv) -> None:
    """#loopLevelSel exists and offers 'all', 'common', 'march', 'national'."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        avail = get_available_levels(s.page)
        for lvl in CANONICAL_LEVELS:
            assert lvl in avail, f"Missing level '{lvl}' in #loopLevelSel (available: {avail})"
        s.assert_no_errors()


def test_T1_21_loop_target_selector_includes_ext_cloze(env: TestEnv) -> None:
    """#loopTargetSel / target bar includes all 5 required targets including 'ext_cloze'."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        avail = get_available_loop_targets(s.page)
        missing = [t for t in CANONICAL_TARGETS if t not in avail]
        assert not missing, f"Contract violation: missing loop targets {missing} (available: {avail})"
        s.assert_no_errors()


def test_T1_22_ext_cloze_national_delivers_only_national_questions(env: TestEnv) -> None:
    """Selecting ext_cloze + national delivers strictly level==='national' MCQs including unmarked Stage 3–5 words."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        pack = load_fixture_json("synthetic_ai_pack.json")
        national_stems = {c["stem"].split("(")[0].strip()[:24] for c in pack["cloze"] if c["level"] == "national"}

        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)

        seen = 0
        for _ in range(12):
            if not s.page.locator("#mcqChoicesGrid").is_visible():
                break
            card_txt = s.page.locator("#loopCardArea").inner_text()
            lvl_badge = s.page.locator("[data-testid='mcq-level-badge']")
            assert lvl_badge.count() >= 1, "Missing data-testid='mcq-level-badge' on MCQ card"
            badge_txt = lvl_badge.first.inner_text()
            assert any(k in badge_txt for k in ("旧帝", "国立", "national", "National")), (
                f"Expected national level badge, got {badge_txt!r}"
            )
            assert any(stem_prefix in card_txt for stem_prefix in national_stems), (
                f"Non-national stem rendered under national filter: {card_txt[:180]}"
            )
            seen += 1
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").click()
        assert seen == 9, f"Expected all 9 synthetic national MCQs (incl. Stage 3-5 unmarked), got {seen}"
        s.assert_no_errors()


def test_T1_23_mcq_level_and_family_badges_render(env: TestEnv) -> None:
    """MCQ cards render both data-testid='mcq-level-badge' and data-testid='mcq-family-badge'."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "all")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        lvl_badge = s.page.locator("[data-testid='mcq-level-badge']")
        fam_badge = s.page.locator("[data-testid='mcq-family-badge']")
        assert lvl_badge.count() >= 1 and lvl_badge.first.is_visible(), "Missing mcq-level-badge"
        assert fam_badge.count() >= 1 and fam_badge.first.is_visible(), "Missing mcq-family-badge"
        assert len(lvl_badge.first.inner_text().strip()) > 0
        assert len(fam_badge.first.inner_text().strip()) > 0
        s.assert_no_errors()


def test_T1_24_vocab_confusable_and_stage5_not_misclassified_as_prep_pattern(env: TestEnv) -> None:
    """Missing a vocab_confusable or stage5_polysemy MCQ must NOT misclassify as prep_pattern (B4)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_target(s.page, "verb_family")
        select_verb_family(s.page, "vocab_confusable")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        # Deliberately choose wrong answer (in synthetic_ai_pack, answer is always index 0, so pick index 1)
        # Note: choices might be shuffled; pick a choice whose text != "reminds"
        btns = s.page.locator("#mcqChoicesGrid button[data-cidx]")
        clicked_wrong = False
        for i in range(btns.count()):
            if "reminds" not in btns.nth(i).inner_text().lower():
                btns.nth(i).click()
                clicked_wrong = True
                break
        assert clicked_wrong
        s.page.locator("#mcqNextBtn").wait_for(state="visible")
        st = read_local_state(s.page)
        tags = st.get("errTags", {}).get("SYN-S2-20", [])
        assert "prep_pattern" not in tags, (
            f"B4 violation: vocab_confusable MCQ miss was misclassified as 'prep_pattern': {tags}"
        )
        assert any(t in tags for t in ("confusable", "confusion")), (
            f"Expected confusable/confusion tag on vocab_confusable miss, got {tags}"
        )
        s.assert_no_errors()


def test_T1_25_common_and_march_level_filters(env: TestEnv) -> None:
    """Filtering by 'common' and 'march' returns exact corresponding subsets."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_target(s.page, "ext_cloze")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")

        for lvl, expected_count in (("common", 4), ("march", 5)):
            select_loop_level(s.page, lvl)
            start_loop_session(s.page)
            n = _complete_mcq_round(s.page, choice_idx=0)
            assert n == expected_count, f"Expected {expected_count} questions for level={lvl}, got {n}"
        s.assert_no_errors()


def test_T1_26_mcq_displays_why_and_trap_after_choice(env: TestEnv) -> None:
    """Answering an imported MCQ renders explanation (why) and warning trap (⚠️)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
        fb = s.page.locator("#mcqFeedbackArea")
        fb.wait_for(state="visible")
        fb_txt = fb.inner_text()
        assert "⚠️" in fb_txt, f"Expected ⚠️ trap warning in MCQ feedback, got: {fb_txt[:200]}"
        assert len(fb_txt) > 30
        s.assert_no_errors()


# ===========================================================================
# Group E: 6-Category Error Tagging & Diagnostics (T1-27..T1-30)
# ===========================================================================


def test_T1_27_six_canonical_error_tag_buttons_exist(env: TestEnv) -> None:
    """All 6 canonical error tag buttons (data-errtag=...) are present & selectable after reveal/answer."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").click()
        s.page.locator("#lfGradeOk").wait_for(state="visible")
        missing = [
            tag
            for tag in CANONICAL_ERROR_TAGS
            if s.page.locator(f"[data-errtag='{tag}']").count() == 0
        ]
        assert not missing, (
            f"Contract violation (F6): missing canonical 6-category error tag buttons: {missing}"
        )
        s.assert_no_errors()


def test_T1_28_selected_error_tags_persist_across_reload(env: TestEnv) -> None:
    """Selecting canonical error tags persists them in state across page reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").click()
        btn = s.page.locator("[data-errtag='misunderstanding']")
        assert btn.count() >= 1, "Contract violation (F6): missing [data-errtag='misunderstanding'] button"
        btn.first.click()
        s.page.locator("#lfGradeX").click()

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        st = read_local_state(s.page)
        all_tags = [t for tags in st.get("errTags", {}).values() for t in tags]
        assert "misunderstanding" in all_tags, (
            f"Expected 'misunderstanding' to persist in errTags after reload, got {st.get('errTags')}"
        )
        s.assert_no_errors()


def test_T1_29_weakness_diagnostics_and_err_reason_filter(env: TestEnv) -> None:
    """err_reason target mode filters words by selected canonical error tag."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Seed a canonical tag via localStorage
        st = read_local_state(s.page)
        st.setdefault("errTags", {})["SYN-S1-01"] = ["order_error"]
        write_local_state(s.page, st)
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")

        switch_tab(s.page, "loop")
        select_loop_target(s.page, "err_reason")
        sub = s.page.locator("#loopSubFilterArea")
        sub.wait_for(state="visible")
        # Must expose order_error filter button or option
        order_btn = sub.locator("[data-ef='order_error'], [data-errtag='order_error'], option[value='order_error']")
        assert order_btn.count() >= 1, (
            f"Contract violation (F6): canonical tag 'order_error' missing from err_reason filter UI: {sub.inner_text()[:200]}"
        )
        if order_btn.first.evaluate("el => el.tagName") == "OPTION":
            sub.locator("select").first.select_option("order_error")
        else:
            order_btn.first.click()
        card_txt = s.page.locator("#loopCardArea").inner_text()
        assert "1語" in card_txt or "1 語" in card_txt or "discuss" in card_txt, (
            f"Expected 1 matched word for order_error filter, got: {card_txt[:200]}"
        )
        s.assert_no_errors()


def test_T1_30_legacy_error_tags_remain_readable(env: TestEnv) -> None:
    """Pre-seeded legacy error tags (prep_pattern, confusable, slow, unlearned) load without crashing."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        st = read_local_state(s.page)
        st["errTags"] = {
            "SYN-S1-01": ["prep_pattern"],
            "SYN-S1-02": ["confusable"],
            "SYN-S1-03": ["slow"],
            "SYN-S1-04": ["unlearned"],
        }
        write_local_state(s.page, st)
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")

        switch_tab(s.page, "loop")
        select_loop_target(s.page, "err_reason")
        s.page.locator("#loopStartBtn").wait_for(state="visible")
        st_after = read_local_state(s.page)
        # Ensure legacy tags were preserved or cleanly migrated without data loss
        total_tagged = sum(1 for v in st_after.get("errTags", {}).values() if v)
        assert total_tagged >= 4, f"Legacy error tags lost after reload: {st_after.get('errTags')}"
        s.assert_no_errors()


# ===========================================================================
# Group F: Kioku-hakase AI Prompts & JSON Pack Import/Export (T1-31..T1-38)
# ===========================================================================


def test_T1_31_kioku_hakase_tab1_mistake_review_prompt(env: TestEnv) -> None:
    """Tab 1 (mistake_review) prompt includes 6 categories, 8 initial items, 5 post-answer items, no-leak rule & exact closing."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_ai_prompt_type(s.page, "mistake_review")
        txt = get_ai_prompt_text(s.page)
        assert CLOSING_TAB1 in txt, f"Missing exact Tab 1 canonical closing phrase: {CLOSING_TAB1}"
        for kw in ("知識不足", "理解のズレ", "読み間違い", "ケアレスミス", "混同", "順番"):
            assert kw in txt, f"Tab 1 prompt missing 6-category keyword '{kw}'"
        assert "答え" in txt and ("先出し" in txt or "非表示" in txt or "出さない" in txt), (
            "Tab 1 prompt must enforce Rule 1 (no answer leak before response)"
        )
        s.assert_no_errors()


def test_T1_32_kioku_hakase_tab3_pretest_chat_prompt(env: TestEnv) -> None:
    """Tab 3 (pretest_chat) prompt enforces 3 Qs, 10s/Q, choice+own-words mix, 6 post-answer items, 旧帝大 focus & exact closing."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_ai_prompt_type(s.page, "pretest_chat")
        txt = get_ai_prompt_text(s.page)
        assert CLOSING_TAB3 in txt, f"Missing exact Tab 3 canonical closing phrase: {CLOSING_TAB3}"
        assert "3問" in txt and "10秒" in txt, "Tab 3 prompt must specify 3 Qs and 10 seconds"
        assert "自分の言葉" in txt, "Tab 3 prompt must include own-words explanation mix (not MCQ-only)"
        assert any(k in txt for k in ("旧帝", "難関国立", "国公立")), "Tab 3 prompt must mention 旧帝大 focus"
        # Canonical 6 post-answer items (check for item 5/6 markers like 次に読むべき教材 / 次に使う質問文)
        assert "⑥" in txt or "6." in txt or "6項目" in txt or "次に使う質問" in txt, (
            "Tab 3 prompt must include all 6 post-answer items"
        )
        s.assert_no_errors()


def test_T1_33_kioku_hakase_tab5_teach_chat_prompt(env: TestEnv) -> None:
    """Tab 5 (teach_chat) prompt includes 7 initial items, 4 post-answer items & exact full canonical closing."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_ai_prompt_type(s.page, "teach_chat")
        txt = get_ai_prompt_text(s.page)
        assert CLOSING_TAB5 in txt, (
            f"Missing exact full Tab 5 canonical closing phrase:\nExpected: {CLOSING_TAB5}\nGot tail: {txt[-200:]}"
        )
        assert "⑦" in txt or "7." in txt or "確認問題" in txt, "Tab 5 prompt must include all 7 initial items"
        assert "使うべき知識" in txt or "次に直すポイント" in txt, "Tab 5 prompt must include 4 post-answer items"
        s.assert_no_errors()


def test_T1_34_json_pack_prompt_uses_canonical_schema_and_imperial_focus(env: TestEnv) -> None:
    """JSON Expansion prompt (json_pack) specifies canonical 13 families & common/march/national levels with 旧帝大 focus."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_ai_prompt_type(s.page, "json_pack")
        txt = get_ai_prompt_text(s.page)
        for fam in ("transitive_trap", "inanimate_subject", "stage5_polysemy", "stage3_usage", "composition_trap"):
            assert fam in txt, f"json_pack prompt missing canonical family '{fam}'"
        for lvl in ("common", "march", "national"):
            assert lvl in txt, f"json_pack prompt missing canonical level '{lvl}'"
        assert "標準〜難関大" not in txt, "json_pack prompt still contains deprecated freeform level '標準〜難関大'"
        assert any(k in txt for k in ("旧帝", "旧帝国大学")), "json_pack prompt missing 旧帝大 orientation"
        s.assert_no_errors()


def test_T1_35_ai_pack_file_upload_updates_badge_and_persists(env: TestEnv) -> None:
    """Importing synthetic_ai_pack.json via file upload updates badge to exact counts and persists across reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        badge = upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        hk, cl = parse_ext_badge_counts(badge)
        assert (hk, cl) == (6, 18), f"Expected 6 hooks & 18 cloze, got badge: {badge!r}"

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        switch_tab(s.page, "loop")
        badge2 = get_ext_badge_text(s.page)
        assert parse_ext_badge_counts(badge2) == (6, 18), (
            f"AI pack did not persist across reload; badge after reload: {badge2!r}"
        )
        s.assert_no_errors()


def test_T1_36_ai_pack_paste_textarea_import(env: TestEnv) -> None:
    """Pasting valid AI pack JSON into textarea merges hooks and cloze cleanly."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        raw = fixture_path("synthetic_ai_pack.json").read_text(encoding="utf-8")
        badge = paste_ai_pack(s.page, raw)
        assert parse_ext_badge_counts(badge) == (6, 18), f"Unexpected counts after paste: {badge!r}"
        s.assert_no_errors()


def test_T1_37_duplicate_reimport_deduplicates_without_inflating_counts(env: TestEnv) -> None:
    """Re-importing the same AI pack deduplicates by id/(wid, stem) without inflating counts."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        raw = fixture_path("synthetic_ai_pack.json").read_text(encoding="utf-8")
        paste_ai_pack(s.page, raw)
        badge_second = paste_ai_pack(s.page, raw)
        assert parse_ext_badge_counts(badge_second) == (6, 18), (
            f"Duplicate re-import inflated counts: {badge_second!r}"
        )
        s.assert_no_errors()


def test_T1_38_ai_pack_export_and_reset_preserves_srs(env: TestEnv) -> None:
    """Exporting and resetting AI pack clears extPack cleanly without corrupting SRS state."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Do 1 study review first to establish SRS daily progress
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        s.page.locator("#revealBtn").click()
        s.page.locator("#gradeOk").click()
        done_before = int(s.page.locator("#statDone").inner_text().strip())
        assert done_before >= 1

        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (6, 18)

        # Trigger download export
        with s.page.expect_download() as dl_info:
            s.page.locator("#aiExportExtBtn").click()
        dl_path = dl_info.value.path()
        exported = json.loads(Path(dl_path).read_text(encoding="utf-8"))
        assert len(exported.get("hooks", {})) == 6 and len(exported.get("cloze", [])) == 18

        # Reset AI pack (confirm dialog auto-accepted by harness)
        s.page.locator("#aiResetExtBtn").click()
        s.page.wait_for_timeout(200)
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (0, 0)

        # Verify SRS daily.done is intact
        switch_tab(s.page, "study")
        done_after = int(s.page.locator("#statDone").inner_text().strip())
        assert done_after == done_before, f"Resetting AI pack altered SRS done count: {done_before} -> {done_after}"
        s.assert_no_errors()


# ===========================================================================
# Group G: Existing Tabs Regression Suite & BYO Hygiene (T1-39..T1-45)
# ===========================================================================


def test_T1_39_study_tab_reveal_grade_and_undo(env: TestEnv) -> None:
    """Study tab supports reveal, SRS grading, daily counter increment, and undo."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        done0 = int(s.page.locator("#statDone").inner_text().strip())
        s.page.locator("#revealBtn").wait_for(state="visible")
        s.page.locator("#revealBtn").click()
        s.page.locator("#gradeOk").click()
        done1 = int(s.page.locator("#statDone").inner_text().strip())
        assert done1 == done0 + 1, f"Expected daily done to increment {done0}->{done0+1}, got {done1}"

        # Undo
        assert not s.page.locator("#undoBtn").is_disabled()
        s.page.locator("#undoBtn").click()
        done2 = int(s.page.locator("#statDone").inner_text().strip())
        assert done2 == done0, f"Undo should restore daily done to {done0}, got {done2}"
        s.assert_no_errors()


def test_T1_40_pattern_srs_bidirectional_trainer(env: TestEnv) -> None:
    """Pattern SRS tab (#tab-pquiz) reveals and grades both en2ja and ja2en cards."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "pquiz")
        for direction in ("en2ja", "ja2en"):
            s.page.locator(f"#pqDirBar button[data-dir='{direction}']").click()
            if s.page.locator("#pqStartBtn").is_visible():
                s.page.locator("#pqStartBtn").click()
            s.page.locator("#pqRevealBtn").wait_for(state="visible")
            s.page.locator("#pqRevealBtn").click()
            s.page.locator("#pqGOk").wait_for(state="visible")
            s.page.locator("#pqGOk").click()
            if s.page.locator("#pqPauseBtn").is_visible():
                s.page.locator("#pqPauseBtn").click()
        s.assert_no_errors()


def test_T1_41_synonyms_tab_renders_synthetic_groups(env: TestEnv) -> None:
    """Synonyms tab renders synthetic synonym groups with nuances, patterns, and search."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "synonyms")
        txt = s.page.locator("#synGroupList").inner_text()
        assert "議論・伝達系の動詞" in txt and "供給・剥奪系の動詞" in txt
        assert "discuss" in txt and "provide" in txt
        s.page.locator("#synSearch").fill("deprive")
        s.page.wait_for_timeout(150)
        filtered = s.page.locator("#synGroupList").inner_text()
        assert "供給・剥奪系の動詞" in filtered and "議論・伝達系の動詞" not in filtered
        s.assert_no_errors()


def test_T1_42_schedule_tab_stage_and_batch_breakdown(env: TestEnv) -> None:
    """Schedule tab displays 7-day forecast and stage/50-word batch breakdown."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "schedule")
        assert s.page.locator("#forecastChart").inner_text().strip() != ""
        s.page.locator("#batchStageFilter").select_option("1")
        s.page.wait_for_timeout(100)
        batch_txt = s.page.locator("#batchGrid").inner_text()
        assert "B0001-0050" in batch_txt or "1" in batch_txt
        s.assert_no_errors()


def test_T1_43_explorer_search_modal_and_wiki_markdown(env: TestEnv) -> None:
    """Explorer searches/opens word detail modal; Wiki tab generates non-empty markdown & backup JSON."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "explorer")
        s.page.locator("#searchInput").fill("prevent")
        s.page.wait_for_timeout(150)
        rows = s.page.locator("#wordList .word-row")
        assert rows.count() >= 1
        rows.first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        assert "prevent" in s.page.locator("#modalContent").inner_text()
        s.page.locator("#mClose").click()

        switch_tab(s.page, "wiki")
        md = s.page.locator("#wikiMdPreview").input_value()
        assert len(md.strip()) > 20, "Expected generated Wiki markdown summary"
        with s.page.expect_download() as dl_info:
            s.page.locator("#exportJsonBtn").click()
        backup = json.loads(Path(dl_info.value.path()).read_text(encoding="utf-8"))
        assert "cards" in backup and "version" in backup
        s.assert_no_errors()


def test_T1_44_repo_byo_hygiene_and_gitignore(env: TestEnv) -> None:
    """Public repo contains zero copyrighted/private JSON packs and .gitignore protects .agents/ & private JSONs."""
    forbidden = [
        REPO_ROOT / "systan_data.json",
        REPO_ROOT / "ext_hooks.json",
        REPO_ROOT / "ext_cloze.json",
        REPO_ROOT / "systan_ai_pack.json",
    ]
    for f in forbidden:
        assert not f.exists(), f"BYO violation: private data file present in repo root: {f}"
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), "Contract/F15 violation: .gitignore is missing from repo root"
    gi_txt = gitignore.read_text(encoding="utf-8")
    assert ".agents" in gi_txt, ".gitignore must ignore .agents/"
    assert any(pat in gi_txt for pat in ("systan_data.json", "systan_ai_pack.json", "*.json", "ext_*.json")), (
        ".gitignore must ignore private JSON data packs"
    )


def test_T1_45_theme_toggle_persists_across_reload(env: TestEnv) -> None:
    """Toggling light/dark theme updates data-theme attribute and persists across reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        before = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        s.page.locator("#themeBtn").click()
        after = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        assert after != before, f"Theme did not change on #themeBtn click: {before} -> {after}"
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain", state="visible")
        reloaded = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        assert reloaded == after, f"Theme did not persist across reload: expected {after}, got {reloaded}"
        s.assert_no_errors()


TESTS: list[tuple[str, Callable[[TestEnv], None]]] = [
    ("T1-01", test_T1_01_onboarding_empty_state_byo),
    ("T1-02", test_T1_02_byo_bundle_upload_boots_app),
    ("T1-03", test_T1_03_bundle_persists_across_reload),
    ("T1-04", test_T1_04_service_worker_registers_cleanly),
    ("T1-05", test_T1_05_spiral_round1_hides_answer_and_hooks_before_reveal),
    ("T1-06", test_T1_06_spiral_completes_all_4_rounds_to_summary),
    ("T1-07", test_T1_07_single_focus_en2ja_and_ja2en),
    ("T1-08", test_T1_08_single_focus_mcq_and_workshop),
    ("T1-09", test_T1_09_recall_timer_measures_positive_latency),
    ("T1-10", test_T1_10_timer_off_allows_fast_clear_and_skips_round2_without_fake_ms),
    ("T1-11", test_T1_11_custom_latency_threshold_modal_persists),
    ("T1-12", test_T1_12_recall_automaticity_slow_classification),
    ("T1-13", test_T1_13_revealed_card_shows_all_3_hook_axes),
    ("T1-14", test_T1_14_hooks_strictly_hidden_before_reveal_in_study),
    ("T1-15", test_T1_15_user_hook_edit_persists_across_reload),
    ("T1-16", test_T1_16_ai_hooks_override_base_bundle_hooks),
    ("T1-17", test_T1_17_verb_family_selector_has_all_13_canonical_families),
    ("T1-18", test_T1_18_transitive_trap_includes_empty_pt_verbs),
    ("T1-19", test_T1_19_imperial_4_categories_filter_imported_questions),
    ("T1-20", test_T1_20_loop_level_selector_contract),
    ("T1-21", test_T1_21_loop_target_selector_includes_ext_cloze),
    ("T1-22", test_T1_22_ext_cloze_national_delivers_only_national_questions),
    ("T1-23", test_T1_23_mcq_level_and_family_badges_render),
    ("T1-24", test_T1_24_vocab_confusable_and_stage5_not_misclassified_as_prep_pattern),
    ("T1-25", test_T1_25_common_and_march_level_filters),
    ("T1-26", test_T1_26_mcq_displays_why_and_trap_after_choice),
    ("T1-27", test_T1_27_six_canonical_error_tag_buttons_exist),
    ("T1-28", test_T1_28_selected_error_tags_persist_across_reload),
    ("T1-29", test_T1_29_weakness_diagnostics_and_err_reason_filter),
    ("T1-30", test_T1_30_legacy_error_tags_remain_readable),
    ("T1-31", test_T1_31_kioku_hakase_tab1_mistake_review_prompt),
    ("T1-32", test_T1_32_kioku_hakase_tab3_pretest_chat_prompt),
    ("T1-33", test_T1_33_kioku_hakase_tab5_teach_chat_prompt),
    ("T1-34", test_T1_34_json_pack_prompt_uses_canonical_schema_and_imperial_focus),
    ("T1-35", test_T1_35_ai_pack_file_upload_updates_badge_and_persists),
    ("T1-36", test_T1_36_ai_pack_paste_textarea_import),
    ("T1-37", test_T1_37_duplicate_reimport_deduplicates_without_inflating_counts),
    ("T1-38", test_T1_38_ai_pack_export_and_reset_preserves_srs),
    ("T1-39", test_T1_39_study_tab_reveal_grade_and_undo),
    ("T1-40", test_T1_40_pattern_srs_bidirectional_trainer),
    ("T1-41", test_T1_41_synonyms_tab_renders_synthetic_groups),
    ("T1-42", test_T1_42_schedule_tab_stage_and_batch_breakdown),
    ("T1-43", test_T1_43_explorer_search_modal_and_wiki_markdown),
    ("T1-44", test_T1_44_repo_byo_hygiene_and_gitignore),
    ("T1-45", test_T1_45_theme_toggle_persists_across_reload),
]
