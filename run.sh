#!/bin/bash
# Quick run script for the IF engine

# Check if API key is set
if [ -z "$GEMINI_API_KEY" ]; then
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo "Error: GEMINI_API_KEY not set and no .env file found"
        echo "Please set GEMINI_API_KEY or create a .env file"
        exit 1
    fi
fi

# Run the game with poetry if available, otherwise use python
if command -v poetry &> /dev/null; then
    poetry run python -m src.main "$@"
else
    python -m src.main "$@"
fi
