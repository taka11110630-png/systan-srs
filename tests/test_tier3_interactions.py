"""Tier 3: Cross-Feature Pairwise Interactions (10 tests T3-01..T3-10)."""

from __future__ import annotations

import json
from typing import Callable

from harness import (
    CLOSING_TAB1,
    TestEnv,
    boot_with_synthetic,
    fixture_path,
    get_ai_prompt_text,
    get_ext_badge_text,
    load_fixture_json,
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
    upload_ai_pack,
)


def test_T3_01_level_times_family_filter_and_interleaving(env: TestEnv) -> None:
    """Level Filter (national) x Family Filter (inanimate_subject vs all) delivers exact subsets and interleaves."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))

        # Pair 1: ext_cloze + national + all families -> 9 questions spanning multiple families
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)
        fam_badges = []
        for _ in range(12):
            if not s.page.locator("#mcqChoicesGrid").is_visible():
                break
            b = s.page.locator("[data-testid='mcq-family-badge']")
            assert b.count() >= 1, "Missing data-testid='mcq-family-badge'"
            fam_badges.append(b.first.inner_text().strip())
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").click()
        assert len(fam_badges) == 9, f"Expected 9 national MCQs, got {len(fam_badges)}"
        assert len(set(fam_badges)) >= 4, f"Expected interleaved questions across >=4 families, got {fam_badges}"

        # Pair 2: verb_family (inanimate_subject) + national -> strictly inanimate_subject (2 questions in fixture)
        select_loop_target(s.page, "verb_family")
        select_verb_family(s.page, "inanimate_subject")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        start_loop_session(s.page)
        seen = 0
        for _ in range(5):
            if not s.page.locator("#mcqChoicesGrid").is_visible():
                break
            card_txt = s.page.locator("#loopCardArea").inner_text()
            assert "telemetry" in card_txt or "blackouts" in card_txt, (
                f"Expected inanimate_subject national stem, got: {card_txt[:180]}"
            )
            seen += 1
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").click()
        assert seen == 2, f"Expected 2 inanimate_subject national questions, got {seen}"
        s.assert_no_errors()


def test_T3_02_timer_off_times_4step_spiral_skips_round2_to_round3_and_4(env: TestEnv) -> None:
    """Timer-OFF x 4-Step Spiral: all-OK Round 1 skips Round 2 Workshop and completes Round 3 & 4 cleanly (B1)."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "spiral")
        select_loop_size(s.page, 10)
        chk = s.page.locator("#loopTimerChk")
        if chk.is_checked():
            chk.uncheck()
        start_loop_session(s.page)

        # Round 1: ace all cards with OK
        for _ in range(15):
            if s.page.locator("#lfRevealBtn").is_visible():
                s.page.locator("#lfRevealBtn").click()
                s.page.locator("#lfGradeOk").click()
                s.page.wait_for_timeout(30)
            else:
                break

        # Round 2 must NOT open #hwInKn workshop editor; must show #r2SkipBtn or go straight to Round 3
        assert not s.page.locator("#hwInKn").is_visible(), (
            "B1 violation: Timer-OFF all-OK Round 1 opened Hook Workshop instead of skipping Round 2!"
        )
        if s.page.locator("#r2SkipBtn").is_visible():
            s.page.locator("#r2SkipBtn").click()

        # Round 3: ja2en
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        for _ in range(15):
            if s.page.locator("#lfRevealBtn").is_visible():
                s.page.locator("#lfRevealBtn").click()
                s.page.locator("#lfGradeOk").click()
                s.page.wait_for_timeout(30)
            else:
                break

        # Round 4: mcq
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        for _ in range(15):
            if s.page.locator("#mcqChoicesGrid").is_visible():
                s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
                s.page.locator("#mcqNextBtn").click()
                s.page.wait_for_timeout(30)
            else:
                break

        s.page.locator("#sumNextSetBtn, #loopRestartBtn").first.wait_for(state="visible")
        st = read_local_state(s.page)
        lat_entries = [e for logs in st.get("latLog", {}).values() for e in logs]
        assert len(lat_entries) == 0, f"B1 violation: Timer-OFF recorded fake latencies: {lat_entries[:3]}"
        s.assert_no_errors()


