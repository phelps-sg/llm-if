"""Event processor for handling automatic and timed game events."""

import logging
from typing import List, Dict, Any, Optional
from src.models.game_state import GameState
from src.models.event import GameEvent

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes automatic game events and triggers.

    Handles:
    - Executing scheduled events
    - Checking automatic triggers (flag-based, location-based)
    - NPC autonomous actions
    - Timed sequences
    """

    def __init__(self) -> None:
        """Initialize event processor."""
        pass

    def process_events(self, game_state: GameState) -> List[Dict[str, Any]]:
        """Process all events for the current turn.

        This should be called at the end of each turn, after player action is processed.

        Returns:
            List of pending events to be passed to DM for interpretation
        """
        pending_events = []

        # 1. Check automatic triggers (flag-based, location-based)
        # These may schedule new events but don't execute mechanics directly
        self._check_automatic_triggers(game_state)

        # 2. Get scheduled events for this turn
        # These are returned to be passed to the DM, not executed directly
        scheduled_events = game_state.event_queue.process_turn(game_state.turn_count)

        if scheduled_events:
            logger.info(f"Retrieved {len(scheduled_events)} scheduled event(s) for turn {game_state.turn_count}")
            # Convert to dict format for DM
            for event in scheduled_events:
                pending_events.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "params": event.params,
                    "description": event.description,
                    "triggered_by": event.triggered_by
                })

        return pending_events

    def _check_automatic_triggers(self, game_state: GameState) -> None:
        """Check for automatic triggers based on game state.

        Reads trigger definitions from world_context overrides and schedules events.
        Does NOT execute mechanics - just schedules events for DM to interpret.

        Trigger format in overrides:
        {
          "automatic_triggers": [
            {
              "trigger_id": "ruby_theft",
              "condition": {"item_becomes_visible": "ruby"},
              "delay_turns": 1,
              "event_type": "npc_theft",
              "params": {...},
              "description": "...",
              "narrative_template": "..."
            }
          ]
        }
        """
        # Get automatic triggers from world context
        if not game_state.world_context:
            return

        overrides = game_state.world_context.get("overrides", {})
        triggers = overrides.get("automatic_triggers", [])

        for trigger_def in triggers:
            self._evaluate_trigger(trigger_def, game_state)

    def _evaluate_trigger(self, trigger_def: Dict[str, Any], game_state: GameState) -> None:
        """Evaluate a single trigger definition and schedule event if conditions met.

        Args:
            trigger_def: Trigger definition from overrides
            game_state: Current game state
        """
        trigger_id = trigger_def.get("trigger_id")
        condition = trigger_def.get("condition", {})

        # Check if trigger already fired (one-time triggers)
        if trigger_def.get("one_time", True):
            if game_state.flags.get(f"{trigger_id}_fired"):
                return

        # Check if event already scheduled
        event_id = f"{trigger_id}_event"
        if game_state.event_queue.get_event(event_id):
            return

        # Evaluate condition
        if not self._check_condition(condition, game_state):
            return

        # Condition met! Mark as fired and schedule event
        if trigger_def.get("one_time", True):
            game_state.flags[f"{trigger_id}_fired"] = True

        delay_turns = trigger_def.get("delay_turns", 0)
        execute_at_turn = game_state.turn_count + delay_turns

        game_state.event_queue.schedule_event(
            event_id=event_id,
            event_type=trigger_def.get("event_type", "custom"),
            execute_at_turn=execute_at_turn,
            params=trigger_def.get("params", {}),
            one_time=trigger_def.get("one_time", True),
            description=trigger_def.get("description"),
            triggered_by=trigger_id
        )

        logger.info(f"Trigger '{trigger_id}' fired, scheduled event for turn {execute_at_turn}")

    def _check_condition(self, condition: Dict[str, Any], game_state: GameState) -> bool:
        """Check if a trigger condition is met.

        Args:
            condition: Condition definition (e.g., {"item_becomes_visible": "ruby"})
            game_state: Current game state

        Returns:
            True if condition is met, False otherwise
        """
        # item_becomes_visible: check if item just became visible this turn
        if "item_becomes_visible" in condition:
            item_id = condition["item_becomes_visible"]
            item = game_state.items.get(item_id)
            if not item:
                return False

            # Check if item is now visible (in world or inventory)
            item_location = game_state.item_locations.get(item_id)
            item_in_inventory = item_id in game_state.player.inventory

            if not item_location and not item_in_inventory:
                return False

            # Check if we already detected this (use flag to track)
            if game_state.flags.get(f"{item_id}_visibility_detected"):
                return False

            # Item is visible and we haven't detected it yet
            game_state.flags[f"{item_id}_visibility_detected"] = True
            game_state.flags[f"{item_id}_appeared_turn"] = game_state.turn_count
            return True

        # flag_equals: check if a flag has a specific value
        if "flag_equals" in condition:
            flag_name, expected_value = list(condition["flag_equals"].items())[0]
            return bool(game_state.flags.get(flag_name) == expected_value)

        # location_is: check if player is at a specific location
        if "location_is" in condition:
            return bool(game_state.player_location == condition["location_is"])

        # Default: unknown condition type
        logger.warning(f"Unknown condition type: {condition}")
        return False
