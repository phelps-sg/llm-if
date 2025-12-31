"""Prototype: ZIL Interpreter Bridge with LLM Command Mapping

This prototype demonstrates a hybrid architecture where:
1. ZIL interpreter maintains game state (source of truth)
2. LLM maps natural language to standard Infocom commands
3. LLM enhances narration of ZIL results

Usage:
    python prototype_zil_bridge.py

This tests the LLM's ability to map NL → IF commands without needing
the actual ZIL interpreter running.
"""

import os
from src.llm.gemini_client import GeminiClient
from src.config import DEFAULT_DM_MODEL


class ZILCommandMapper:
    """Maps natural language input to Infocom-style commands using LLM."""

    def __init__(self, llm_client: GeminiClient):
        self.llm = llm_client

    def map_nl_to_command(self, player_input: str, game_context: dict) -> dict:
        """Map natural language to Infocom command.

        Args:
            player_input: Natural language from player (e.g., "spit at blather")
            game_context: Current game state context {
                'location': location name/description,
                'objects': list of visible objects,
                'npcs': list of NPCs present,
                'inventory': list of items in inventory,
                'exits': list of available directions
            }

        Returns:
            {
                'command': Infocom command string (e.g., "SPIT AT BLATHER"),
                'confidence': float 0-1,
                'reasoning': explanation of mapping
            }
        """
        prompt = self._build_mapping_prompt(player_input, game_context)

        # Use LLM to generate structured command mapping
        from vertexai.generative_models import GenerationConfig
        import json

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING"},
                "confidence": {"type": "NUMBER"},
                "reasoning": {"type": "STRING"}
            },
            "required": ["command", "confidence", "reasoning"]
        }

        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.1,  # Low temperature for consistent mapping
        )

        response = self.llm.model.generate_content(prompt, generation_config=generation_config)
        result = json.loads(response.text)

        return result

    def _build_mapping_prompt(self, player_input: str, context: dict) -> str:
        """Build prompt for NL → IF command mapping."""
        location = context.get('location', 'Unknown')
        objects = context.get('objects', [])
        npcs = context.get('npcs', [])
        inventory = context.get('inventory', [])
        exits = context.get('exits', [])

        return f"""You are translating natural language player input into classic Infocom text adventure commands.

CURRENT GAME CONTEXT:
Location: {location}
Visible Objects: {', '.join(objects) if objects else '(none)'}
NPCs Present: {', '.join(npcs) if npcs else '(none)'}
Inventory: {', '.join(inventory) if inventory else '(empty)'}
Available Exits: {', '.join(exits) if exits else '(none)'}

STANDARD INFOCOM COMMAND PATTERNS:
- Movement: NORTH, SOUTH, EAST, WEST, UP, DOWN, IN, OUT, etc.
- Inventory: INVENTORY (or I), TAKE <object>, DROP <object>
- Interaction: EXAMINE <object>, OPEN <object>, CLOSE <object>
- Two-word verbs: PUT <obj> IN <container>, ATTACK <npc> WITH <weapon>
- Communication: ASK <npc> ABOUT <topic>, TELL <npc> ABOUT <topic>
- Unusual verbs: SPIT AT <npc>, THROW <obj> AT <target>, SHAKE <obj>

PLAYER INPUT: "{player_input}"

YOUR TASK:
Map the player's natural language to a standard Infocom command.
- Use UPPERCASE for the command
- Use exact object/NPC names from context when possible
- Handle synonyms (e.g., "chuck" → THROW, "inspect" → EXAMINE)
- If direction is implicit (e.g., "go through door"), infer from exits
- Give confidence 0-1 based on how certain the mapping is

EXAMPLES:
Input: "spit at blather" → {{"command": "SPIT AT BLATHER", "confidence": 0.95}}
Input: "look at my watch" → {{"command": "EXAMINE CHRONOMETER", "confidence": 0.9}}
Input: "go north" → {{"command": "NORTH", "confidence": 1.0}}
Input: "chuck the nest" → {{"command": "THROW NEST", "confidence": 0.85}}
Input: "what's in my bag?" → {{"command": "INVENTORY", "confidence": 0.9}}

Return the mapped command with confidence and reasoning.
"""