def test_T3_03_error_tagging_flows_into_diagnostics_and_tab1_prompt(env: TestEnv) -> None:
    """6-Category Error Tagging x Weakness Diagnostics x Tab 1 AI Mistake Review Prompt."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")
        s.page.locator("#loopRangeFrom").fill("1")
        s.page.locator("#loopRangeTo").fill("1")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)

        s.page.locator("#lfRevealBtn").click()
        tag_btn = s.page.locator("[data-errtag='misunderstanding']")
        assert tag_btn.count() >= 1, "Contract violation (F6): missing [data-errtag='misunderstanding']"
        tag_btn.first.click()
        s.page.locator("#lfGradeX").click()

        # Generate Tab 1 Mistake Review prompt and confirm the tagged word & error reason flow into it
        select_ai_prompt_type(s.page, "mistake_review")
        prompt_txt = get_ai_prompt_text(s.page)
        assert CLOSING_TAB1 in prompt_txt, "Missing Tab 1 canonical closing phrase"
        assert "discuss" in prompt_txt, "Tagged weak word 'discuss' did not flow into Tab 1 prompt"
        assert "理解のズレ" in prompt_txt or "misunderstanding" in prompt_txt, (
            "Selected error category 'misunderstanding'/'理解のズレ' did not flow into Tab 1 prompt"
        )
        s.assert_no_errors()


def test_T3_04_hook_precedence_user_over_ai_over_base(env: TestEnv) -> None:
    """Precedence Chain: userHooks > extPack.hooks > w.hk across Explorer Modal, Study, and Loop."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)

        # 1. Initially base w.hk is shown for 'discuss'
        switch_tab(s.page, "explorer")
        s.page.locator("#searchInput").fill("discuss")
        s.page.wait_for_timeout(120)
        s.page.locator("#wordList .word-row").first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        assert "BASE_KN_DISCUSS" in s.page.locator("#modalContent").inner_text() or "BASE_KN_DISCUSS" in s.page.locator("#mHkKn").input_value()
        s.page.locator("#mClose").click()

        # 2. Import AI pack -> AI hook overrides base w.hk
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        switch_tab(s.page, "explorer")
        s.page.locator("#wordList .word-row").first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        m_txt_ai = s.page.locator("#modalContent").inner_text()
        assert "AI_KN_DISCUSS" in m_txt_ai or "AI_CO_DISCUSS" in m_txt_ai, (
            f"AI hook failed to override base hook: {m_txt_ai[:250]}"
        )

        # 3. Edit userHook in modal -> userHook overrides AI hook everywhere
        s.page.locator("#mHkKn").fill("USER_OVERRIDE_KN_DISCUSS")
        s.page.locator("#mSave").click()
        s.page.wait_for_timeout(150)

        # Verify in Explorer modal
        s.page.locator("#wordList .word-row").first.click()
        s.page.locator("#modalBackdrop.open").wait_for(state="visible")
        assert s.page.locator("#mHkKn").input_value() == "USER_OVERRIDE_KN_DISCUSS"
        s.page.locator("#mClose").click()

        # Verify in Loop reveal for discuss (#1)
        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")
        s.page.locator("#loopRangeFrom").fill("1")
        s.page.locator("#loopRangeTo").fill("1")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").click()
        loop_txt = s.page.locator("#loopCardArea").inner_text()
        assert "USER_OVERRIDE_KN_DISCUSS" in loop_txt, (
            f"userHooks did not override AI hook in Loop card: {loop_txt[:250]}"
        )
        s.assert_no_errors()


