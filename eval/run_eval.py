"""
Main eval runner for the arcs-rules skill.

Usage:
    python eval/run_eval.py --suite unit
    python eval/run_eval.py --suite regression
    python eval/run_eval.py --suite all --sample 20
    python eval/run_eval.py --suite eval --output results/my-run/

Run from the project root.
"""

import argparse
import json
import pathlib
import random
import sys
import time
from datetime import datetime

# Approximate token counts for the two context modes (measured 2026-05).
# Used only for pre-call user feedback and for the error fallback path —
# actual delays use real token counts from response.usage.
_TOKENS_RULES_ONLY = 100_000
_TOKENS_FULL = 200_000

# Default rate limit — override with --rate-limit if your tier differs
_DEFAULT_RATE_LIMIT_TPM = 30_000


def _required_delay(tokens_sent: int, elapsed_s: float, rate_limit_tpm: int) -> float:
    """Seconds to sleep so the current request's tokens clear the per-minute window."""
    budget_seconds = (tokens_sent / rate_limit_tpm) * 60
    return max(0.0, budget_seconds - elapsed_s)

ROOT = pathlib.Path(__file__).parent.parent
EVAL_DIR = pathlib.Path(__file__).parent
FIXTURES_DIR = EVAL_DIR / "fixtures"


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------

def run_checks(response: str, checks: dict) -> dict[str, bool]:
    results = {}
    r = response.lower()

    if checks.get("must_not_contain_raw_tokens"):
        results["no_raw_tokens"] = "$link:" not in response and "$symbol:" not in response

    for term in checks.get("must_not_contain", []):
        results[f"not_contain:{term}"] = term.lower() not in r

    for term in checks.get("must_contain_any", []):
        results["contains_any"] = any(t.lower() in r for t in checks["must_contain_any"])
        break

    for term in checks.get("must_mention", []):
        results[f"mention:{term}"] = term.lower() in r

    for kw in checks.get("must_mention_keywords", []):
        results[f"keyword:{kw}"] = kw.lower() in r

    if "must_name_card" in checks:
        card = checks["must_name_card"]
        results[f"names_card:{card}"] = card.lower() in r

    if checks.get("must_cite_card_url"):
        results["has_card_url"] = "cards.buriedgiant.com/card/" in response

    if "must_cite_section" in checks:
        section = checks["must_cite_section"]
        results["cites_section"] = (
            section in response
            or f"§{section}" in response
            or f"#{section}" in response
        )

    if checks.get("must_cite_errata"):
        results["cites_errata"] = (
            "errata" in r
            or "correction" in r
            or "corrected" in r
            or "updated" in r
        )

    for linked_card in checks.get("must_resolve_links", []):
        results[f"resolves_link:{linked_card}"] = linked_card.lower() in r

    if checks.get("must_hedge"):
        hedge_words = ["unclear", "ambiguous", "table ruling", "doesn't directly", "don't directly",
                       "not explicitly", "may vary", "consult", "community", "judgment"]
        results["hedges"] = any(w in r for w in hedge_words)

    if checks.get("must_split_base_expansion"):
        results["splits_base_expansion"] = (
            ("base game" in r or "base:" in r)
            and ("blighted reach" in r or "campaign" in r or "expansion" in r)
        )

    if checks.get("must_distinguish_versions"):
        results["distinguishes_versions"] = (
            ("base" in r or "base game" in r)
            or ("blighted reach" in r or "campaign" in r)
        )

    if "answer_should_be" in checks:
        expected = checks["answer_should_be"].lower()
        # Simple yes/no check: look for the word near the start of the response
        first_200 = r[:200]
        results[f"answer_is_{expected}"] = expected in first_200

    if "answer_should_contain" in checks:
        phrase = checks["answer_should_contain"].lower()
        results[f"answer_contains:{phrase}"] = phrase in r

    if "must_explain" in checks:
        phrase = checks["must_explain"].lower()
        results[f"explains:{phrase}"] = phrase in r

    return results


