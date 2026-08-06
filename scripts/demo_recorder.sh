#!/bin/bash
# demo_recorder.sh
# Record a demo video of the TuniLoon system

echo "====================================="
echo "  TuniLoon Demo Recorder"
echo "====================================="
echo ""

# Check if asciinema is installed
if ! command -v asciinema &> /dev/null; then
    echo "ERROR: asciinema not found. Install it with:"
    echo "  pip install asciinema"
    exit 1
fi

# Create recordings directory
mkdir -p recordings

echo "[INFO] Starting demo recording..."
echo "[INFO] This will record the terminal session"
echo "[INFO] Press Ctrl+D to stop recording"
echo ""

# Record the terminal session
asciinema rec recordings/demo_$(date +%Y%m%d_%H%M%S).cast

echo ""
echo "[INFO] Recording saved to recordings/"
echo "[INFO] You can upload to asciinema.org or convert to GIF"
