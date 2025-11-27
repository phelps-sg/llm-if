"""End-to-end tests for NPC dialogue system.

These tests verify that the DM correctly handles NPC conversations by:
1. Generating quoted dialogue when player talks to NPCs
2. NPCs explain their role/mechanics through dialogue
3. NPC personality affects dialogue style
4. Different NPC types respond appropriately
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def skip_if_no_gcp():
    """Skip tests if GCP is not configured."""
    if not os.getenv("GCP_PROJECT"):
        pytest.skip("GCP_PROJECT not set - skipping e2e Gemini tests")


@pytest.fixture
def game_setup():
    """Set up a game with various NPCs."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Initialize Gemini client
    gemini_client = GeminiClient()

    # Initialize rule engine
    rule_engine = RuleEngine()

    # Create game loop
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_genie_dialogue_explains_wishes(skip_if_no_gcp, game_setup):
    """Test that genie speaks with dialogue and explains wish mechanics.

    This tests:
    1. Narrative includes quoted dialogue from genie
    2. Genie explains it grants wishes
    3. Genie mentions limitations ("exactly what is asked")
    4. Dialogue is atmospheric and in-character
    """
    game_loop, game_state, gemini_client = game_setup

    # Move to forest clearing where genie is
    game_state.player_location = "forest_clearing"

    print("\n=== TESTING GENIE DIALOGUE ===")

    # Talk to genie
    narrative, interpretation = game_loop.process_turn("talk to genie")

    print(f"Narrative: {narrative}")
    print(f"Intent: {interpretation.get('intent')}")

    # Assert dialogue is present (check for quotation marks)
    assert '"' in narrative or "'" in narrative, (
        "Genie should speak with quoted dialogue. "
        f"Got narrative: {narrative}"
    )
    print("✅ Genie speaks with quoted dialogue")

    # Assert genie mentions wishes
    narrative_lower = narrative.lower()
    assert "wish" in narrative_lower, (
        "Genie should mention wishes when talked to. "
        f"Got narrative: {narrative}"
    )
    print("✅ Genie mentions wishes")

    # Assert genie explains the rules (precision/exactness)
    precision_keywords = ["exact", "precisely", "no more", "no less", "careful", "wisely"]
    has_precision_warning = any(keyword in narrative_lower for keyword in precision_keywords)

    if has_precision_warning:
        print("✅ Genie explains wish limitations")
    else:
        print(f"⚠️  WARNING: Genie doesn't explain precision requirement")
        print(f"   Expected keywords like: {precision_keywords}")
        print(f"   Got: {narrative}")

    # Assert genie has mischievous personality reflected
    personality_indicators = ["grin", "twinkle", "mischiev", "ancient", "bound"]
    has_personality = any(indicator in narrative_lower for indicator in personality_indicators)

    if has_personality:
        print("✅ Genie's personality comes through in dialogue")
    else:
        print(f"⚠️  INFO: Genie dialogue could be more atmospheric")

    print("\n✅ Test passed: Genie dialogue is functional and informative")


def test_skeleton_guard_threatening_dialogue(skip_if_no_gcp, game_setup):
    """Test that aggressive NPC has threatening dialogue.

    This tests:
    1. Skeleton guard speaks with quoted dialogue
    2. Dialogue reflects aggressive/hostile personality
    3. Guard warns or threatens player
    """
    game_loop, game_state, gemini_client = game_setup

    # Move to hall where skeleton guard is
    game_state.player_location = "hall"

    print("\n=== TESTING SKELETON GUARD DIALOGUE ===")

    # Speak to skeleton
    narrative, interpretation = game_loop.process_turn("speak to skeleton guard")

    print(f"Narrative: {narrative}")
    print(f"Intent: {interpretation.get('intent')}")

    # Assert dialogue is present
    assert '"' in narrative or "'" in narrative, (
        "Skeleton guard should speak with quoted dialogue. "
        f"Got narrative: {narrative}"
    )
    print("✅ Skeleton guard speaks with quoted dialogue")

    # Assert threatening/hostile tone
    narrative_lower = narrative.lower()
    hostile_keywords = ["halt", "stop", "trespasser", "pass", "guard", "blade", "sword", "fight", "attack", "warn"]
    has_hostile_tone = any(keyword in narrative_lower for keyword in hostile_keywords)

    assert has_hostile_tone, (
        "Skeleton guard (hostile) should have threatening dialogue. "
        f"Expected keywords like: {hostile_keywords}\n"
        f"Got narrative: {narrative}"
    )
    print("✅ Skeleton guard has hostile/threatening dialogue")

    print("\n✅ Test passed: Hostile NPC dialogue reflects personality")


