"""
Compare two eval results directories to surface regressions and improvements.

Usage:
    python eval/scripts/compare_runs.py results/2026-05-01-1200/ results/2026-05-12-1530/
"""

import argparse
import json
import pathlib
import sys


def load_results(directory: pathlib.Path) -> dict[str, dict]:
    """Load all *-results.json files from a directory, keyed by test id."""
    all_results = {}
    for path in sorted(directory.glob("*-results.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for result in data:
            all_results[result["id"]] = result
    return all_results


def compare(baseline_dir: pathlib.Path, new_dir: pathlib.Path):
    baseline = load_results(baseline_dir)
    new = load_results(new_dir)

    all_ids = sorted(set(baseline) | set(new))

    regressions = []
    improvements = []
    new_tests = []
    removed_tests = []

    for tid in all_ids:
        b = baseline.get(tid)
        n = new.get(tid)

        if b is None:
            new_tests.append(tid)
            continue
        if n is None:
            removed_tests.append(tid)
            continue

        b_status = b.get("status", "UNKNOWN")
        n_status = n.get("status", "UNKNOWN")

        if b_status == "PASS" and n_status != "PASS":
            regressions.append((tid, b_status, n_status, n.get("check_results", {})))
        elif b_status != "PASS" and n_status == "PASS":
            improvements.append((tid, b_status, n_status))

    # Judge score delta
    b_scores = [v["judge_scores"]["aggregate_score"] for v in baseline.values()
                if "judge_scores" in v and v["judge_scores"].get("aggregate_score") is not None]
    n_scores = [v["judge_scores"]["aggregate_score"] for v in new.values()
                if "judge_scores" in v and v["judge_scores"].get("aggregate_score") is not None]

    print(f"\nBaseline : {baseline_dir}")
    print(f"New      : {new_dir}")
    print(f"\nTotal tests — baseline: {len(baseline)}, new: {len(new)}")
    print(f"New tests added : {len(new_tests)}")
    print(f"Tests removed   : {len(removed_tests)}")

    if regressions:
        print(f"\n{'REGRESSIONS':=<60}")
        for tid, b_s, n_s, checks in regressions:
            failed = [k for k, v in checks.items() if not v]
            print(f"  {tid}: {b_s} → {n_s}  (failed: {failed})")
    else:
        print("\nNo regressions.")

    if improvements:
        print(f"\n{'IMPROVEMENTS':=<60}")
        for tid, b_s, n_s in improvements:
            print(f"  {tid}: {b_s} → {n_s}")

    if b_scores and n_scores:
        b_avg = sum(b_scores) / len(b_scores)
        n_avg = sum(n_scores) / len(n_scores)
        delta = n_avg - b_avg
        sign = "+" if delta >= 0 else ""
        print(f"\nJudge score: {b_avg:.1f} → {n_avg:.1f}  ({sign}{delta:.1f})")


def main():
    parser = argparse.ArgumentParser(description="Compare two eval run directories")
    parser.add_argument("baseline", help="Path to baseline results directory")
    parser.add_argument("new", help="Path to new results directory")
    args = parser.parse_args()

    baseline_dir = pathlib.Path(args.baseline)
    new_dir = pathlib.Path(args.new)

    for d in (baseline_dir, new_dir):
        if not d.is_dir():
            print(f"Error: {d} is not a directory", file=sys.stderr)
            sys.exit(1)

    compare(baseline_dir, new_dir)


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
    main()