def score_checks(check_results: dict[str, bool]) -> tuple[int, int]:
    passed = sum(1 for v in check_results.values() if v)
    total = len(check_results)
    return passed, total


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def load_unit_fixtures(sample: int | None = None) -> list[dict]:
    files = [
        FIXTURES_DIR / "unit" / "rules-faq.json",
        FIXTURES_DIR / "unit" / "card-faq.json",
        FIXTURES_DIR / "unit" / "rules-errata.json",
        FIXTURES_DIR / "unit" / "card-errata.json",
        FIXTURES_DIR / "unit" / "card-names.json",
    ]
    fixtures = []
    for f in files:
        if f.exists():
            fixtures.extend(json.loads(f.read_text(encoding="utf-8")))
    if sample and sample < len(fixtures):
        fixtures = random.sample(fixtures, sample)
    return fixtures


def load_regression_fixtures() -> list[dict]:
    path = FIXTURES_DIR / "regression" / "cases.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_manual_fixtures() -> list[dict]:
    fixtures = []
    for f in (FIXTURES_DIR / "manual").glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fixtures.extend(data)
        else:
            fixtures.append(data)
    return fixtures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_suite(
    fixtures: list[dict],
    client,
    model: str,
    use_judge: bool,
    output_dir: pathlib.Path,
    rate_limit_tpm: int = _DEFAULT_RATE_LIMIT_TPM,
) -> list[dict]:
    from eval.scripts.invoke_skill import invoke, needs_card_context

    results = []
    total = len(fixtures)

    for i, fixture in enumerate(fixtures, 1):
        fid = fixture.get("id", f"fixture-{i}")
        question = fixture.get("question", "")
        checks = fixture.get("checks", {})

        with_cards = needs_card_context(question)
        ctx_label = "full" if with_cards else "rules"
        est_tokens = _TOKENS_FULL if with_cards else _TOKENS_RULES_ONLY
        print(f"  [{i}/{total}] {fid} [{ctx_label} ~{est_tokens//1000}K]", flush=True)
        start = time.time()

        try:
            response, usage = invoke(question, client, model=model, with_cards=with_cards)
            elapsed = time.time() - start

            new_t = usage["input_tokens"] + usage["cache_creation_input_tokens"]
            cached_t = usage["cache_read_input_tokens"]
            total_t = usage["total_input"]
            print(
                f"      usage: new={new_t//1000}K  cache_read={cached_t//1000}K  "
                f"total_in={total_t//1000}K  out={usage['output_tokens']}",
                flush=True,
            )

            if i < total:
                # Pace based on total input tokens (the conservative assumption that
                # cache reads count against the per-minute limit). If your tier
                # exempts cache reads, you'll waste some time waiting — that's
                # safer than getting 429s.
                pause = _required_delay(total_t, elapsed, rate_limit_tpm)
                if pause > 0:
                    print(f"      pause {pause:.0f}s", flush=True)
                    time.sleep(pause)

            check_results = run_checks(response, checks)
            passed, total_checks = score_checks(check_results)
            pass_rate = passed / total_checks if total_checks else 1.0
            status = "PASS" if pass_rate == 1.0 else ("WARN" if pass_rate >= 0.7 else "FAIL")

            result = {
                "id": fid,
                "question": question,
                "response": response,
                "check_results": check_results,
                "passed": passed,
                "total_checks": total_checks,
                "pass_rate": round(pass_rate, 3),
                "status": status,
                "elapsed_s": round(elapsed, 2),
                "usage": usage,
            }

            if use_judge and fixture.get("canonical_answer"):
                from eval.judge import judge_response
                scores = judge_response(
                    question=question,
                    canonical=fixture["canonical_answer"],
                    actual=response,
                    client=client,
                    model=model,
                )
                result["judge_scores"] = scores

            print(f"      {status} ({passed}/{total_checks} checks, {elapsed:.1f}s)")

        except Exception as e:
            elapsed = time.time() - start
            print(f"      ERROR: {e}")
            result = {
                "id": fid,
                "question": question,
                "error": str(e),
                "status": "ERROR",
            }
            # No actual usage data on failure — fall back to upper-bound estimate
            if i < total:
                pause = _required_delay(est_tokens, elapsed, rate_limit_tpm)
                if pause > 0:
                    print(f"      pause {pause:.0f}s (estimated)", flush=True)
                    time.sleep(pause)

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(results: list[dict], suite_name: str):
    passed = sum(1 for r in results if r.get("status") == "PASS")
    warned = sum(1 for r in results if r.get("status") == "WARN")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    errored = sum(1 for r in results if r.get("status") == "ERROR")
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  {suite_name.upper()} RESULTS")
    print(f"{'='*60}")
    print(f"  PASS  {passed:>4}  ({100*passed//total if total else 0}%)")
    print(f"  WARN  {warned:>4}")
    print(f"  FAIL  {failed:>4}")
    print(f"  ERROR {errored:>4}")
    print(f"  TOTAL {total:>4}")

    failures = [r for r in results if r.get("status") in ("FAIL", "ERROR")]
    if failures:
        print(f"\n  Failures:")
        for r in failures[:10]:
            fid = r.get("id", "?")
            if "error" in r:
                print(f"    {fid}: {r['error']}")
            else:
                failed_checks = [k for k, v in r.get("check_results", {}).items() if not v]
                print(f"    {fid}: failed {failed_checks}")

    if any("judge_scores" in r for r in results):
        scores = [r["judge_scores"]["aggregate_score"] for r in results if "judge_scores" in r]
        avg = sum(scores) / len(scores)
        print(f"\n  Judge quality score: {avg:.1f}/100 (n={len(scores)})")

    print()


