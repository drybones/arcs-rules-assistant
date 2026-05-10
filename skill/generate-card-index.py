"""
Regenerate skill/arcs-rules/card-index.txt from the cards repo YAML files.
Run this from the project root after any git pull in the cards/ repo:

    python skill/generate-card-index.py
"""
import yaml
import pathlib

CARDS_URL_BASE = "https://cards.buriedgiant.com/card"

base = pathlib.Path(__file__).parent.parent / "cards/content/card-data/arcs/en-US"
out = pathlib.Path(__file__).parent / "arcs-rules" / "card-index.txt"

sources = [
    ("arcsbasegame.yml", "Base"),
    ("blightedreach.yml", "Blighted Reach"),
    ("leaders-lore.yml", "Leaders & Lore"),
]

cards = []
for filename, label in sources:
    data = yaml.safe_load((base / filename).read_text(encoding="utf-8"))
    for card in data:
        if "name" in card and "id" in card:
            url = f"{CARDS_URL_BASE}/{card['id']}"
            cards.append((card["name"], label, card["id"], url))

cards.sort(key=lambda x: x[0])

lines = [
    "# Arcs card name index — auto-generated from cards/content/card-data/arcs/en-US/",
    "# Regenerate with: python skill/generate-card-index.py",
    "# Fields (tab-separated): card name | product | card id | url",
    "",
]
for name, label, card_id, url in cards:
    lines.append(f"{name}\t{label}\t{card_id}\t{url}")

out.write_text("\n".join(lines), encoding="utf-8")
print(f"Written {len(cards)} cards to {out}")
