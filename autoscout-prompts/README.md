# AutoScout Prompts

Versioned LLM prompts for AutoScout AI. Every prompt has tests and a regression suite.

## Philosophy

- **Prompts are code.** They're versioned, tested, and reviewed like any other code.
- **All prompts in source control.** Never edit prompts in production dashboards or notebooks.
- **Every prompt has tests.** Minimum 30 regression test cases per prompt version.
- **Prompt changes go through PR review.** The AI/ML engineer and at least one other engineer review.
- **Roll back fast.** If a prompt change degrades quality, revert and file a bug.

## Directory Structure

```
autoscout-prompts/
├── profile_parser/
│   ├── v1.md                                # System prompt for profile parsing
│   ├── v1_test_cases.yaml                   # 30+ test cases with expected outputs
│   ├── v1_regression_results.json           # Latest test run results
│   └── CHANGELOG.md                         # What changed between versions
├── ranking/
│   ├── v1.md                                # Ranking prompt
│   ├── v1_test_cases.yaml
│   ├── v1_regression_results.json
│   └── CHANGELOG.md
├── dedup_tiebreaker/
│   ├── v1.md
│   ├── v1_test_cases.yaml
│   └── ...
├── summarization/                           # Summary for WhatsApp messages
│   ├── v1.md
│   ├── v1_test_cases.yaml
│   └── ...
├── tools/                                   # Tool-use JSON schemas
│   ├── profile_extraction.json              # For profile_parser tool
│   ├── ranking_scores.json                  # For ranking tool
│   └── ...
├── test_harness.py                          # CLI to run regression tests
├── requirements.txt                         # anthropic SDK, pyyaml, etc.
└── README.md
```

## Prompt Format

Each prompt is a markdown file with metadata and content:

```markdown
---
name: profile_parser
version: v1
model: claude-sonnet-4-6
input: free-text description of a car search
output: structured search profile (JSON)
created_at: 2026-05-14
author: aidiemaj
---

# Profile Parser Prompt

You are a search form assistant for an Albanian used-car marketplace. Users type what they're looking for in Albanian or English, and you extract structured fields.

## Instructions

1. Extract make, model, year range, price, mileage, location, condition.
2. Use the `create_search_profile` tool to structure your response.
3. If a field is ambiguous or missing, leave it null.
...
```

## Test Cases

Test cases are in YAML:

```yaml
test_cases:
  - name: "Simple Albanian query"
    input: "kërkoj Golf 6 nën 8000 euro, max 200 mijë km, afër Tiranës"
    expected_output:
      make: "Volkswagen"
      model: "Golf 6"
      year_min: null
      year_max: null
      price_max: 8000
      currency: "EUR"
      mileage_max: 200000
      location_text: "Tiranë"
    tolerance:
      price: 500  # Allow ±500 EUR

  - name: "English query with year range"
    input: "Looking for a Honda Civic 2010 to 2015, under $12,000, manual transmission"
    expected_output:
      make: "Honda"
      model: "Civic"
      year_min: 2010
      year_max: 2015
      price_max: 12000
      currency: "USD"  # Will be converted to EUR
      transmission: "manual"
```

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests for a prompt
python test_harness.py --prompt=profile_parser --version=v1

# Run and save results
python test_harness.py --prompt=profile_parser --version=v1 --save-results

# Run a specific test case
python test_harness.py --prompt=profile_parser --version=v1 --case="Simple Albanian query"

# Compare two versions
python test_harness.py --compare=v1 v2
```

Output example:
```
Profile Parser v1 Regression Tests
====================================
Passed: 28/30
Failed: 2/30
Regression: +0.3%

Failed cases:
  - "Dialect: southern Albanian" — expected make=null, got make="Fiat"
  - "Misspelling: vw instead of vw" — expected make="Volkswagen", got make=null
```

## Prompt Versioning Workflow

1. **Create a new version:**
   ```bash
   cp profile_parser/v1.md profile_parser/v2.md
   cp profile_parser/v1_test_cases.yaml profile_parser/v2_test_cases.yaml
   ```

2. **Edit the prompt** (`profile_parser/v2.md`).

3. **Run tests:**
   ```bash
   python test_harness.py --prompt=profile_parser --version=v2 --save-results
   ```

4. **Compare against v1:**
   ```bash
   python test_harness.py --compare=v1 v2
   ```

5. **Review:** Submit PR with prompt, test cases, and regression results. At least one engineer must review.

6. **Merge:** Once approved, merge to main.

7. **Deploy:** Update backend to reference `v2` in settings; deploy.

8. **Monitor:** Watch LLM cost and error rates for 24h. If regression detected, roll back to v1.

## Cost Tracking

Every prompt tracks token usage:

```json
{
  "prompt_name": "profile_parser",
  "version": "v1",
  "model": "claude-sonnet-4-6",
  "date": "2026-05-14",
  "calls": 150,
  "input_tokens_total": 45000,
  "output_tokens_total": 3000,
  "cost_usd": 0.60,
  "avg_tokens_per_call": 320,
  "latency_p95_ms": 1200
}
```

Logged daily; alerting if a prompt's cost exceeds budget.

## Fallback Prompts

If Claude is unavailable, fallback to deterministic rules (documented in backend code). Fallback cost is zero but quality is lower. Fallback usage is tracked; if >5% of calls hit fallback, escalate.

## Contributing

1. **Prompt tweak?** Update the version file in-place (v1.md), add test cases, run the harness, commit + PR.
2. **New prompt type?** Create a new directory, add v1.md + v1_test_cases.yaml, run harness, PR.
3. **Test cases from beta feedback?** Add to the test file under a new `beta_feedback` section with the user's original query.
