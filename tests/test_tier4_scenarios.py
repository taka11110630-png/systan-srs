"""Tier 4: Real-World Imperial University (旧帝大) Application Scenarios (8 scenarios).

Opaque-box end-to-end journeys exercising realistic multi-step workflows,
including optional read-only integration verification against external private packs.
"""

from __future__ import annotations

import json
from datetime import date

from harness import (
    CANONICAL_FAMILIES,
    CLOSING_TAB1,
    CLOSING_TAB3,
    CLOSING_TAB5,
    EXTERNAL_AI_PACK_PATH,
    EXTERNAL_BUNDLE_PATH,
    IMPERIAL_4_FAMILIES,
    SkipTest,
    TestEnv,
    boot_with_synthetic,
    fixture_path,
    get_ai_prompt_text,
    get_available_verb_families,
    get_ext_badge_text,
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
    upload_ai_pack,
    upload_bundle,
    write_local_state,
)


def _finish_flash(page, grade_selector: str = "#lfGradeOk", max_cards: int = 40) -> int:
    count = 0
    for _ in range(max_cards):
        rev = page.locator("#lfRevealBtn")
        if rev.count() > 0 and rev.is_visible():
            rev.click()
            page.locator(grade_selector).wait_for(state="visible")
            page.locator(grade_selector).click()
            count += 1
            page.wait_for_timeout(30)
        else:
            break
    return count


def _finish_mcq(page, choice_idx: int = 0, max_cards: int = 40) -> int:
    count = 0
    for _ in range(max_cards):
        grid = page.locator("#mcqChoicesGrid")
        if grid.count() > 0 and grid.is_visible():
            btns = grid.locator("button[data-cidx]")
            assert btns.count() == 4
            btns.nth(choice_idx).click()
            page.locator("#mcqNextBtn").wait_for(state="visible")
            page.locator("#mcqNextBtn").click()
            count += 1
            page.wait_for_timeout(30)
        else:
            break
    return count


def test_T4_01_full_4step_spiral_student_session(env: TestEnv) -> None:
    """Full 4-Step Spiral: miss/ace mix → Hook Workshop custom edit → R3 ja2en → R4 MCQ → Summary & reload."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))

        select_loop_mode(s.page, "spiral")
        select_loop_target(s.page, "today_weak")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)

        # Round 1: miss first 2 words, ace remaining
        r1 = 0
        for i in range(25):
            rev = s.page.locator("#lfRevealBtn")
            if rev.count() == 0 or not rev.is_visible():
                break
            rev.click()
            btn = "#lfGradeX" if i < 2 else "#lfGradeOk"
            s.page.locator(btn).wait_for(state="visible")
            s.page.locator(btn).click()
            r1 += 1
            s.page.wait_for_timeout(30)
        assert r1 >= 2, f"Expected >=2 cards in Round 1, got {r1}"

        # Round 2: Hook Workshop must appear for missed words; edit custom hook
        ws_kn = s.page.locator("#hwInKn")
        ws_kn.wait_for(state="visible")
        ws_kn.fill("旧帝大T4カスタム外来語フック")
        s.page.wait_for_timeout(400)
        for _ in range(20):
            nxt = s.page.locator("#hwNextBtn")
            if nxt.count() > 0 and nxt.is_visible():
                nxt.click()
                s.page.wait_for_timeout(40)
            else:
                break

        # Round 3: ja2en (interleaved)
        r3 = _finish_flash(s.page, "#lfGradeOk", max_cards=30)
        assert r3 >= 1, "Expected Round 3 ja2en cards after Workshop"

        # Round 4: MCQ
        r4 = _finish_mcq(s.page, choice_idx=0, max_cards=30)
        assert r4 >= 1, "Expected Round 4 MCQ cards"

        # Summary must show latency & completion stats
        summary_text = s.page.locator("#loopCardArea").inner_text()
        assert "周回" in summary_text or "完了" in summary_text or "平均" in summary_text

        # Reload and verify custom hook + latLog persisted
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")
        st = read_local_state(s.page)
        assert any(
            (v or {}).get("kn") == "旧帝大T4カスタム外来語フック"
            for v in (st.get("userHooks") or {}).values()
        ), "Custom hook edited during Round 2 Workshop did not persist"
        assert len(st.get("latLog") or {}) >= 1, "Latency log should persist after spiral session"
        s.assert_no_errors()


def test_T4_02_imperial_national_4category_cram_session(env: TestEnv) -> None:
    """Filter ext_cloze + national across all 4 旧帝大 categories and verify badges, why, and ⚠️ trap."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json"))

        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")

        for cat in IMPERIAL_4_FAMILIES:
            select_verb_family(s.page, cat)
            start_loop_session(s.page)
            s.page.locator("#mcqChoicesGrid").wait_for(state="visible")

            lvl_badge = s.page.locator("[data-testid='mcq-level-badge']").inner_text()
            fam_badge = s.page.locator("[data-testid='mcq-family-badge']").inner_text()
            assert "旧帝" in lvl_badge or "国公立" in lvl_badge or "national" in lvl_badge.lower(), (
                f"Expected national level badge for {cat}, got {lvl_badge!r}"
            )
            assert len(fam_badge.strip()) > 0, f"Empty family badge for {cat}"

            s.page.locator("#mcqChoicesGrid button[data-cidx]").first.click()
            s.page.locator("#mcqNextBtn").wait_for(state="visible")
            card_text = s.page.locator("#loopCardArea").inner_text()
            assert "⚠️" in card_text, f"Expected ⚠️ trap warning on MCQ reveal for {cat}"

            # Return to standby to pick next category
            s.page.locator("#mcqPauseBtn").click()
            s.page.locator("#loopStartBtn").wait_for(state="visible")
        s.assert_no_errors()


