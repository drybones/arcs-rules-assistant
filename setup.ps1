$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Clone or update content repos
if (Test-Path cards) { git -C cards pull } else { git clone https://github.com/buriedgiantstudios/cards.git cards }
if (Test-Path rules) { git -C rules pull } else { git clone https://github.com/buriedgiantstudios/rules.git rules }

# Build indexes
python skill/generate-card-index.py
python skill/generate-rules-index.py

# Install skill
$skillsDir = Join-Path $HOME ".claude\skills"
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
Copy-Item -Path "skill\arcs-rules" -Destination $skillsDir -Recurse -Force

Write-Host "Setup complete. Restart Claude Code and use /arcs-rules <question>."
