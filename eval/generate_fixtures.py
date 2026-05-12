"""
Generate eval fixtures from YAML source files.
Run from the project root: python eval/generate_fixtures.py
"""

import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).parent.parent
OUT = pathlib.Path(__file__).parent / "fixtures" / "unit"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def extract_keywords(text: str, n: int = 4) -> list[str]:
    """Pull the most meaningful words from a text string."""
    # Remove markdown formatting and $token$ markers
    cleaned = re.sub(r"\$\w+:[^$]+\$", "", text)
    cleaned = re.sub(r"[*_`#\[\]()]", "", cleaned)
    # Bold/important words (surrounded by ** in original)
    bold = re.findall(r"\*\*([^*]+)\*\*", text)
    # Longer words (likely domain-specific nouns)
    long_words = [w for w in re.findall(r"\b[A-Za-z]{6,}\b", cleaned) if w.lower() not in STOPWORDS]
    candidates = bold + long_words
    seen = set()
    result = []
    for w in candidates:
        key = w.lower()
        if key not in seen:
            seen.add(key)
            result.append(w)
        if len(result) >= n:
            break
    return result


STOPWORDS = {
    "because", "before", "after", "during", "through", "without", "against",
    "between", "should", "could", "would", "their", "there", "where", "which",
    "other", "these", "those", "being", "having", "taking", "making", "always",
    "never", "cannot", "unless", "player", "players", "action", "actions",
}


def find_links(text: str) -> list[str]:
    return re.findall(r"\$link:([^$]+)\$", text)


# ---------------------------------------------------------------------------
# Rules FAQ
# ---------------------------------------------------------------------------

def gen_rules_faq():
    src = ROOT / "rules/content/rules/arcs/en-US/p1/faq.yml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    fixtures = []
    for i, entry in enumerate(data):
        sections = entry.get("rules", [])
        fixture = {
            "id": f"rules-faq-{i+1:03d}",
            "source": "rules/content/rules/arcs/en-US/p1/faq.yml",
            "question": entry["q"].strip(),
            "canonical_answer": entry["a"].strip(),
            "rule_sections": sections,
            "checks": {
                "must_mention_keywords": extract_keywords(entry["a"]),
                "must_not_contain_raw_tokens": True,
            },
        }
        if sections:
            fixture["checks"]["must_cite_section"] = sections[0]
        fixtures.append(fixture)
    _write(OUT / "rules-faq.json", fixtures)
    print(f"  rules-faq.json: {len(fixtures)} entries")


# ---------------------------------------------------------------------------
# Card FAQ
# ---------------------------------------------------------------------------

def gen_card_faq():
    src = ROOT / "cards/content/faq/arcs/en-US.yml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    fixtures = []
    for block in data:
        card = block["card"]
        for j, qa in enumerate(block["faq"]):
            q_text = qa["q"].strip()
            a_text = qa["a"].strip()
            links = find_links(q_text + " " + a_text)
            checks = {
                "must_name_card": card,
                "must_mention_keywords": extract_keywords(a_text),
                "must_not_contain_raw_tokens": True,
            }
            if links:
                checks["must_resolve_links"] = links
            fixture = {
                "id": f"card-faq-{slugify(card)}-{j+1:03d}",
                "source": "cards/content/faq/arcs/en-US.yml",
                "card_name": card,
                "question": f"Regarding the card \"{card}\": {q_text}",
                "canonical_answer": a_text,
                "checks": checks,
            }
            fixtures.append(fixture)
    _write(OUT / "card-faq.json", fixtures)
    print(f"  card-faq.json: {len(fixtures)} entries")


# ---------------------------------------------------------------------------
# Rules errata
# ---------------------------------------------------------------------------

