$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Clone content repos
if (-not (Test-Path cards)) { git clone https://github.com/buriedgiantstudios/cards.git cards }
if (-not (Test-Path rules)) { git clone https://github.com/buriedgiantstudios/rules.git rules }

# Install skill
$skillsDir = Join-Path $HOME ".claude\skills"
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
Copy-Item -Path "skill\arcs-rules" -Destination $skillsDir -Recurse -Force

# Build indexes
python skill/generate-card-index.py
python skill/generate-rules-index.py

Write-Host "Setup complete. Restart Claude Code and use /arcs-rules <question>."