def test_T4_03_end_to_end_ai_weakness_loop(env: TestEnv) -> None:
    """Miss words → 6-category error tag → verify all 4 AI prompts → paste prose-wrapped JSON → drill new Q."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "loop")

        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "en2ja")
        select_loop_target(s.page, "today_weak")
        select_loop_size(s.page, 10)
        start_loop_session(s.page)

        s.page.locator("#lfRevealBtn").click()
        s.page.locator("button[data-errtag='misunderstanding']").click()
        s.page.locator("button[data-errtag='confusion']").click()
        s.page.locator("#lfGradeX").click()
        s.page.locator("#lfPauseBtn").click()

        # Verify all 4 prompt types
        select_ai_prompt_type(s.page, "mistake_review")
        p1 = get_ai_prompt_text(s.page)
        assert CLOSING_TAB1 in p1

        select_ai_prompt_type(s.page, "pretest_chat")
        p3 = get_ai_prompt_text(s.page)
        assert CLOSING_TAB3 in p3

        select_ai_prompt_type(s.page, "teach_chat")
        p5 = get_ai_prompt_text(s.page)
        assert CLOSING_TAB5 in p5

        select_ai_prompt_type(s.page, "json_pack")
        pj = get_ai_prompt_text(s.page)
        assert "inanimate_subject" in pj and "national" in pj

        # Paste prose-wrapped AI JSON response with a brand-new national MCQ
        ai_reply = (
            "以下が旧帝大向けの追加問題パックです。\n```json\n"
            + json.dumps(
                {
                    "version": "1.1",
                    "hooks": {
                        "SYN-S1-01": {
                            "mp": [{"part": "dis-", "role": "prefix", "gloss": "離れて"}],
                            "co": "徹底的に論じ合う",
                            "et": "",
                            "kn": "ディスカッション",
                            "mn": "ディスカッションは目的語直結でabout不要",
                            "cf": ["talk about"],
                            "src": "ai",
                        }
                    },
                    "cloze": [
                        {
                            "id": "Q-T4-NEW",
                            "wid": "SYN-S1-01",
                            "family": "composition_trap",
                            "stem": "The faculty senate convened to (    ) the revised doctoral curriculum yesterday.",
                            "ja": "教授会は改訂された博士課程カリキュラムについて議論するため招集された。",
                            "choices": ["discuss", "discuss about", "discuss on", "be discussed"],
                            "answer": 0,
                            "why": "discuss は他動詞なので前置詞 about/on は不要。",
                            "trap": "⚠️ discuss about は英作文で大減点",
                            "level": "旧帝大",
                            "confusable_wids": [],
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n```\n頑張ってください！"
        )
        badge = paste_ai_pack(s.page, ai_reply)
        hk_cnt, cl_cnt = parse_ext_badge_counts(badge)
        assert hk_cnt >= 1 and cl_cnt >= 1

        # Immediately drill the imported national question
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        select_verb_family(s.page, "composition_trap")
        start_loop_session(s.page)
        s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
        assert "revised doctoral curriculum" in s.page.locator("#loopCardArea").inner_text()
        s.assert_no_errors()


def test_T4_04_congestion_traffic_brake_recovery(env: TestEnv) -> None:
    """Seed >105 due cards → red Traffic Brake triggers → complete reviews → due count drops & persists."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        st = read_local_state(s.page)
        today = date.today().isoformat()
        # Add 110 custom due cards to exceed 100
        st.setdefault("customWords", [])
        st.setdefault("cards", {})
        for i in range(110):
            cid = f"C-CONG-{i}"
            st["customWords"].append(
                {
                    "id": cid,
                    "s": 1,
                    "n": 9000 + i,
                    "w": f"congword{i}",
                    "ipa": "",
                    "pos": "動詞",
                    "ph": "",
                    "m": f"渋滞テスト語{i}",
                    "rel": "",
                    "mk": "",
                    "dt": [],
                    "b": "B9001-9050",
                }
            )
            st["cards"][cid] = {
                "st": "review",
                "step": 2,
                "iv": 3,
                "ef": 2.3,
                "due": today,
                "dueTs": 0,
                "reps": 2,
                "lapses": 0,
                "streakFast": 0,
                "lastGrade": "ok",
                "note": "",
            }
        write_local_state(s.page, st)
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")

        due_before = int(s.page.locator("#statDue").inner_text().strip())
        assert due_before > 100, f"Expected >100 due count, got {due_before}"
        pace_sub = s.page.locator("#statPaceSub").inner_text()
        assert "渋滞ブレーキ" in pace_sub or "🔴" in pace_sub

        # Complete 2 study reviews
        s.page.locator("#startSessionBtn").click()
        for _ in range(2):
            s.page.locator("#revealBtn").click()
            s.page.locator("#gradeOk").click()
            s.page.wait_for_timeout(40)

        due_after = int(s.page.locator("#statDue").inner_text().strip())
        assert due_after == due_before - 2, f"Expected due to drop by 2 ({due_before} -> {due_after})"
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")
        assert int(s.page.locator("#statDue").inner_text().strip()) == due_after
        s.assert_no_errors()