def test_command_mapping():
    """Test the LLM's ability to map NL to IF commands."""
    print("="*70)
    print("PROTOTYPE: ZIL Bridge with LLM Command Mapping")
    print("="*70)

    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        print("ERROR: GCP_PROJECT environment variable not set")
        return

    print("\nInitializing LLM client...")
    llm = GeminiClient(project=gcp_project, model_name=DEFAULT_DM_MODEL)
    mapper = ZILCommandMapper(llm)

    # Test cases from Planetfall scenario
    test_cases = [
        {
            "input": "spit at blather",
            "context": {
                "location": "Deck Nine",
                "objects": ["escape pod bulkhead", "wide bulkhead", "stairway"],
                "npcs": ["Ensign First Class Blather"],
                "inventory": ["scrub brush", "chronometer", "uniform", "diary"],
                "exits": ["east", "west", "up", "in"]
            },
            "expected": "SPIT AT BLATHER"
        },
        {
            "input": "look at my watch",
            "context": {
                "location": "Reactor Lobby",
                "objects": [],
                "npcs": ["Ensign First Class Blather"],
                "inventory": ["scrub brush", "chronometer", "uniform", "diary"],
                "exits": ["north", "south", "east", "west"]
            },
            "expected": "EXAMINE CHRONOMETER"
        },
        {
            "input": "go west",
            "context": {
                "location": "Reactor Lobby",
                "objects": [],
                "npcs": [],
                "inventory": ["scrub brush", "chronometer"],
                "exits": ["north", "south", "east", "west"]
            },
            "expected": "WEST"
        },
        {
            "input": "check my inventory",
            "context": {
                "location": "Deck Nine",
                "objects": [],
                "npcs": [],
                "inventory": ["scrub brush", "chronometer", "uniform"],
                "exits": ["east", "west"]
            },
            "expected": "INVENTORY"
        },
        {
            "input": "use the scrub brush on the deck",
            "context": {
                "location": "Reactor Lobby",
                "objects": ["deck"],
                "npcs": ["Ensign First Class Blather"],
                "inventory": ["scrub brush", "chronometer"],
                "exits": ["north", "south", "east", "west"]
            },
            "expected": "SCRUB DECK WITH BRUSH"  # Game-specific verb
        }
    ]

    print("\n" + "="*70)
    print("TESTING COMMAND MAPPING")
    print("="*70)

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}/{len(test_cases)} ---")
        print(f"Input: \"{test['input']}\"")
        print(f"Expected: {test['expected']}")

        result = mapper.map_nl_to_command(test['input'], test['context'])

        print(f"Mapped to: {result['command']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reasoning: {result['reasoning']}")

        matches = result['command'] == test['expected']
        print(f"✅ MATCH" if matches else f"❌ MISMATCH")

        results.append({
            'test': test,
            'result': result,
            'matches': matches
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    matches = sum(1 for r in results if r['matches'])
    print(f"Exact matches: {matches}/{len(test_cases)}")
    print(f"Success rate: {matches/len(test_cases)*100:.1f}%")

    avg_confidence = sum(r['result']['confidence'] for r in results) / len(results)
    print(f"Average confidence: {avg_confidence:.2f}")

    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    if matches == len(test_cases):
        print("✅ Perfect mapping! LLM can reliably map NL to IF commands.")
    elif matches >= len(test_cases) * 0.8:
        print("⚠️  Good but not perfect. LLM mostly succeeds at mapping.")
    else:
        print("❌ Poor mapping. This approach may not be viable.")

    print("\nMismatches:")
    for r in results:
        if not r['matches']:
            print(f"  • '{r['test']['input']}' → {r['result']['command']} (expected {r['test']['expected']})")

    return results


if __name__ == "__main__":
    test_command_mapping()
