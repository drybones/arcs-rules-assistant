# Eval framework — approach and open problems

Paused 2026-05-12 on branch `eval-framework`. Code is in `eval/`; the framework is structurally complete and the fixture pipeline works end-to-end, but the runner cannot complete a Sonnet eval at our current Anthropic rate-limit tier. See "Why this is paused" below.

## What was built

A layered test/eval suite for the `/arcs-rules` skill, in `eval/`:

```
eval/
├── README.md                       # how to run
├── rubric.md                       # human-readable scoring rubric
├── requirements.txt
├── generate_fixtures.py            # builds unit fixtures from YAML
├── run_eval.py                     # main runner
├── judge.py                        # LLM-as-judge scoring (Layer 3)
├── fixtures/
│   ├── unit/                       # 402 cases, generated from official YAML
│   └── regression/cases.json       # 10 hand-authored failure-mode cases
├── scripts/
│   ├── invoke_skill.py             # SDK wrapper with prompt caching
│   └── compare_runs.py             # diff two results dirs
└── results/                        # timestamped per-run outputs (gitignored)
```

### Three layers

**Layer 1 — Unit tests (402 cases, auto-generated).** `generate_fixtures.py` parses the official YAML sources and emits JSON fixtures: 39 rules FAQ, 225 card FAQ, 21 rules errata, 67 card errata, 50 card-name samples. Deterministic checks only (no LLM judge needed) — verifies the response cites the expected section, names the right card, doesn't leak `$link:` tokens, mentions key terms from the canonical answer.

**Layer 2 — Regression tests (10 cases, hand-authored).** Each case targets a specific known failure mode: publisher confusion (Leder Games vs Buried Giant), `$link:` token leaks, errata-overrides-rules, base/expansion splits, ambiguity hedging, card errata that flip a ruling.

**Layer 3 — LLM-as-judge quality eval.** Six dimensions weighted to an aggregate 0–100 score: accuracy (35%), citation quality (20%), errata coverage (15%), base/expansion split (10%), hedging (10%), cross-reference resolution (10%). N/A maps to full marks when a dimension doesn't apply. Judge runs as a separate, lightweight Claude call.

### Invocation strategy

`invoke_skill.py` calls Claude Sonnet 4.6 via the SDK with the full corpus loaded into the system prompt and marked `cache_control: ephemeral`. This approximates the skill's behavior without going through the Claude Code harness (which would be too slow and stateful for an automated suite). The system instruction is kept static (no `$ARGUMENTS` injection) so the cache prefix doesn't change between calls.

Two context modes: **rules-only** (skips card YAML for general rules questions) and **full** (includes everything). `needs_card_context()` auto-detects which to use by scanning the question for card keywords and matching against the card-name index.

### Dynamic rate-limit pacing

After each call, the runner reads `response.usage` and sleeps long enough that the request's tokens have aged out of the per-minute window before the next call:

```python
pause = (tokens_used / rate_limit_tpm) * 60 - elapsed
```

The 1-hour cache TTL (via `extended-cache-ttl-2025-04-11` beta header) is set so the long pauses don't bust the cache.

## Why this is paused

**The corpus is too large for our rate-limit tier.**

Measured token counts (not the 107K guess in the original DEVELOPMENT.md note):

| Context | Bytes | Tokens |
|---|---|---|
| Rules-only | 293 KB | ~98K |
| Full corpus | 600 KB | ~200K |

Largest contributors: `blightedreach.yml` (72K tokens), `rules.yml` (40K), `rules-index.txt` (30K).

At our current limit of **30,000 input tokens per minute**, every full-context call consumes ~6.7 minutes of budget. Anthropic counts cache reads against the per-minute input limit (caching saves money but does not bypass the rate limit), so even with the corpus cached the per-call pause stays at ~6.7 minutes. A 20-sample run takes roughly **two hours of wall time**. The full 412-case suite is impractical.

We cannot get around this with code. The pause length is dictated by the rate-limit math.

## Paths forward (when resumed)

In rough order of practicality:

1. **Request a rate-limit increase from Anthropic.** Tier 2 (typically 100K TPM) makes the suite usable; Tier 3 (300K TPM) makes it fast. This is the right answer.

2. **Shrink the corpus.** Drop the largest non-essential files:
   - `rules-index.txt` (30K tokens) — used for URL lookup; could be replaced with a smaller mapping or generated at answer time
   - `card-index.txt` (15K tokens) — same
   - Possibly trim `blightedreach.yml` (72K tokens) by excluding card flavor text from the eval corpus
   - Realistic target: ~110K tokens, roughly half the current size, still slow but viable

3. **Move to retrieval.** Rather than loading the entire corpus per call, pre-embed the YAML and retrieve only the relevant 5–10K tokens per question. This is the right architecture for a production app but is a significant rewrite — overkill for the eval alone.

4. **Run on a paid tier with prepaid spend.** If Anthropic offers a usage-tier upgrade by raising the deposit, that's the lowest-friction path.

## Test the framework before scaling

Once the rate-limit issue is resolved, validate end-to-end with a small run before doing anything large:

```bash
python eval/run_eval.py --suite regression                  # 10 hand-authored cases
python eval/run_eval.py --suite unit --sample 5             # 5 random unit cases
python eval/run_eval.py --suite eval --sample 20            # 20 cases with judge scoring
```

Each call's `response.usage` is printed live (new vs cache_read vs total) so you can verify caching is actually working before running anything expensive.

## Other notes for future work

- The original DEVELOPMENT.md note "430 KB ≈ 107K tokens" was wrong by ~2×. Corrected.
- Question sourcing beyond the YAML — BGG forums (game ID 359871) and Reddit r/Arcs — was planned in `eval/README.md` but not yet implemented. Add scripts to `eval/scripts/` when resumed.
- Manual fixtures (`eval/fixtures/manual/`) are picked up automatically; this is the right place for cases added from real table play.
- The judge prompt in `eval/judge.py` could be improved with few-shot examples once we have real scored responses to calibrate against.
