# Arcs Rules Skill — Eval Rubric

Answers are scored on six dimensions, each rated 0–3 then normalized and weighted.

**Aggregate score = Σ(score/3 × weight × 100)** → 0–100.

Dimensions marked **N/A** for a given question receive full marks (3/3).

---

## Dimensions

### 1. Accuracy — 35%

Does every factual claim match the canonical answer or official source?

| Score | Meaning |
|---|---|
| 3 | All claims match the canonical answer or source YAML within reasonable paraphrase. |
| 2 | Minor omission or imprecision that does not change the practical ruling. |
| 1 | A key fact is wrong or reversed (e.g., answers "yes" when canonical answer is "no"). |
| 0 | Fabricated rule not in any source file, or direct contradiction of the source. |

### 2. Citation quality — 20%

Are rules sections and card URLs cited, and are they correct?

| Score | Meaning |
|---|---|
| 3 | Cites the correct section number AND uses a valid `link_url` from `rules-index.txt`, or a correct card URL from `card-index.txt`. |
| 2 | Mentions the right topic area but section number is off, or the link is missing. |
| 1 | Cites a tangentially related section. |
| 0 | No citation, or cites a non-existent section number. |

### 3. Errata coverage — 15%

Did the skill notice and correctly apply relevant errata?

| Score | Meaning |
|---|---|
| 3 | All relevant errata noted and labeled as errata (not presented as original printed text). |
| 2 | Errata mentioned but not clearly labeled, or only partially noted. |
| 1 | Errata exists and is completely ignored; original text cited as current. |
| 0 | Errata'd text cited and described as currently correct. |
| N/A | No errata applies to the question — treated as 3/3. |

### 4. Base/expansion split — 10%

When rules differ between base game and Blighted Reach, is the distinction clear?

| Score | Meaning |
|---|---|
| 3 | Clearly splits the answer when needed; does not split when both products share the same rule. |
| 2 | Mentions both contexts but doesn't delineate which is which clearly. |
| 1 | Only addresses one context when both apply. |
| 0 | Conflates base and campaign rules, or ignores a meaningful difference. |
| N/A | Question is unambiguously base-only or campaign-only — treated as 3/3. |

### 5. Appropriate hedging — 10%

Is the answer confident when the source is clear, and honest when it is not?

| Score | Meaning |
|---|---|
| 3 | Confident where the source is clear; hedges correctly where genuinely ambiguous; says "the rules don't address this" when true. |
| 2 | Slightly over- or under-confident, but not misleading. |
| 1 | Presents a genuinely uncertain ruling as definitive. |
| 0 | Invents a rule and presents it as official, or presents a community guess as an official ruling. |

### 6. Cross-reference resolution — 10%

Are `$link:CardName$` tokens in card text resolved to actual card detail?

| Score | Meaning |
|---|---|
| 3 | All `$link:` references resolved — the linked card's relevant text is discussed. |
| 2 | Most resolved; one or two minor links skipped. |
| 1 | Linked card name mentioned but without any substantive detail. |
| 0 | Raw `$link:CardName$` or `$symbol:text$` token appears verbatim in the answer. |
| N/A | No cross-references involved — treated as 3/3. |

---

## Aggregation formula

```
weights = {accuracy: 0.35, citation: 0.20, errata: 0.15, split: 0.10, hedging: 0.10, xref: 0.10}

for each dimension d:
    if score[d] is N/A:
        contribution[d] = weights[d] * 100
    else:
        contribution[d] = (score[d] / 3) * weights[d] * 100

aggregate = sum(contribution.values())   # 0–100
```
