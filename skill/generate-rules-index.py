"""
Regenerate skill/arcs-rules/rules-index.txt from the rules repo YAML file.
Run this from the project root after any git pull in the rules/ repo:

    python skill/generate-rules-index.py

Anchors use the raw section index (e.g. #3.1.2) rather than the slugTitle hash.
The rules site renders a <span id="rule.index"> for every section unconditionally,
making these anchors reliable regardless of how the JS slugify library handles
special characters in section names.

Depth-4+ sections (e.g. 20.3.4.3) have a known race condition on the rules site:
the app fires its hash-scroll after a 1500ms timeout, but the page component is
lazy-loaded via a plain Subject (no replay), so the scroll event can be lost on
slower connections. For these sections, link_url points to the depth-3 ancestor
instead (e.g. 20.3.4), which is a stable landing point. The section's own URL
is still recorded for reference.
"""
import yaml
import pathlib
import re

RULES_URL_BASE = "https://rules.buriedgiant.com/?product=arcs&locale=en-US&printing=p1"

rules_file = pathlib.Path(__file__).parent.parent / "rules/content/rules/arcs/en-US/p1/rules.yml"
out = pathlib.Path(__file__).parent / "arcs-rules" / "rules-index.txt"


def strip_markup(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def index_depth(index: str) -> int:
    """Return the nesting depth of a section index.
    Top-level indices end with a dot (e.g. '3.') and have depth 1.
    Child indices are dot-separated without a trailing dot (e.g. '3.1.2' = depth 3).
    """
    if index.endswith("."):
        return 1
    return len(index.split("."))


def walk(rules, prefix_parts):
    entries = []
    for i, rule in enumerate(rules):
        parts = prefix_parts + [str(i + 1)]
        # Top-level sections get a trailing dot in their index (matches the app)
        index = ".".join(parts) + ("." if len(parts) == 1 else "")
        name = strip_markup(rule.get("name") or "")
        url = f"{RULES_URL_BASE}#{index}"
        entries.append((index, name, url))
        if rule.get("children"):
            entries.extend(walk(rule["children"], parts))
    return entries


def depth3_ancestor_index(index: str) -> str:
    """Return the depth-3 ancestor index for a depth-4+ section.
    e.g. '20.3.4.3' -> '20.3.4'
    """
    parts = index.split(".")
    return ".".join(parts[:3])


rules_data = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
entries = walk(rules_data, [])

# Build a lookup of index -> url for ancestor resolution
url_by_index = {index: url for index, name, url in entries}

lines = [
    "# Arcs rules section index — auto-generated from rules/content/rules/arcs/en-US/p1/rules.yml",
    "# Regenerate with: python skill/generate-rules-index.py",
    "# Fields (tab-separated): section_number | section_name | url | link_url",
    "# link_url: use this for hyperlinks. For depth-4+ sections it points to the",
    "#   depth-3 ancestor to avoid a race-condition bug in the rules site's hash",
    "#   navigation. url always points to the section itself.",
    "",
]

for index, name, url in entries:
    if index_depth(index) >= 4:
        ancestor = depth3_ancestor_index(index)
        link_url = url_by_index.get(ancestor, url)
    else:
        link_url = url
    lines.append(f"{index}\t{name}\t{url}\t{link_url}")

out.write_text("\n".join(lines), encoding="utf-8")
print(f"Written {len(entries)} rule sections to {out}")