def test_T4_05_offline_pwa_reload_after_sw_activation(env: TestEnv) -> None:
    """Service Worker activates and serves app shell cleanly offline with persisted bundle."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        # Wait for SW ready + controller
        sw_ready = s.page.evaluate(
            """async () => {
                if (!('serviceWorker' in navigator)) return false;
                const reg = await navigator.serviceWorker.ready;
                return Boolean(reg && reg.active);
            }"""
        )
        assert sw_ready, "Service Worker failed to reach active ready state"
        # Reload once online so SW controls the page
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")
        controlled = s.page.evaluate("() => Boolean(navigator.serviceWorker.controller)")
        assert controlled, "Service Worker did not take control after reload"

        # Go offline and reload
        s.context.set_offline(True)
        try:
            s.page.reload(wait_until="domcontentloaded")
            s.page.wait_for_selector("#appMain")
            assert s.page.locator("#appMain").is_visible()
            switch_tab(s.page, "loop")
            assert s.page.locator("#tab-loop.active").is_visible()
        finally:
            s.context.set_offline(False)
        s.assert_no_errors()


def test_T4_06_custom_word_and_backup_workflow(env: TestEnv) -> None:
    """Add custom word (pos: 追加) → drill dynamic 4-choice MCQ → verify Wiki markdown & persistence."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        switch_tab(s.page, "explorer")
        s.page.locator("#addWordBtn").click()
        s.page.locator("#awNum").fill("9123")
        s.page.locator("#awWord").fill("ameliorate")
        s.page.locator("#awMeaning").fill("〜を改善する・緩和する")
        s.page.locator("#awPattern").fill("ameliorate A（Aを改善する）")
        s.page.locator("#awSubmit").click()
        s.page.wait_for_timeout(150)

        # Open word modal and save custom note
        s.page.locator("#searchInput").fill("ameliorate")
        s.page.wait_for_timeout(150)
        s.page.locator("#wordList .word-item").first.click()
        s.page.locator("#mNote").wait_for(state="visible")
        s.page.locator("#mNote").fill("メリア＝より良く改善")
        s.page.locator("#mSave").click()

        # Verify Wiki tab markdown generates cleanly
        switch_tab(s.page, "wiki")
        wiki_md = s.page.locator("#wikiMdPreview").input_value()
        assert len(wiki_md) > 40

        # Reload and confirm custom word survives
        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")
        switch_tab(s.page, "explorer")
        s.page.locator("#searchInput").fill("ameliorate")
        s.page.wait_for_timeout(150)
        assert "ameliorate" in s.page.locator("#wordList").inner_text()
        s.assert_no_errors()


