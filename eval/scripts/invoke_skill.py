"""
Invoke the arcs-rules skill via the Anthropic SDK with all source files pre-loaded.
Approximates the skill's behavior without the Claude Code harness.

Usage:
    from eval.scripts.invoke_skill import invoke, build_client
    client = build_client()
    response = invoke("How does ambition work?", client)

Token budget per call (approximate):
    Rules-only context  ~30K tokens  (rules.yml + faq + errata + indices + primers)
    Full context        ~107K tokens (adds card data + card FAQ + card errata)

The 'with_cards' parameter controls which context to load. Pass False for questions
that don't mention a specific card — this keeps calls well under typical rate limits.
Pass True (or omit) for card-related questions.
"""

import os
import pathlib
import re

import anthropic

ROOT = pathlib.Path(__file__).parent.parent.parent

_RULES_FILES = [
    ("rules_index", ROOT / "skill/arcs-rules/rules-index.txt"),
    ("card_index", ROOT / "skill/arcs-rules/card-index.txt"),
    ("primer_base_game", ROOT / "skill/arcs-rules/primer-base-game.md"),
    ("primer_expansion", ROOT / "skill/arcs-rules/primer-expansion.md"),
    ("rules_yml", ROOT / "rules/content/rules/arcs/en-US/p1/rules.yml"),
    ("faq_yml", ROOT / "rules/content/rules/arcs/en-US/p1/faq.yml"),
    ("errata_yml", ROOT / "rules/content/rules/arcs/en-US/errata.yml"),
]

_CARD_FILES = [
    ("card_faq_yml", ROOT / "cards/content/faq/arcs/en-US.yml"),
    ("card_errata_yml", ROOT / "cards/content/errata/arcs/en-US.yml"),
    ("base_cards_yml", ROOT / "cards/content/card-data/arcs/en-US/arcsbasegame.yml"),
    ("br_cards_yml", ROOT / "cards/content/card-data/arcs/en-US/blightedreach.yml"),
    ("ll_cards_yml", ROOT / "cards/content/card-data/arcs/en-US/leaders-lore.yml"),
]

_SKILL_MD = ROOT / "skill/arcs-rules/SKILL.md"

# Load card names once for heuristic detection
_card_names: set[str] = set()

def _get_card_names() -> set[str]:
    if not _card_names:
        idx = ROOT / "skill/arcs-rules/card-index.txt"
        for line in idx.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if parts:
                _card_names.add(parts[0].lower())
    return _card_names

# Cache content blocks to avoid re-reading disk on every call
_cache: dict[str, str] = {}


def _load_block(with_cards: bool) -> str:
    key = "full" if with_cards else "rules"
    if key in _cache:
        return _cache[key]

    files = _RULES_FILES + (_CARD_FILES if with_cards else [])
    parts = [f"<{tag}>\n{path.read_text(encoding='utf-8')}\n</{tag}>" for tag, path in files]
    _cache[key] = "\n\n".join(parts)
    return _cache[key]


def needs_card_context(question: str) -> bool:
    """Heuristic: does this question likely need card file context?"""
    q = question.lower()
    card_keywords = {"card", "ability", "guild", "lore card", "leader", "fate",
                     "edict", "event", "regent", "outlaw", "flagship"}
    if any(kw in q for kw in card_keywords):
        return True
    # Check against known card names
    names = _get_card_names()
    words = set(re.findall(r"[a-z']+", q))
    # Single-word card name match
    if words & names:
        return True
    # Two-word card name match
    tokens = q.split()
    bigrams = {f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)}
    return bool(bigrams & names)


def _build_system() -> str:
    """Return the static skill instructions (no question injected).
    The question arrives via the user message; keeping this block identical
    across all calls is what allows the corpus cache_control block to hit."""
    if "system" in _cache:
        return _cache["system"]
    skill_text = _SKILL_MD.read_text(encoding="utf-8")
    if skill_text.startswith("---"):
        _, _, skill_text = skill_text.split("---", 2)
    # Remove the $ARGUMENTS line — the question is in the user message instead.
    # Leaving it would make this block different on every call, busting the cache.
    skill_text = re.sub(r"The question to answer is:.*?\n\n", "", skill_text, flags=re.DOTALL)
    _cache["system"] = skill_text.strip()
    return _cache["system"]


def build_client() -> anthropic.Anthropic:
    # extended-cache-ttl-2025-04-11 unlocks the 1-hour cache TTL option.
    # We need this because at low TPM tiers the rate-limit pause between calls
    # (often >5 min for a 200K-token corpus) would expire the default 5-min cache.
    return anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        default_headers={"anthropic-beta": "extended-cache-ttl-2025-04-11"},
    )


def invoke(
    question: str,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2048,
    with_cards: bool | None = None,
) -> tuple[str, int]:
    """
    Invoke the skill for a single question.
    Returns (response_text, total_input_tokens) where total_input_tokens is
    the sum of all input tokens charged (cache write + cache read + uncached).
    Use this count — not estimates — to calculate rate-limit delays.

    with_cards=None  auto-detect from question text (default)
    with_cards=True  always include card files (~107K tokens)
    with_cards=False always use rules-only context (~30K tokens)
    """
    if with_cards is None:
        with_cards = needs_card_context(question)

    system_instruction = _build_system()
    content_block = _load_block(with_cards)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {"type": "text", "text": system_instruction},
            {
                "type": "text",
                "text": content_block,
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
        ],
        messages=[{"role": "user", "content": question}],
    )

    usage = response.usage
    usage_info = {
        "input_tokens": usage.input_tokens or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "output_tokens": usage.output_tokens or 0,
    }
    usage_info["total_input"] = (
        usage_info["input_tokens"]
        + usage_info["cache_read_input_tokens"]
        + usage_info["cache_creation_input_tokens"]
    )
    return response.content[0].text, usage_info
