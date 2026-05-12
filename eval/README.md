# Arcs Rules Skill — Eval Framework

Tests and evaluates the `/arcs-rules` skill across three layers: unit tests generated from the official YAML sources, hand-authored regression tests for known failure modes, and an optional LLM-as-judge quality score.

## Setup

```
pip install -r eval/requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

## Generating fixtures

Run this any time you update the content repos (`rules/` or `cards/`):

```
python eval/generate_fixtures.py
```

This regenerates the four JSON files in `eval/fixtures/unit/` from the YAML sources — 402 test cases total (39 rules FAQ, 225 card FAQ, 21 rules errata, 67 card errata, 50 card name samples).

## Running the eval

From the project root:

```
# Quick sanity check (20 random unit tests, deterministic only)
python eval/run_eval.py --suite unit --sample 20

# Full unit suite
python eval/run_eval.py --suite unit

# Regression tests (10 hand-authored failure-mode cases)
python eval/run_eval.py --suite regression

# Everything
python eval/run_eval.py --suite all

# Full unit suite with LLM-as-judge quality scoring (~$3-4, warm cache)
python eval/run_eval.py --suite eval
```

Results land in `eval/results/YYYY-MM-DD-HHmm/`.

## Comparing runs

```
python eval/scripts/compare_runs.py results/2026-05-01-1200/ results/2026-05-12-1530/
```

Prints regressions (tests that were PASS and are now FAIL), improvements (the reverse), and judge score delta.

## Test layers

### Layer 1: Unit tests (`--suite unit`)

Generated automatically from official source files. Each test case is derived from a real Q&A pair or errata entry. Deterministic checks only — no LLM calls for scoring.

| Fixture file | Source | Count |
|---|---|---|
| `fixtures/unit/rules-faq.json` | `rules/.../faq.yml` | 39 |
| `fixtures/unit/card-faq.json` | `cards/content/faq/arcs/en-US.yml` | 225 |
| `fixtures/unit/rules-errata.json` | `rules/.../errata.yml` | 21 |
| `fixtures/unit/card-errata.json` | `cards/content/errata/arcs/en-US.yml` | 67 |
| `fixtures/unit/card-names.json` | `skill/arcs-rules/card-index.txt` | 50 |

### Layer 2: Regression tests (`--suite regression`)

Hand-authored cases targeting specific known failure modes. Grow this set when table play reveals a new failure.

| ID | Failure mode |
|---|---|
| reg-001 | Publisher confusion (Leder Games vs Buried Giant) |
| reg-002 | Ambiguity hedge (simultaneous effects) |
| reg-003 | Cross-product context (L&L + Blighted Reach) |
| reg-004 | Errata overrides rules (3.1.2.6 shuffle step) |
| reg-005 | Raw token leak (`$link:` in output) |
| reg-006 | Base vs expansion split (hit resolution FAQ 7.7.1) |
| reg-007 | Renamed errata'd term ("deep wells" → "lower wells") |
| reg-008 | No official answer (solitaire mode) |
| reg-009 | Card errata flips ruling (Foiling Conspiracies) |
| reg-010 | Multi-product card variant (Admin Union) |

### Layer 3: Quality eval (`--suite eval` or `--judge` flag)

Runs the LLM-as-judge (`eval/judge.py`) on each response and produces a 0–100 quality score. See `eval/rubric.md` for scoring dimensions and weights.

**Approximate cost:** ~$3–4 per full suite run on warm cache. Use `--sample 20` during development.

## Adding tests

**Unit tests** — re-run `generate_fixtures.py` after updating the content repos. Tests are derived automatically; no manual authoring needed.

**Regression tests** — edit `eval/fixtures/regression/cases.json`. Each case needs an `id`, `failure_mode`, `title`, `question`, and `checks` dict.

**Manual tests** — drop any `*.json` file (array of fixture objects) into `eval/fixtures/manual/`. These are picked up by `--suite all`.

## Sourcing questions from the community

BGG forums (Arcs game page, ID 359871) and Reddit r/Arcs are good sources for real player questions. Threads with a Buried Giant designer reply are gold-standard regression cases. Add them to `eval/fixtures/manual/` or `eval/fixtures/regression/cases.json`.
