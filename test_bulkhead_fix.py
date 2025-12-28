#!/usr/bin/env python3
"""Test the bulkhead door fix."""

import sys
sys.path.insert(0, '/Users/Steve.Phelps/vcs/coding/llm-if')

from src.models.game_state import GameState
from src.main import main

# Test the deck nine location description
print("=" * 80)
print("TESTING BULKHEAD DOOR FIX")
print("=" * 80)
print("\nRunning: poetry run python -m src.main worlds/planetfall.json --single-step 'look' --save-file /tmp/test_bulkhead.json")
print("\nExpected: The description should indicate bulkheads are OPEN or corridors are accessible")
print("NOT expected: 'blocked by closed bulkheads'\n")
print("=" * 80)
