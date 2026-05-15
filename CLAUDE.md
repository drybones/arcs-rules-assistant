# Arcs Rules Assistant

Run `/arcs-rules <question>` for rules questions about the board game Arcs (base game, Blighted Reach, Leaders & Lore).

Content is read from `rules/` and `cards/` (local repo clones, git-ignored).

To update content after new printings or errata, re-run the setup script from this directory:

```powershell
.\setup.ps1   # Windows
bash setup.sh  # Mac/Linux
```

For strategy questions about specific fates, read from the relevant primer in `guides/` (e.g. `guides/admiral-primer.md`). 

Developer documentation is in [DEVELOPMENT.md](DEVELOPMENT.md).
