#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# ANet Exit Ticket Studio — First-time setup for Mac
# Run once: open Terminal, type bash + drag setup.sh onto window, press Enter
# ──────────────────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "══════════════════════════════════════════════════"
echo "  ANet Exit Ticket Studio — Setup (Mac)"
echo "══════════════════════════════════════════════════"
echo ""

# ── Python check ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌  Python 3 not found. Download from https://python.org"
    exit 1
fi
PY_FULL=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "❌  Python $PY_FULL found — version 3.9+ required. Download from https://python.org"
    exit 1
fi
echo "✅  Python $PY_FULL"

# ── Virtual environment ────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "📦  Creating virtual environment…"
    python3 -m venv venv
fi
source venv/bin/activate

# ── Install packages ───────────────────────────────────────────────────────────
echo "📦  Installing packages (may take a minute)…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "✅  Packages installed"

# ── PNG export check (optional — SVG visuals always work regardless) ──────────
echo ""
if python3 -c "import cairosvg" &>/dev/null; then
    echo "✅  PNG export available (Cairo found)"
else
    echo "⚠️   PNG export unavailable — visuals will still work as SVG everywhere."
    echo "     To enable PNG export too, run:  brew install cairo"
    echo "     (then re-run this setup script)"
fi

# ── Output folder ──────────────────────────────────────────────────────────────
[ ! -d "output" ] && mkdir -p output && echo "📁  Created output/ — generated lessons will be saved here"

# ── API key ────────────────────────────────────────────────────────────────────
echo ""
echo "🔑  API Key Setup"
read -rp "    Anthropic API key (claude.ai → Settings → API Keys): " ANT_KEY
cat > "$SCRIPT_DIR/.env" <<EOF
ANTHROPIC_API_KEY=$ANT_KEY
EOF
echo "✅  Key saved to .env"

# ── Make launcher executable ───────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/launch.command"
echo "✅  launch.command is ready"

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✅  Setup complete!"
echo "  → Double-click launch.command to start the app"
echo "══════════════════════════════════════════════════"
echo ""