def test_T3_05_bundle_reload_preserves_extpack_and_srs_state(env: TestEnv) -> None:
    """Reloading bundle via #reloadBundleInput preserves existing extPack and SRS progress."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Complete 1 Study card
        if s.page.locator("#startSessionBtn").is_visible():
            s.page.locator("#startSessionBtn").click()
        s.page.locator("#revealBtn").click()
        s.page.locator("#gradeOk").click()
        done_before = int(s.page.locator("#statDone").inner_text().strip())

        # Import AI pack
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (6, 18)

        # Reload bundle via Wiki tab
        switch_tab(s.page, "wiki")
        s.page.locator("#reloadBundleInput").set_input_files(str(fixture_path("synthetic_bundle.json")))
        s.page.wait_for_timeout(300)

        # Verify SRS daily.done and AI pack counts survived
        switch_tab(s.page, "study")
        done_after = int(s.page.locator("#statDone").inner_text().strip())
        assert done_after == done_before, f"SRS progress lost on bundle reload: {done_before} -> {done_after}"
        switch_tab(s.page, "loop")
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (6, 18), (
            "AI pack lost on bundle reload"
        )
        s.assert_no_errors()


def test_T3_06_auto_audio_checkbox_controls_ja2en_speech(env: TestEnv) -> None:
    """#autoAudioChk unchecked MUST NOT call speechSynthesis.speak on ja2en reveal; checked DOES (B10)."""
    speech_spy = """
    (() => {
        window.__spokenCalls = [];
        const fakeSynth = {
            cancel: () => {},
            speak: (u) => { window.__spokenCalls.push(u && u.text ? String(u.text) : String(u)); },
            getVoices: () => []
        };
        try {
            Object.defineProperty(window, 'speechSynthesis', { value: fakeSynth, configurable: true });
        } catch (e) {}
    })();
    """
    with env.new_session(init_script=speech_spy) as s:
        boot_with_synthetic(s.page, s.base_url)
        # Ensure #autoAudioChk is unchecked
        chk = s.page.locator("#autoAudioChk")
        if chk.is_checked():
            chk.uncheck()
        assert not chk.is_checked()

        switch_tab(s.page, "loop")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "ja2en")
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.evaluate("() => { window.__spokenCalls = []; }")
        s.page.locator("#lfRevealBtn").click()
        s.page.wait_for_timeout(120)
        calls_off = s.page.evaluate("() => window.__spokenCalls")
        assert len(calls_off) == 0, (
            f"B10 violation: ja2en reveal called speechSynthesis.speak even though #autoAudioChk was unchecked: {calls_off}"
        )

        # Now check #autoAudioChk and verify reveal DOES call speak
        switch_tab(s.page, "study")
        s.page.locator("#autoAudioChk").check()
        switch_tab(s.page, "loop")
        if s.page.locator("#loopStartBtn").is_visible():
            start_loop_session(s.page)
        if s.page.locator("#lfGradeOk").is_visible():
            s.page.locator("#lfGradeOk").click()
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.evaluate("() => { window.__spokenCalls = []; }")
        s.page.locator("#lfRevealBtn").click()
        s.page.wait_for_timeout(120)
        calls_on = s.page.evaluate("() => window.__spokenCalls")
        assert len(calls_on) >= 1, (
            "Expected speechSynthesis.speak to be called on ja2en reveal when #autoAudioChk is checked"
        )
        s.assert_no_errors()


def test_T3_07_duplicate_upsert_updates_why_and_level_without_inflation(env: TestEnv) -> None:
    """Re-importing an existing cloze ID updates why & level without inflating counts."""
    edges = load_fixture_json("edge_ai_packs.json")
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))
        assert parse_ext_badge_counts(get_ext_badge_text(s.page)) == (6, 18)

        # Upsert SYN-Q-01 (previously level='common') -> level='national', updated why
        badge = paste_ai_pack(s.page, json.dumps(edges["duplicate_update_pack"], ensure_ascii=False))
        assert parse_ext_badge_counts(badge) == (6, 18), (
            f"Upsert inflated counts instead of updating in place: {badge!r}"
        )

        # Verify SYN-Q-01 now appears under national filter with updated why!
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_size(s.page, 20)
        start_loop_session(s.page)
        found_updated = False
        for _ in range(15):
            if not s.page.locator("#mcqChoicesGrid").is_visible():
                break
            if "harbor budget" in s.page.locator("#loopCardArea").inner_text():
                s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
                fb = s.page.locator("#mcqFeedbackArea").inner_text()
                assert "UPDATED_WHY_SYN_Q01" in fb, f"Upserted 'why' did not update: {fb[:200]}"
                found_updated = True
                break
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").click()
        assert found_updated, "Upserted SYN-Q-01 did not move to level='national' filter pool"
        s.assert_no_errors()


def test_T3_08_legacy_family_aliases_normalize_to_canonical_filters(env: TestEnv) -> None:
    """Legacy family aliases (vt_trap, svoo_to, writing_trap) match canonical filters (transitive_trap, svoo_vs_to, composition_trap)."""
    edges = load_fixture_json("edge_ai_packs.json")
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        badge = paste_ai_pack(s.page, json.dumps(edges["legacy_alias_pack"], ensure_ascii=False))
        assert parse_ext_badge_counts(badge) == (0, 3)

        select_loop_target(s.page, "verb_family")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")

        for canonical, stem_hint in (
            ("transitive_trap", "coastal drainage blueprint"),
            ("svoo_vs_to", "calibration chart"),
            ("composition_trap", "cooling vents"),
        ):
            select_verb_family(s.page, canonical)
            start_loop_session(s.page)
            s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
            found = False
            for _ in range(12):
                if not s.page.locator("#mcqChoicesGrid").is_visible():
                    break
                if stem_hint in s.page.locator("#loopCardArea").inner_text():
                    found = True
                    break
                s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
                s.page.locator("#mcqNextBtn").click()
            assert found, (
                f"Legacy alias item ({stem_hint!r}) did not surface under canonical family filter '{canonical}'"
            )
            if s.page.locator("#mcqPauseBtn").is_visible():
                s.page.locator("#mcqPauseBtn").click()
        s.assert_no_errors()


