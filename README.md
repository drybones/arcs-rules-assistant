# Arcs Rules Assistant

A rules assistant for the board game **[Arcs](https://buriedgiant.com/arcs)** by Buried Giant Studios, covering the base game, the Blighted Reach campaign expansion, and Leaders & Lore.

Ask it rules questions, card interactions, setup questions, or errata lookups. Answers cite official sources — rulebook, card text, FAQ, and errata — and fall back to community sources (BGG, r/Arcs) for genuinely ambiguous rulings.

## How it works

The assistant runs as a **[Claude Code](https://claude.ai/code) skill** on your machine. One player at the table runs it locally; others ask questions verbally or via group chat and the operator relays answers.

Content is read from local clones of the official [Buried Giant cards repo](https://github.com/buriedgiantstudios/cards) and [rules repo](https://github.com/buriedgiantstudios/rules), so responses are fast and consistent without hitting the web on every query.

## Setup

You need [Claude Code](https://claude.ai/code), [Python 3](https://python.org), and [PyYAML](https://pypi.org/project/PyYAML/) (`pip install pyyaml`).

Clone this repo, then run the setup script from the repo root. It clones the content repos, installs the skill into Claude Code, and builds the search indexes.

**Mac/Linux:**
```bash
git clone https://github.com/drybones/arcs-rules-assistant.git
cd arcs-rules-assistant
bash setup.sh
```

**Windows:**
```powershell
git clone https://github.com/drybones/arcs-rules-assistant.git
cd arcs-rules-assistant
.\setup.ps1
```

Then restart Claude Code.

## Usage

Open Claude Code in the `arcs-rules-assistant` directory and ask:

```
/arcs-rules Can I build in a system I just raided?
/arcs-rules How does the Blighted Reach Warlord card work?
/arcs-rules What happens if two players tie for an ambition?
```

## Keeping content up to date

When Buried Giant publishes new printings or errata, pull both repos and regenerate the indexes:

**Mac/Linux:**
```bash
git -C cards pull && git -C rules pull && bash setup.sh
```

**Windows:**
```powershell
git -C cards pull; git -C rules pull; .\setup.ps1
```

## Sources

| Source | What it covers |
|--------|---------------|
| `rules/content/rules/arcs/en-US/p1/rules.yml` | Full rulebook — base game and Blighted Reach |
| `rules/content/rules/arcs/en-US/p1/faq.yml` | Rules-level Q&A |
| `rules/content/rules/arcs/en-US/errata.yml` | Rules errata |
| `cards/content/card-data/arcs/en-US/` | Card definitions for all three products |
| `cards/content/faq/arcs/en-US.yml` | Per-card FAQ |
| `cards/content/errata/arcs/en-US.yml` | Card errata |

Community fallback: [BGG forums](https://boardgamegeek.com/boardgame/359871/arcs/forums/0) and [r/Arcs](https://www.reddit.com/r/Arcs/), used only when official sources don't resolve the question.