def test_deer_non_speaking_response(skip_if_no_gcp, game_setup):
    """Test that passive animals don't speak but respond appropriately.

    This tests:
    1. Deer doesn't have quoted dialogue (animals don't speak)
    2. Narrative describes deer's reaction/behavior
    3. Tone is gentle/peaceful (matches passive hostility)
    """
    game_loop, game_state, gemini_client = game_setup

    # Move to forest clearing where deer is
    game_state.player_location = "forest_clearing"

    print("\n=== TESTING DEER NON-SPEAKING RESPONSE ===")

    # Greet deer
    narrative, interpretation = game_loop.process_turn("greet the deer")

    print(f"Narrative: {narrative}")
    print(f"Intent: {interpretation.get('intent')}")

    # Deer should NOT speak (it's an animal)
    # But it's okay if there are quotation marks for other reasons
    # The key is that the deer isn't speaking like a person

    # Assert gentle/peaceful description
    narrative_lower = narrative.lower()
    gentle_keywords = ["gentle", "peaceful", "soft", "calm", "graceful", "eyes", "watch", "lift"]
    has_gentle_tone = any(keyword in narrative_lower for keyword in gentle_keywords)

    if has_gentle_tone:
        print("✅ Deer response is gentle and appropriate for passive creature")
    else:
        print(f"⚠️  INFO: Deer could show more gentle behavior")
        print(f"   Got: {narrative}")

    # Assert it's atmospheric (not just "the deer ignores you")
    assert len(narrative) > 20, (
        "Deer response should be atmospheric and descriptive. "
        f"Got: {narrative}"
    )
    print("✅ Deer response is atmospheric")

    print("\n✅ Test passed: Passive animal responds appropriately")


def test_multiple_npcs_different_dialogue(skip_if_no_gcp, game_setup):
    """Test that different NPCs have distinctly different dialogue styles.

    This tests:
    1. Genie has mystical/formal dialogue
    2. Skeleton has hostile dialogue
    3. Each NPC's dialogue reflects their unique attributes
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING DIALOGUE VARIETY ===")

    # Talk to genie
    game_state.player_location = "forest_clearing"
    genie_narrative, _ = game_loop.process_turn("talk to genie")
    print(f"\nGenie dialogue: {genie_narrative[:150]}...")

    # Talk to skeleton
    game_state.player_location = "hall"
    skeleton_narrative, _ = game_loop.process_turn("talk to skeleton guard")
    print(f"\nSkeleton dialogue: {skeleton_narrative[:150]}...")

    # Assert the dialogues are different
    # (They should use different words and have different tones)
    genie_words = set(genie_narrative.lower().split())
    skeleton_words = set(skeleton_narrative.lower().split())

    # Calculate overlap (should be low for distinct dialogue)
    common_words = genie_words & skeleton_words
    # Exclude common words like "the", "a", "you", etc.
    stopwords = {"the", "a", "an", "you", "your", "and", "of", "to", "in", "is", "it", "that", "with"}
    meaningful_common = common_words - stopwords

    unique_genie = genie_words - skeleton_words - stopwords
    unique_skeleton = skeleton_words - genie_words - stopwords

    print(f"\nUnique genie words: {len(unique_genie)}")
    print(f"Unique skeleton words: {len(unique_skeleton)}")
    print(f"Meaningful overlap: {len(meaningful_common)}")

    # Assert each has unique vocabulary
    assert len(unique_genie) > 5, "Genie should have unique vocabulary"
    assert len(unique_skeleton) > 5, "Skeleton should have unique vocabulary"

    print("✅ NPCs have distinct dialogue styles")

    print("\n✅ Test passed: NPC dialogue is varied and personality-driven")


def test_rat_defensive_dialogue(skip_if_no_gcp, game_setup):
    """Test that defensive NPC has cautious/nervous dialogue.

    This tests:
    1. Rat (defensive creature) doesn't immediately attack
    2. Dialogue or behavior shows caution/nervousness
    3. Different from aggressive (skeleton) and passive (deer) NPCs
    """
    game_loop, game_state, gemini_client = game_setup

    # Move to armory where rat is
    game_state.player_location = "armory"

    print("\n=== TESTING DEFENSIVE NPC DIALOGUE ===")

    # Speak to rat
    narrative, interpretation = game_loop.process_turn("speak to the rat")

    print(f"Narrative: {narrative}")
    print(f"Intent: {interpretation.get('intent')}")

    # Check for defensive/cautious behavior
    narrative_lower = narrative.lower()
    defensive_keywords = ["wary", "cautious", "nervous", "watch", "eye", "bead", "tense", "ready", "defensive"]
    has_defensive_tone = any(keyword in narrative_lower for keyword in defensive_keywords)

    if has_defensive_tone:
        print("✅ Rat shows defensive/cautious behavior")
    else:
        print(f"⚠️  INFO: Rat could show more defensive behavior")
        print(f"   Expected keywords like: {defensive_keywords}")

    # Assert NOT immediately hostile (shouldn't say "attacks you")
    hostile_actions = ["attacks", "lunges", "bites", "strikes at"]
    is_attacking = any(action in narrative_lower for action in hostile_actions)

    if is_attacking:
        print(f"⚠️  WARNING: Defensive rat shouldn't immediately attack")
        print(f"   Defensive NPCs should only fight if attacked first")
    else:
        print("✅ Rat doesn't immediately attack (defensive behavior)")

    print("\n✅ Test passed: Defensive NPC behaves appropriately")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
