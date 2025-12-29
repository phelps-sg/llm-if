#!/bin/bash
# Test god mode with Trinity

echo "Testing god mode..."
echo ""
echo "Commands to test:"
echo "/inventory"
echo "/inspect coin"
echo "/state"
echo "quit"
echo ""

# Run Trinity with god mode
poetry run python -m src.main worlds/trinity.json --god-mode <<EOF
/inventory
/inspect coin
/state
quit
EOF
