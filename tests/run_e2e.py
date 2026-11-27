#!/usr/bin/env python3
"""Unified CLI E2E test runner for systan-srs (Tiers 1–4).

Usage:
  python3 tests/run_e2e.py [--tier 1|2|3|4|all] [-k PATTERN]
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from harness import SkipTest, TestEnv  # noqa: E402

TIER_MODULES = {
    "1": "test_tier1_features",
    "2": "test_tier2_boundaries",
    "3": "test_tier3_interactions",
    "4": "test_tier4_scenarios",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run systan-srs Playwright E2E tests.")
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Which tier to execute (default: all).",
    )
    parser.add_argument(
        "-k",
        dest="pattern",
        default="",
        help="Optional substring filter on test function names.",
    )
    args = parser.parse_args()

    selected_tiers = ["1", "2", "3", "4"] if args.tier == "all" else [args.tier]
    modules = []
    for t in selected_tiers:
        mod_name = TIER_MODULES[t]
        mod_path = TESTS_DIR / f"{mod_name}.py"
        if mod_path.exists():
            modules.append((t, importlib.import_module(mod_name)))

    passed = 0
    skipped = 0
    failed: list[tuple[str, str, str]] = []
    t0 = time.time()

    with TestEnv() as env:
        for tier, mod in modules:
            funcs = [n for n in sorted(dir(mod)) if n.startswith("test_")]
            if args.pattern:
                funcs = [n for n in funcs if args.pattern in n]
            for name in funcs:
                fn = getattr(mod, name)
                label = f"T{tier}:{name}"
                try:
                    fn(env)
                    passed += 1
                    print(f"PASS {label}")
                except SkipTest as exc:
                    skipped += 1
                    print(f"SKIP {label} — {exc}")
                except Exception as exc:
                    tb = traceback.format_exc()
                    failed.append((label, str(exc), tb))
                    print(f"FAIL {label} — {exc}")

    elapsed = time.time() - t0
    total = passed + skipped + len(failed)
    print(f"\n=== E2E SUMMARY: {passed} passed, {skipped} skipped, {len(failed)} failed (total {total}) in {elapsed:.1f}s ===")
    if failed:
        print("\n--- FAILURE DETAILS ---")
        for label, msg, tb in failed:
            print(f"\n[{label}] {msg}\n{tb}")
        return 1
    if total == 0:
        print("ERROR: zero tests collected.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
