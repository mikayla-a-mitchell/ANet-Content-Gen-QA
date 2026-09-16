#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    read -rp "Press Enter to close..."
    exit 1
fi
source venv/bin/activate
echo "Starting ANet Exit Ticket Studio — your browser will open shortly…"
streamlit run app.py --server.headless false
