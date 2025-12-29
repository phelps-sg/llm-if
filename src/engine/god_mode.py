"""God mode - debugging and inspection tools for developers."""

import json
from typing import Optional, List
from ..models.game_state import GameState
from ..llm.zil_translation_cache import get_cache


def handle_god_command(command: str, game_state: GameState) -> str:
    """Handle god mode inspection commands.

    Args:
        command: Command string starting with /
        game_state: Current game state

    Returns:
        Formatted response text
    """
    parts = command[1:].split()
    if not parts:
        return _show_help()

    cmd = parts[0].lower()
    args = parts[1:]

    handlers = {
        "inspect": lambda: _inspect_entity(args, game_state),
        "inventory": lambda: _show_inventory(game_state),
        "state": lambda: _show_state(game_state),
        "context": lambda: _show_context(game_state),
        "overrides": lambda: _show_overrides(game_state),
        "history": lambda: _show_history(args, game_state),
        "last": lambda: _show_history(["1"], game_state),
        "help": lambda: _show_help(),
    }

    handler = handlers.get(cmd)
    if handler:
        return handler()
    else:
        return f"Unknown god mode command: /{cmd}\n\nType /help for available commands."


def _show_help() -> str:
    """Show available god mode commands."""
    return """
=== GOD MODE COMMANDS ===

/inspect <entity>   Show raw JSON for item/NPC/location
                    Example: /inspect coin

/inventory          Show player inventory with nested structure

/state              Show game state summary (location, turn, flags)

/context            Show what's in the current LLM context

/overrides          Show active overrides from *_overrides.json

/history [n]        Show last N turns with state_updates (default: 3)
                    Example: /history 5

/last               Show last turn's interpretation and state_updates
                    (shorthand for /history 1)

/help               Show this help message

DM: <question>      Ask the DM for debugging help
                    Example: DM: Why doesn't the ruby appear?

=========================
"""


def _get_zil_translation(zil_code: str) -> Optional[str]:
    """Get cached ZIL translation if available.

    Args:
        zil_code: ZIL code string

    Returns:
        Natural language translation, or None if not cached
    """
    if not zil_code or not zil_code.strip():
        return None

    try:
        cache = get_cache()
        return cache.get(zil_code)
    except Exception as e:
        return f"[Error loading translation: {e}]"


def _format_zil_section(attributes: dict) -> str:
    """Format ZIL code sections with translations if available.

    Args:
        attributes: Entity attributes dict that may contain ZIL code

    Returns:
        Formatted string with ZIL code and translations
    """
    result = ""

    # Check for various ZIL code fields
    zil_fields = [
        "zil_action_code",
        "zil_examine_code",
        "zil_take_code",
        "zil_open_code",
        "zil_close_code"
    ]

    for field in zil_fields:
        if field in attributes and attributes[field]:
            zil_code = attributes[field]

            result += f"\n--- {field.upper()} ---\n"
            result += f"Raw ZIL ({len(zil_code)} chars):\n"
            result += zil_code[:200]  # Show first 200 chars
            if len(zil_code) > 200:
                result += f"\n... ({len(zil_code) - 200} more chars)"

            # Try to get translation
            translation = _get_zil_translation(zil_code)
            if translation:
                result += f"\n\nNatural Language Translation:\n{translation}\n"
            else:
                result += "\n\n⚠️  No translation cached yet - will be generated on first use\n"

    return result


def _inspect_entity(args: List[str], game_state: GameState) -> str:
    """Inspect an entity's raw JSON data.

    Args:
        args: [entity_id]
        game_state: Current game state

    Returns:
        Formatted JSON or error message
    """
    if not args:
        return "Usage: /inspect <entity_id>\nExample: /inspect coin"

    entity_id = args[0].lower()

    # Check items
    if entity_id in game_state.items:
        item = game_state.items[entity_id]
        location = game_state.item_locations.get(entity_id, "player inventory")

        result = f"\n=== ITEM: {entity_id} ({item.name}) ===\n"
        result += f"Location: {location}\n\n"
        result += json.dumps(item.model_dump(), indent=2)

        # Add ZIL translation section if ZIL code exists
        zil_section = _format_zil_section(item.attributes)
        if zil_section:
            result += f"\n\n{'=' * 60}"
            result += "\nZIL CODE & TRANSLATIONS"
            result += f"\n{'=' * 60}"
            result += zil_section

        result += "\n\nSource: Check worlds/<game>_overrides.json for manual overrides"
        return result

    # Check NPCs
    if entity_id in game_state.npcs:
        npc = game_state.npcs[entity_id]
        location = game_state.npc_locations.get(entity_id, "unknown")

        result = f"\n=== NPC: {entity_id} ({npc.name}) ===\n"
        result += f"Location: {location}\n\n"
        result += json.dumps(npc.model_dump(), indent=2)

        # Add ZIL translation section if ZIL code exists
        zil_section = _format_zil_section(npc.attributes)
        if zil_section:
            result += f"\n\n{'=' * 60}"
            result += "\nZIL CODE & TRANSLATIONS"
            result += f"\n{'=' * 60}"
            result += zil_section

        result += "\n\nSource: Check worlds/<game>_overrides.json for manual overrides"
        return result

    # Check locations
    if entity_id in game_state.locations:
        location = game_state.locations[entity_id]

        result = f"\n=== LOCATION: {entity_id} ({location.name}) ===\n\n"
        result += json.dumps(location.model_dump(), indent=2)

        # Add ZIL translation section if ZIL code exists
        zil_section = _format_zil_section(location.attributes)
        if zil_section:
            result += f"\n\n{'=' * 60}"
            result += "\nZIL CODE & TRANSLATIONS"
            result += f"\n{'=' * 60}"
            result += zil_section

        result += "\n\nSource: Check worlds/<game>_overrides.json for manual overrides"
        return result

    return f"Entity '{entity_id}' not found. Check items, NPCs, and locations."


