#!/bin/bash
# run_simulation.sh
# Run TuniLoon mock payload simulation

echo "========================================"
echo "  TuniLoon Mock Payload Simulation"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!"
    exit 1
fi

# Check requirements
echo "[1/3] Checking requirements..."
if ! python3 -c "import serial" 2>/dev/null; then
    echo "WARNING: pyserial not installed. Run: pip install -r requirements.txt"
fi

# Get arguments
MODE=${1:-"print"}  # "print" or "serial"
INTERVAL=${2:-30}   # Transmission interval in seconds

echo "[2/3] Starting simulation..."
echo "  Mode: $MODE"
echo "  Interval: $INTERVAL seconds"
echo ""

# Run the simulation
cd "$(dirname "$0")/.." || exit

if [ "$MODE" = "serial" ]; then
    python3 -m payload_simulator.src.MockPayload --serial --interval "$INTERVAL"
else
    python3 -m payload_simulator.src.MockPayload --interval "$INTERVAL"
fi

echo ""
echo "[3/3] Simulation complete!"
