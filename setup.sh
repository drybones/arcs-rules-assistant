#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Clone or update content repos
if [ -d cards ]; then git -C cards pull; else git clone https://github.com/buriedgiantstudios/cards.git cards; fi
if [ -d rules ]; then git -C rules pull; else git clone https://github.com/buriedgiantstudios/rules.git rules; fi

# Build indexes
python3 skill/generate-card-index.py
python3 skill/generate-rules-index.py

# Install skill
mkdir -p ~/.claude/skills
cp -r skill/arcs-rules ~/.claude/skills/

echo "Setup complete. Restart Claude Code and use /arcs-rules <question>."