def _show_inventory(game_state: GameState) -> str:
    """Show player inventory with nested structure."""
    result = "\n=== PLAYER INVENTORY ===\n\n"
    result += f"Direct inventory: {game_state.player.inventory}\n\n"

    if not game_state.player.inventory:
        result += "  (empty)\n"
        return result

    for item_id in game_state.player.inventory:
        item = game_state.items.get(item_id)
        if not item:
            result += f"  ⚠️  {item_id} (NOT FOUND IN ITEMS)\n"
            continue

        result += f"  • {item.name} ({item_id})\n"

        # Check if this item is a container
        container_items = game_state.get_items_in_container(item_id)
        if container_items:
            result += f"    Contains:\n"
            for nested_item in container_items:
                result += f"      - {nested_item.name} ({nested_item.id})\n"

    return result


def _show_state(game_state: GameState) -> str:
    """Show game state summary."""
    current_location = game_state.get_player_location()
    location_name = current_location.name if current_location else "unknown"

    result = "\n=== GAME STATE ===\n\n"
    result += f"Turn: {game_state.turn_count}\n"
    result += f"Location: {game_state.player_location} ({location_name})\n"
    result += f"Game Time: {game_state.game_time}\n"
    result += f"\nInventory: {game_state.player.inventory}\n"

    # Show flags
    if game_state.flags:
        result += f"\nFlags:\n"
        for key, value in game_state.flags.items():
            if key != "god_mode":  # Skip god_mode flag
                result += f"  {key}: {value}\n"

    # Show items at current location
    if current_location:
        items_here = game_state.get_items_at_location(game_state.player_location)
        if items_here:
            result += f"\nItems at location:\n"
            for item in items_here:
                result += f"  • {item.name} ({item.id})\n"

        # Show NPCs at current location
        npcs_here = game_state.get_npcs_at_location(game_state.player_location)
        if npcs_here:
            result += f"\nNPCs at location:\n"
            for npc in npcs_here:
                result += f"  • {npc.name} ({npc.id})\n"

    return result


def _show_context(game_state: GameState) -> str:
    """Show what's currently in the LLM context.

    This shows the game entities that would be included in the next LLM call.
    """
    current_location = game_state.get_player_location()

    result = "\n=== LLM CONTEXT (what DM sees) ===\n\n"

    if current_location:
        result += f"Current Location:\n  {current_location.name} ({current_location.id})\n"
        result += f"  Connections: {list(current_location.connections.keys())}\n\n"

    # Items at location
    items_here = game_state.get_items_at_location(game_state.player_location)
    result += f"Visible Items ({len(items_here)}):\n"
    for item in items_here[:5]:  # Show first 5
        result += f"  • {item.name}\n"
    if len(items_here) > 5:
        result += f"  ... and {len(items_here) - 5} more\n"
    result += "\n"

    # NPCs at location
    npcs_here = game_state.get_npcs_at_location(game_state.player_location)
    result += f"NPCs Present ({len(npcs_here)}):\n"
    for npc in npcs_here:
        result += f"  • {npc.name}\n"
        if hasattr(npc, 'ambient_phrases') and npc.attributes.get('ambient_phrases'):
            result += f"    Ambient phrases: {npc.attributes['ambient_phrases'][:2]}...\n"
    result += "\n"

    # Player inventory
    result += f"Player Inventory ({len(game_state.player.inventory)} items):\n"
    for item_id in game_state.player.inventory:
        item = game_state.items.get(item_id)
        if item:
            result += f"  • {item.name}\n"
    result += "\n"

    # Recent history
    recent = game_state.get_recent_history(2)
    result += f"Recent History (last {len(recent)} turns):\n"
    for entry in recent:
        if "user_input" in entry:
            result += f"  Turn {entry.get('turn', '?')}: {entry['user_input']}\n"

    # World context
    if game_state.world_context:
        result += f"\nWorld Context:\n"
        result += f"  Title: {game_state.world_context.get('title', 'unknown')}\n"
        result += f"  Has intro: {'intro' in game_state.world_context}\n"
        result += f"  Has DM instructions: {'dm_instructions' in game_state.world_context}\n"

    return result


