# Arcs Rules Assistant

A rules assistant for the board game **Arcs** by Buried Giant Studios, covering the base game, the Blighted Reach campaign expansion, and the Leaders & Lore expansion.

The assistant answers rules questions by consulting official sources — rulebook, card text, FAQ, and errata — in priority order, and falls back to community sources (BGG forums, r/Arcs) for genuinely ambiguous or unresolved questions.

## Current implementation: Claude Code skill

The skill lives in `skill/arcs-rules/SKILL.md`. It is designed to be channelled through a single player at the table who runs Claude Code locally. Other players ask questions verbally or via group chat; the operator enters them and relays answers.

Clone this repo, then run the setup script from the repo root. It clones the content repos, installs the skill, and builds the search indexes:

**Mac/Linux:**
```bash
bash setup.sh
```

**Windows:**
```powershell
.\setup.ps1
```

Then invoke it with `/arcs-rules <question>` inside any Claude Code session opened at this project root.

Content is read from local cloned repos rather than fetching the web on every query — this keeps responses fast and consistent.

## Content sources

All content is Arcs-specific. The repos also contain rules and cards for other Buried Giant games (Oath, Pax Pamir, John Company); those are ignored.

### Cloned repos (primary, authoritative)

| Path | What it contains |
|------|-----------------|
| `rules/content/rules/arcs/en-US/p1/rules.yml` | Full rulebook — base game and Blighted Reach combined, 2,807 lines |
| `rules/content/rules/arcs/en-US/p1/faq.yml` | Rules-level Q&A, 264 lines, with rule section cross-references |
| `rules/content/rules/arcs/en-US/errata.yml` | Rules errata with section references |
| `cards/content/card-data/arcs/en-US/arcsbasegame.yml` | Base game card definitions |
| `cards/content/card-data/arcs/en-US/blightedreach.yml` | Blighted Reach card definitions (212 KB — the largest file) |
| `cards/content/card-data/arcs/en-US/leaders-lore.yml` | Leaders & Lore card definitions |
| `cards/content/faq/arcs/en-US.yml` | Card-level FAQ, 1,190 lines of Q&A per card |
| `cards/content/errata/arcs/en-US.yml` | Card errata, 197 entries |

Refresh both repos with `git pull` inside `cards/` and `rules/` when new printings or errata are published, then regenerate the indexes:

```bash
git -C cards pull
git -C rules pull
python3 skill/generate-card-index.py   # Mac/Linux
python3 skill/generate-rules-index.py
```

```powershell
git -C cards pull
git -C rules pull
python skill/generate-card-index.py   # Windows
python skill/generate-rules-index.py
```

### Community fallback sources

Used only when the official sources don't resolve the question or when the question is about community interpretation of an ambiguous rule.

- **BGG forums**: https://boardgamegeek.com/boardgame/359871/arcs/forums/0
- **Reddit**: https://www.reddit.com/r/Arcs/

### Authoritative context

- Arcs was originally published by **Leder Games**. It is now owned and published by **Buried Giant Studios**. Buried Giant resources are authoritative; Leder Games resources are historical and may be outdated.
- The Buried Giant card library: https://cards.buriedgiant.com
- The Buried Giant rules site: https://rules.buriedgiant.com

## YAML format notes

**Card YAML fields**: `id`, `name`, `tags` (includes product tag: `Base`, `Blighted Reach`, `Leaders`), `text` (markdown with `$link:CardName$` cross-references and `$symbol:text$` tokens), `meta` (keys, act, complexity), `flipSide`.

**Rules YAML structure**: Hierarchical sections with `name`, `pretext`, `text`, and `children`. Errata entries reference rule sections by number (e.g. `'3.1.2.6'`). FAQ entries reference rule sections in a `rules` array.

**Cross-references**: `$link:CardName$` in card text refers to another card by name. `rules: ['5.']` in FAQ entries refers to rule section numbers. A thorough answer should resolve these rather than surface the raw token.

## Future: API app

If the single-operator model becomes a bottleneck, the natural next step is a small API app so every player can query independently from their own device.

The app would:
- Parse all YAML files at startup into an in-memory index
- Expose Claude API tool use: `lookup_card(name)`, `search_rules(query)`, `get_faq(topic)`, `get_errata(card_or_section)`
- Cache the full corpus using the Anthropic prompt cache (430 KB ≈ 107K tokens; ~$0.032 per cached query on Sonnet 4.6)
- Fall back to targeted BGG/Reddit web search when official sources don't resolve the question
- Be served as a simple web UI, accessible by URL from any device

Estimated cost at casual group usage: **$50–100/month** on Sonnet 4.6, or roughly 10× cheaper on Haiku 4.5.

Stack candidates: Python + FastAPI + a minimal HTML/JS front-end, or TypeScript + Hono. Hosting: anywhere the operator already has capacity.
