"""
LLM-as-judge scoring for the arcs-rules skill eval.

The judge is a separate, lightweight Claude call — it does NOT receive
the full corpus, only the question, canonical answer, and actual response.
"""

import json
import re

import anthropic

JUDGE_SYSTEM = """\
You are an impartial evaluator scoring answers to Arcs board game rules questions.

Score the answer on each of the six dimensions below, on a scale of 0 to 3.
Use null for a dimension that is not applicable to this question.

Dimensions:
1. accuracy          — factual correctness vs. the canonical answer (weight 35%)
2. citation_quality  — correct rules section or card URL cited (weight 20%)
3. errata_coverage   — relevant errata noticed and labeled (weight 15%; null if no errata applies)
4. base_expansion_split — base/campaign distinction when needed (weight 10%; null if question is unambiguously one or the other)
5. appropriate_hedging  — confident when clear, hedges when genuinely ambiguous (weight 10%)
6. cross_ref_resolution — $link: tokens resolved to actual card detail (weight 10%; null if no cross-references)

Scoring guide:
  3 = fully correct / complete
  2 = mostly correct, minor gap that doesn't change the ruling
  1 = partial, a key fact or element missing or wrong
  0 = absent, fabricated, or directly contradicts the source

Weights for aggregate:
  accuracy=0.35, citation_quality=0.20, errata_coverage=0.15,
  base_expansion_split=0.10, appropriate_hedging=0.10, cross_ref_resolution=0.10

Compute aggregate_score (0–100) using:
  For non-null dimensions: contribution = (score / 3) * weight * 100
  For null dimensions:     contribution = weight * 100  (full marks for N/A)
  aggregate_score = sum of all contributions

Return ONLY valid JSON in this exact shape, no other text:
{
  "accuracy": <0-3>,
  "citation_quality": <0-3>,
  "errata_coverage": <0-3 or null>,
  "base_expansion_split": <0-3 or null>,
  "appropriate_hedging": <0-3>,
  "cross_ref_resolution": <0-3 or null>,
  "reasoning": {
    "accuracy": "<one sentence>",
    "citation_quality": "<one sentence>",
    "errata_coverage": "<one sentence or 'N/A'>",
    "base_expansion_split": "<one sentence or 'N/A'>",
    "appropriate_hedging": "<one sentence>",
    "cross_ref_resolution": "<one sentence or 'N/A'>"
  },
  "aggregate_score": <0-100>
}
"""

WEIGHTS = {
    "accuracy": 0.35,
    "citation_quality": 0.20,
    "errata_coverage": 0.15,
    "base_expansion_split": 0.10,
    "appropriate_hedging": 0.10,
    "cross_ref_resolution": 0.10,
}


def compute_aggregate(scores: dict) -> float:
    total = 0.0
    for dim, weight in WEIGHTS.items():
        score = scores.get(dim)
        if score is None:
            total += weight * 100
        else:
            total += (score / 3) * weight * 100
    return round(total, 1)


def judge_response(
    question: str,
    canonical: str,
    actual: str,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> dict:
    user_msg = f"QUESTION:\n{question}\n\nCANONICAL ANSWER:\n{canonical}\n\nACTUAL RESPONSE TO EVALUATE:\n{actual}"

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()

    # Strip any accidental markdown code fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        scores = json.loads(raw)
    except json.JSONDecodeError:
        # Return a sentinel so the run can continue
        return {
            "error": f"JSON parse failed: {raw[:200]}",
            "aggregate_score": None,
        }

    # Recompute aggregate locally as a sanity check
    scores["aggregate_score"] = compute_aggregate(scores)
    return scores