def save_results(results: list[dict], output_dir: pathlib.Path, filename: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Results saved to {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Arcs rules skill eval runner")
    parser.add_argument(
        "--suite",
        choices=["unit", "regression", "eval", "all"],
        default="unit",
        help="Which test suite to run",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Run N randomly sampled unit tests instead of the full set",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for results JSON (default: results/YYYY-MM-DD-HHmm/)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-6",
        help="Claude model to use",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run LLM-as-judge scoring (slower, costs more)",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=_DEFAULT_RATE_LIMIT_TPM,
        dest="rate_limit",
        help="Your input tokens-per-minute rate limit (default: 30000). "
             "The runner sleeps after each call for exactly long enough to clear "
             "that call's tokens from the rolling window before the next call starts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print fixtures without invoking the skill",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    output_dir = pathlib.Path(args.output) if args.output else EVAL_DIR / "results" / timestamp

    if args.dry_run:
        fixtures = load_unit_fixtures(args.sample)
        print(f"Would run {len(fixtures)} unit fixtures")
        reg = load_regression_fixtures()
        print(f"Would run {len(reg)} regression fixtures")
        return

    # Lazy import so the file is importable without anthropic installed
    import os
    if "ANTHROPIC_API_KEY" not in os.environ:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    from eval.scripts.invoke_skill import build_client
    client = build_client()

    suites_to_run = []
    if args.suite in ("unit", "all"):
        suites_to_run.append(("unit", load_unit_fixtures(args.sample), False))
    if args.suite in ("regression", "all"):
        suites_to_run.append(("regression", load_regression_fixtures(), False))
    if args.suite == "eval":
        # eval runs unit fixtures with judge enabled
        suites_to_run.append(("eval", load_unit_fixtures(args.sample), True))

    use_judge = args.judge or args.suite == "eval"

    for suite_name, fixtures, suite_judge in suites_to_run:
        if not fixtures:
            print(f"\nNo fixtures found for suite '{suite_name}'. Run generate_fixtures.py first.")
            continue
        print(f"\nRunning {suite_name} suite ({len(fixtures)} cases, rate limit {args.rate_limit} tpm)...")
        results = run_suite(
            fixtures, client, args.model, use_judge or suite_judge, output_dir,
            rate_limit_tpm=args.rate_limit,
        )
        print_summary(results, suite_name)
        save_results(results, output_dir, f"{suite_name}-results.json")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