def gen_rules_errata():
    src = ROOT / "rules/content/rules/arcs/en-US/errata.yml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    fixtures = []
    for i, entry in enumerate(data):
        sections = entry.get("rules", [])
        text = entry["text"].strip()
        section_label = sections[0] if sections else f"entry {i+1}"
        fixture = {
            "id": f"rules-errata-{i+1:03d}",
            "source": "rules/content/rules/arcs/en-US/errata.yml",
            "rule_sections": sections,
            "canonical_errata_text": text,
            "question": f"Is there any errata for rule section {section_label}?",
            "checks": {
                "must_cite_errata": True,
                "must_mention_keywords": extract_keywords(text),
                "must_not_contain_raw_tokens": True,
            },
        }
        if sections:
            fixture["checks"]["must_cite_section"] = sections[0]
        fixtures.append(fixture)
    _write(OUT / "rules-errata.json", fixtures)
    print(f"  rules-errata.json: {len(fixtures)} entries")


# ---------------------------------------------------------------------------
# Card errata
# ---------------------------------------------------------------------------

def gen_card_errata():
    src = ROOT / "cards/content/errata/arcs/en-US.yml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    fixtures = []
    for block in data:
        card = block["card"]
        for j, entry in enumerate(block["errata"]):
            text = entry["text"].strip()
            links = find_links(text)
            checks = {
                "must_cite_errata": True,
                "must_name_card": card,
                "must_mention_keywords": extract_keywords(text),
                "must_not_contain_raw_tokens": True,
            }
            if links:
                checks["must_resolve_links"] = links
            fixture = {
                "id": f"card-errata-{slugify(card)}-{j+1:03d}",
                "source": "cards/content/errata/arcs/en-US.yml",
                "card_name": card,
                "canonical_errata_text": text,
                "question": f"Is there any errata for the card \"{card}\"?",
                "checks": checks,
            }
            fixtures.append(fixture)
    _write(OUT / "card-errata.json", fixtures)
    print(f"  card-errata.json: {len(fixtures)} entries")


# ---------------------------------------------------------------------------
# Card name recognition (sampled)
# ---------------------------------------------------------------------------

def gen_card_names():
    src = ROOT / "skill/arcs-rules/card-index.txt"
    lines = [l for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Parse: name \t product \t id \t url
    by_product: dict[str, list] = {}
    multi: list = []
    seen_names: dict[str, list] = {}
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name, product, card_id, url = parts[0], parts[1], parts[2], parts[3]
        if name not in seen_names:
            seen_names[name] = []
        seen_names[name].append({"product": product, "id": card_id, "url": url})
        by_product.setdefault(product, []).append((name, product, card_id, url))

    # 10 per product + all multi-product cards (capped at 20)
    selected = []
    for product, cards in by_product.items():
        selected.extend(cards[:10])

    multi_cards = [(n, entries) for n, entries in seen_names.items() if len(entries) > 1]
    selected_multi = multi_cards[:20]

    fixtures = []
    seen_ids = set()

    for name, product, card_id, url in selected:
        if card_id in seen_ids:
            continue
        seen_ids.add(card_id)
        products = [e["product"] for e in seen_names[name]]
        checks = {
            "must_name_card": name,
            "must_cite_card_url": True,
        }
        if len(products) > 1:
            checks["multi_product"] = True
            checks["must_distinguish_versions"] = True
        fixtures.append({
            "id": f"card-name-{slugify(name)}-{slugify(product)}",
            "card_name": name,
            "products": products,
            "card_ids": [e["id"] for e in seen_names[name]],
            "question": f"How does {name} work?",
            "checks": checks,
        })

    for name, entries in selected_multi:
        card_id = entries[0]["id"]
        if card_id in seen_ids:
            continue
        seen_ids.add(card_id)
        products = [e["product"] for e in entries]
        fixtures.append({
            "id": f"card-name-{slugify(name)}-multi",
            "card_name": name,
            "products": products,
            "card_ids": [e["id"] for e in entries],
            "question": f"How does {name} work?",
            "checks": {
                "must_name_card": name,
                "must_cite_card_url": True,
                "multi_product": True,
                "must_distinguish_versions": True,
            },
        })

    _write(OUT / "card-names.json", fixtures)
    print(f"  card-names.json: {len(fixtures)} entries")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: pathlib.Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    print("Generating fixtures...")
    gen_rules_faq()
    gen_card_faq()
    gen_rules_errata()
    gen_card_errata()
    gen_card_names()
    print("Done.")