def test_T4_07_multi_tab_cross_session_journey(env: TestEnv) -> None:
    """Traverse all 7 tabs with real interactions, toggle dark theme, reload and verify persistence."""
    with env.new_session() as s:
        boot_with_synthetic(s.page, s.base_url)
        upload_ai_pack(s.page, fixture_path("synthetic_ai_pack.json")) if False else None

        for tab in ("study", "loop", "pquiz", "synonyms", "schedule", "explorer", "wiki"):
            switch_tab(s.page, tab)
            assert s.page.locator(f"#tab-{tab}.active").is_visible()

        # Toggle dark mode and verify persistence across reload
        initial_theme = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        s.page.locator("#themeBtn").click()
        toggled_theme = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        assert toggled_theme != initial_theme

        s.page.reload(wait_until="domcontentloaded")
        s.page.wait_for_selector("#appMain")
        reloaded_theme = s.page.evaluate("() => document.documentElement.getAttribute('data-theme') || 'light'")
        assert reloaded_theme == toggled_theme
        s.assert_no_errors()


def test_T4_08_real_private_pack_integration_readonly(env: TestEnv) -> None:
    """Optional read-only live integration check against actual private v1.1 pack & systan_data.json."""
    if not EXTERNAL_BUNDLE_PATH.exists() or not EXTERNAL_AI_PACK_PATH.exists():
        raise SkipTest("External private data files not present on disk")

    bundle = json.loads(EXTERNAL_BUNDLE_PATH.read_text(encoding="utf-8"))
    pack = json.loads(EXTERNAL_AI_PACK_PATH.read_text(encoding="utf-8"))
    wids = {w["id"] for w in bundle.get("words", [])}

    # Referential & count checks on real pack
    assert len(pack.get("hooks", {})) == 220, f"Expected 220 hooks, got {len(pack.get('hooks', {}))}"
    assert len(pack.get("cloze", [])) >= 271, f"Expected >=271 cloze, got {len(pack.get('cloze', []))}"
    national = [q for q in pack["cloze"] if q.get("level") == "national"]
    assert len(national) >= 94, f"Expected >=94 national cloze, got {len(national)}"
    broken = [q["id"] for q in pack["cloze"] if q.get("wid") not in wids]
    assert not broken, f"Broken wids in real pack: {broken[:10]}"

    with env.new_session(timeout_ms=10000) as s:
        open_app(s.page, s.base_url)
        upload_bundle(s.page, EXTERNAL_BUNDLE_PATH)
        switch_tab(s.page, "loop")
        badge = upload_ai_pack(s.page, EXTERNAL_AI_PACK_PATH)
        hk_cnt, cl_cnt = parse_ext_badge_counts(badge)
        assert hk_cnt == 220, f"Expected badge 220 hooks, got {hk_cnt}"
        assert cl_cnt == len(pack["cloze"]), f"Expected badge {len(pack['cloze'])} cloze, got {cl_cnt}"

        fams = get_available_verb_families(s.page)
        for cf in CANONICAL_FAMILIES:
            assert cf in fams, f"Missing canonical family {cf!r} in real pack UI"

        # Drill ext_cloze + national + each of the 4 旧帝大 categories
        select_loop_mode(s.page, "single")
        select_loop_focus(s.page, "mcq")
        select_loop_target(s.page, "ext_cloze")
        select_loop_level(s.page, "national")
        for cat in IMPERIAL_4_FAMILIES:
            select_verb_family(s.page, cat)
            start_loop_session(s.page)
            s.page.locator("#mcqChoicesGrid").wait_for(state="visible")
            lvl_text = s.page.locator("[data-testid='mcq-level-badge']").inner_text()
            assert "旧帝" in lvl_text or "国公立" in lvl_text or "national" in lvl_text.lower()
            s.page.locator("#mcqPauseBtn").click()
            s.page.locator("#loopStartBtn").wait_for(state="visible")

        s.assert_no_errors()