def test_T3_09_custom_thresholds_slow_detection_downgrades_srs_ok_to_tri(env: TestEnv) -> None:
    """Exceeding custom pass threshold downgrades 'ok' to 'tri' in SRS and adds 'slow' tag."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        s.page.locator("#loopThresholdBtn").click()
        s.page.locator("#thEnFast").fill("0.1")
        s.page.locator("#thEnPass").fill("0.2")
        s.page.locator("#thSaveBtn").click()

        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_target(s.page, "stage_batch")
        s.page.locator("#loopStageSel").select_option("1")
        s.page.locator("#loopRangeFrom").fill("1")
        s.page.locator("#loopRangeTo").fill("1")
        s.page.locator("#loopApplyRangeBtn").click()
        start_loop_session(s.page)
        s.page.locator("#lfRevealBtn").wait_for(state="visible")
        s.page.wait_for_timeout(320)
        s.page.locator("#lfRevealBtn").click()
        # Learner clicks OK, but elapsed > 0.2s pass threshold -> downgraded to tri + slow tag
        s.page.locator("#lfGradeOk").click()

        st = read_local_state(s.page)
        card = st.get("cards", {}).get("SYN-S1-01", {})
        tags = st.get("errTags", {}).get("SYN-S1-01", [])
        assert "slow" in tags, f"Expected 'slow' tag on SYN-S1-01, got {tags}"
        assert card.get("lastGrade") == "tri" or card.get("status") == "tri" or card.get("triCount", 0) >= 1 or card.get("interval", 99) <= 1, (
            f"Expected slow OK to downgrade SRS grade to tri, got card={card}"
        )
        s.assert_no_errors()


def test_T3_10_unmarked_stage3_stage5_words_drillable_via_ext_cloze_national(env: TestEnv) -> None:
    """Stage 3 & Stage 5 unmarked words (mk==='') are directly drillable via ext_cloze + national."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))

        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_size(s.page, 20)
        start_loop_session(s.page)

        seen_stems = []
        for _ in range(12):
            if not s.page.locator("#mcqChoicesGrid").is_visible():
                break
            seen_stems.append(s.page.locator("#loopCardArea").inner_text())
            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").click()

        joined = "\n".join(seen_stems)
        # SYN-S3-23 compel (Stage 3, mk='') & SYN-S5-31 yield (Stage 5, mk='') must both appear!
        assert "winter blackouts" in joined, "Unmarked Stage 3 word (compel) was not surfaced via ext_cloze + national"
        assert "glacier" in joined, "Unmarked Stage 5 word (yield) was not surfaced via ext_cloze + national"
        s.assert_no_errors()


TESTS: list[tuple[str, Callable[[TestEnv], None]]] = [
    ("T3-01", test_T3_01_level_times_family_filter_and_interleaving),
    ("T3-02", test_T3_02_timer_off_times_4step_spiral_skips_round2_to_round3_and_4),
    ("T3-03", test_T3_03_error_tagging_flows_into_diagnostics_and_tab1_prompt),
    ("T3-04", test_T3_04_hook_precedence_user_over_ai_over_base),
    ("T3-05", test_T3_05_bundle_reload_preserves_extpack_and_srs_state),
    ("T3-06", test_T3_06_auto_audio_checkbox_controls_ja2en_speech),
    ("T3-07", test_T3_07_duplicate_upsert_updates_why_and_level_without_inflation),
    ("T3-08", test_T3_08_legacy_family_aliases_normalize_to_canonical_filters),
    ("T3-09", test_T3_09_custom_thresholds_slow_detection_downgrades_srs_ok_to_tri),
    ("T3-10", test_T3_10_unmarked_stage3_stage5_words_drillable_via_ext_cloze_national),
]