def _show_history(args: List[str], game_state: GameState) -> str:
    """Show recent turns with state_updates.

    Args:
        args: [count] - number of turns to show (default: 3)
        game_state: Current game state

    Returns:
        Formatted history with state_updates
    """
    count = 3  # default
    if args:
        try:
            count = int(args[0])
        except ValueError:
            return "Usage: /history [count]\nExample: /history 5"

    history = game_state.get_recent_history(count)

    if not history:
        return "\n=== HISTORY ===\n\n(No history yet)\n"

    result = f"\n=== HISTORY (last {len(history)} turns) ===\n"

    for entry in history:
        turn = entry.get("turn", "?")
        user_input = entry.get("input", "")
        interpretation = entry.get("interpretation", {})

        result += f"\n{'=' * 60}\n"
        result += f"Turn {turn}: {user_input}\n"
        result += f"{'=' * 60}\n\n"

        # Show interpretation details
        result += f"Intent: {interpretation.get('intent', 'N/A')}\n"
        result += f"Valid: {interpretation.get('is_valid', 'N/A')}\n\n"

        # Show state_updates (the important part for debugging!)
        state_updates = interpretation.get("state_updates", [])
        if state_updates:
            result += f"State Updates ({len(state_updates)}):\n"
            result += json.dumps(state_updates, indent=2)
            result += "\n\n"
        else:
            result += "State Updates: (none)\n\n"

        # Show narrative snippet
        narrative = interpretation.get("narrative_response", "")
        if narrative:
            narrative_preview = narrative[:150] + "..." if len(narrative) > 150 else narrative
            result += f"Narrative: {narrative_preview}\n"

    return result


def _show_overrides(game_state: GameState) -> str:
    """Show which entities have active overrides."""
    result = "\n=== ACTIVE OVERRIDES ===\n\n"

    # This is a simplified view - in a real implementation, we'd track which
    # fields came from overrides vs base data
    result += "To see override details, check:\n"
    result += "  worlds/<game>_overrides.json\n\n"

    result += "Entities with common override fields:\n\n"

    # Check items for override fields (look in attributes dict, not hasattr)
    items_with_overrides = []
    for item_id, item in game_state.items.items():
        override_fields = []
        if item.attributes.get('examine_text'):
            override_fields.append('examine_text')
        if item.attributes.get('triggers'):
            override_fields.append('triggers')
        if item.attributes.get('purchasable'):
            override_fields.append('purchasable')

        if override_fields:
            items_with_overrides.append((item_id, item.name, override_fields))

    if items_with_overrides:
        result += "Items:\n"
        for item_id, name, fields in items_with_overrides:
            result += f"  • {name} ({item_id}): {', '.join(fields)}\n"
        result += "\n"

    # Check NPCs for override fields (look in attributes dict, not hasattr)
    npcs_with_overrides = []
    for npc_id, npc in game_state.npcs.items():
        override_fields = []
        if npc.attributes.get('ambient_phrases'):
            override_fields.append('ambient_phrases')
        if npc.attributes.get('ambient_frequency'):
            override_fields.append('ambient_frequency')
        if npc.attributes.get('description_override'):
            override_fields.append('description_override')

        if override_fields:
            npcs_with_overrides.append((npc_id, npc.name, override_fields))

    if npcs_with_overrides:
        result += "NPCs:\n"
        for npc_id, name, fields in npcs_with_overrides:
            result += f"  • {name} ({npc_id}): {', '.join(fields)}\n"
        result += "\n"

    # Check locations for override fields
    locations_with_overrides = []
    for loc_id, loc in game_state.locations.items():
        override_fields = []
        if loc.attributes.get('examine_details'):
            override_fields.append('examine_details')

        if override_fields:
            locations_with_overrides.append((loc_id, loc.name, override_fields))

    if locations_with_overrides:
        result += "Locations:\n"
        for loc_id, name, fields in locations_with_overrides:
            result += f"  • {name} ({loc_id}): {', '.join(fields)}\n"
        result += "\n"

    if not items_with_overrides and not npcs_with_overrides and not locations_with_overrides:
        result += "  (No overrides detected - attributes may be in base JSON)\n"

    return result
