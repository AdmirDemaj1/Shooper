#!/usr/bin/env python3
"""
Ranking prompt regression test harness.

Loads test_cases.json, calls the ranking prompt via the Claude API, and
checks that every predicted score falls within the hand-graded acceptable
range. Computes MAE against the midpoint of each range as an overall metric.

CI gate: MAE must be <= 8 points.

Usage:
    ANTHROPIC_API_KEY=sk-... python autoscout-prompts/test_harness.py
    ANTHROPIC_API_KEY=sk-... python autoscout-prompts/test_harness.py --verbose
    ANTHROPIC_API_KEY=sk-... python autoscout-prompts/test_harness.py --fail-fast
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

import anthropic

TESTS_PATH = pathlib.Path(__file__).parent / "ranking" / "test_cases.json"
PROMPT_PATH = pathlib.Path(__file__).parent / "ranking" / "v1.md"
MAE_GATE = 8.0

RANKING_TOOL: dict[str, Any] = {
    "name": "rank_listings",
    "description": "Score each car listing for relevance to the user's search profile.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "listing_id": {"type": "string"},
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "reasoning": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["listing_id", "score", "reasoning", "summary"],
                },
            }
        },
        "required": ["scores"],
    },
}


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _profile_description(profile: dict) -> str:
    parts = []
    if profile.get("make"):
        parts.append(f"Make: {profile['make']}")
    if profile.get("model"):
        parts.append(f"Model: {profile['model']}")
    if profile.get("year_min") or profile.get("year_max"):
        parts.append(f"Year range: {profile.get('year_min', '?')} – {profile.get('year_max', '?')}")
    if profile.get("price_max"):
        parts.append(f"Max price: {profile['price_max']} {profile.get('currency', 'EUR')}")
    if profile.get("mileage_max"):
        parts.append(f"Max mileage: {profile['mileage_max']:,} km")
    if profile.get("fuel_type"):
        parts.append(f"Fuel type: {profile['fuel_type']}")
    if profile.get("transmission"):
        parts.append(f"Transmission: {profile['transmission']}")
    if profile.get("body_type"):
        parts.append(f"Body type: {profile['body_type']}")
    if profile.get("free_text_criteria"):
        parts.append(f"Additional criteria: {profile['free_text_criteria']}")
    return "\n".join(parts) or "No specific criteria."


def _score_single(
    client: anthropic.Anthropic,
    system_prompt: str,
    case: dict,
) -> int:
    """Call Claude and return the predicted score for a single test case."""
    profile_desc = _profile_description(case["profile"])
    listing = case["listing"]
    listing_with_id = {**listing, "id": case["id"]}

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=system_prompt,
        tools=[RANKING_TOOL],
        tool_choice={"type": "tool", "name": "rank_listings"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"SEARCH PROFILE:\n{profile_desc}\n\n"
                    f"LISTINGS (JSON):\n{json.dumps([listing_with_id], ensure_ascii=False)}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "rank_listings":
            scores = block.input.get("scores", [])
            if scores:
                return int(scores[0]["score"])

    raise ValueError(f"Claude did not return a score for case {case['id']}")


def run_tests(verbose: bool = False, fail_fast: bool = False) -> bool:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(TESTS_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]
    system_prompt = _load_system_prompt()
    client = anthropic.Anthropic(api_key=api_key)

    results = []
    pass_count = 0
    fail_count = 0

    print(f"Running {len(cases)} test cases against ranking/v1.md ...\n")

    for case in cases:
        cid = case["id"]
        score_min = case["score_min"]
        score_max = case["score_max"]
        midpoint = (score_min + score_max) / 2

        try:
            predicted = _score_single(client, system_prompt, case)
        except Exception as exc:
            print(f"  [ERROR] {cid}: {exc}")
            fail_count += 1
            if fail_fast:
                break
            continue

        in_range = score_min <= predicted <= score_max
        abs_error = abs(predicted - midpoint)
        results.append(abs_error)

        status = "PASS" if in_range else "FAIL"
        if in_range:
            pass_count += 1
        else:
            fail_count += 1

        if verbose or not in_range:
            print(
                f"  [{status}] {cid}: predicted={predicted}, "
                f"expected=[{score_min},{score_max}], |err|={abs_error:.1f}"
                f"\n         {case['description']}"
            )
        else:
            print(f"  [{status}] {cid}: {predicted} ∈ [{score_min},{score_max}]")

        if fail_fast and not in_range:
            break

    print(f"\n{'='*60}")
    print(f"Results: {pass_count} passed, {fail_count} failed out of {len(results)} scored")

    if results:
        mae = sum(results) / len(results)
        gate_status = "PASS" if mae <= MAE_GATE else "FAIL"
        print(f"MAE against midpoints: {mae:.2f} (gate <= {MAE_GATE}) [{gate_status}]")
    else:
        mae = float("inf")
        gate_status = "FAIL"

    all_passed = fail_count == 0 and mae <= MAE_GATE
    print(f"\nOverall: {'PASS ✓' if all_passed else 'FAIL ✗'}")
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ranking prompt regression tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print all results, not just failures")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")
    args = parser.parse_args()

    success = run_tests(verbose=args.verbose, fail_fast=args.fail_fast)
    sys.exit(0 if success else 1)
