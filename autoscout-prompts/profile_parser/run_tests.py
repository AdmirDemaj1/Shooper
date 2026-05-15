#!/usr/bin/env python3
"""
Regression test harness for the AutoScout profile parser prompt.

Run from the autoscout-backend directory:
    ANTHROPIC_API_KEY=sk-ant-... poetry run python ../autoscout-prompts/profile_parser/run_tests.py

Options:
    --id <id>        Run a single test case by id
    --lang sq|en     Filter by language
    --fail-fast      Stop on first failure
    --verbose        Show actual parsed output for every case
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

TESTS_FILE = Path(__file__).parent / "tests.yaml"
NUMERIC_TOLERANCE_PCT = 0.10  # 10% tolerance for numeric comparisons

# Add backend to path so we can import the shared tool definition + prompt
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "autoscout-backend"))

try:
    import anthropic
    from autoscout.profiles.router import _PARSE_TOOL, _load_system_prompt
    from autoscout.settings import settings
except ImportError as e:
    print(f"ERROR: Could not import backend modules: {e}", file=sys.stderr)
    print("Run this script from the autoscout-backend directory with: poetry run python ...", file=sys.stderr)
    sys.exit(1)


def call_claude(client: anthropic.Anthropic, text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_load_system_prompt(),
        tools=[_PARSE_TOOL],
        tool_choice={"type": "tool", "name": "create_search_profile"},
        messages=[{"role": "user", "content": text}],
    )
    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_block:
        return {}
    result = dict(tool_block.input)
    result.pop("confidence_scores", None)
    result.pop("location_name", None)
    return result


def check_field(field: str, expected, actual) -> tuple[bool, str]:
    if actual is None:
        return False, f"missing — expected {expected!r}"

    if isinstance(expected, str):
        e_lower = expected.lower()
        a_lower = str(actual).lower()
        if e_lower in a_lower or a_lower in e_lower:
            return True, ""
        return False, f"got {actual!r}, expected to contain {expected!r}"

    if isinstance(expected, (int, float)):
        tolerance = max(abs(expected) * NUMERIC_TOLERANCE_PCT, 1)
        if abs(float(actual) - float(expected)) <= tolerance:
            return True, ""
        return False, f"got {actual}, expected {expected} (±{tolerance:.0f})"

    if actual == expected:
        return True, ""
    return False, f"got {actual!r}, expected {expected!r}"


def run_case(client: anthropic.Anthropic, case: dict, verbose: bool = False) -> dict:
    result: dict = {"id": case["id"], "passed": True, "failures": []}

    try:
        actual = call_claude(client, case["input"])
    except Exception as e:
        result["passed"] = False
        result["failures"].append(f"API error: {e}")
        return result

    for field, expected_value in case.get("expect", {}).items():
        passed, reason = check_field(field, expected_value, actual.get(field))
        if not passed:
            result["passed"] = False
            result["failures"].append(f"{field}: {reason}")

    for field in case.get("must_not_be_null", []):
        if not actual.get(field):
            result["passed"] = False
            result["failures"].append(f"{field}: must not be null/empty")

    if verbose:
        result["actual"] = actual

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run profile parser regression tests")
    parser.add_argument("--id", help="Run only the test with this id")
    parser.add_argument("--lang", choices=["sq", "en"], help="Filter by language")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--verbose", action="store_true", help="Show parsed output for every case")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    with open(TESTS_FILE) as f:
        cases: list[dict] = yaml.safe_load(f)

    if args.id:
        cases = [c for c in cases if c["id"] == args.id]
    if args.lang:
        cases = [c for c in cases if c.get("lang") == args.lang]

    if not cases:
        print("No matching test cases.")
        sys.exit(0)

    client = anthropic.Anthropic(api_key=api_key)
    passed = failed = 0

    for case in cases:
        r = run_case(client, case, verbose=args.verbose)
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lang_tag = f"[{case.get('lang', '??')}]"
        print(f"{status} {lang_tag} [{r['id']}]  {case['input'][:70]}")
        for failure in r.get("failures", []):
            print(f"       → {failure}")
        if args.verbose and "actual" in r:
            print(f"       actual: {r['actual']}")

        if r["passed"]:
            passed += 1
        else:
            failed += 1
            if args.fail_fast:
                break

    total = passed + failed
    print(f"\n{'─' * 60}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)")
    else:
        print("  — all green ✅")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
