"""Event system for timed and automatic game events."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class GameEvent(BaseModel):
    """Represents a scheduled game event.

    Events can be triggered by:
    - Turn number (execute_at_turn)
    - Flags/conditions checked each turn
    - Immediate execution (execute_at_turn = current turn)
    """

    event_id: str = Field(..., description="Unique identifier for this event")
    event_type: str = Field(..., description="Type of event (npc_action, item_spawn, etc.)")
    execute_at_turn: int = Field(..., description="Turn number when event should execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Event-specific parameters")
    repeating: bool = Field(default=False, description="If true, reschedule after execution")
    repeat_interval: Optional[int] = Field(default=None, description="Turns between repeats")
    one_time: bool = Field(default=True, description="If true, remove after execution")

    # Metadata
    description: Optional[str] = Field(default=None, description="Human-readable event description")
    triggered_by: Optional[str] = Field(default=None, description="What triggered this event")


class EventQueue(BaseModel):
    """Manages scheduled game events.

    Events are stored by turn number and processed in order.
    Supports QUEUE (schedule), DEQUEUE (cancel), and automatic processing.
    """

    events: List[GameEvent] = Field(default_factory=list, description="All scheduled events")
    executed_event_ids: List[str] = Field(default_factory=list, description="IDs of executed one-time events")

    def schedule_event(
        self,
        event_id: str,
        event_type: str,
        execute_at_turn: int,
        params: Dict[str, Any],
        one_time: bool = True,
        repeating: bool = False,
        repeat_interval: Optional[int] = None,
        description: Optional[str] = None,
        triggered_by: Optional[str] = None
    ) -> None:
        """Schedule a new event (QUEUE operation).

        Args:
            event_id: Unique identifier for this event
            event_type: Type of event to execute
            execute_at_turn: Turn number when event should fire
            params: Event-specific parameters
            one_time: If True, event only fires once
            repeating: If True, reschedule after execution
            repeat_interval: Turns between repeats (if repeating)
            description: Human-readable description
            triggered_by: What triggered this event
        """
        # Check if event already exists
        existing = self.get_event(event_id)
        if existing:
            logger.warning(f"Event '{event_id}' already scheduled, skipping duplicate")
            return

        # Check if already executed (for one-time events)
        if one_time and event_id in self.executed_event_ids:
            logger.info(f"Event '{event_id}' already executed, skipping")
            return

        event = GameEvent(
            event_id=event_id,
            event_type=event_type,
            execute_at_turn=execute_at_turn,
            params=params,
            repeating=repeating,
            repeat_interval=repeat_interval,
            one_time=one_time,
            description=description,
            triggered_by=triggered_by
        )

        self.events.append(event)
        logger.info(f"Scheduled event '{event_id}' type={event_type} at turn {execute_at_turn}")

    def cancel_event(self, event_id: str) -> bool:
        """Cancel a scheduled event (DEQUEUE operation).

        Args:
            event_id: ID of event to cancel

        Returns:
            True if event was found and cancelled, False otherwise
        """
        for i, event in enumerate(self.events):
            if event.event_id == event_id:
                self.events.pop(i)
                logger.info(f"Cancelled event '{event_id}'")
                return True

        logger.warning(f"Event '{event_id}' not found, cannot cancel")
        return False

    def get_event(self, event_id: str) -> Optional[GameEvent]:
        """Get event by ID.

        Args:
            event_id: ID of event to retrieve

        Returns:
            GameEvent if found, None otherwise
        """
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def get_events_for_turn(self, turn_number: int) -> List[GameEvent]:
        """Get all events scheduled for a specific turn.

        Args:
            turn_number: Turn number to check

        Returns:
            List of events scheduled for this turn
        """
        return [e for e in self.events if e.execute_at_turn == turn_number]

    def process_turn(self, current_turn: int) -> List[GameEvent]:
        """Process all events for the current turn.

        This should be called at the end of each turn.
        Returns events that should execute, and handles rescheduling/removal.

        Args:
            current_turn: Current turn number

        Returns:
            List of events to execute this turn
        """
        events_to_execute = self.get_events_for_turn(current_turn)

        if not events_to_execute:
            return []

        logger.info(f"Processing {len(events_to_execute)} event(s) for turn {current_turn}")

        # Remove executed events or reschedule if repeating
        for event in events_to_execute:
            # Remove from queue
            self.events.remove(event)

            # Track as executed if one-time
            if event.one_time:
                self.executed_event_ids.append(event.event_id)

            # Reschedule if repeating
            if event.repeating and event.repeat_interval:
                next_turn = current_turn + event.repeat_interval
                self.schedule_event(
                    event_id=f"{event.event_id}_repeat_{next_turn}",
                    event_type=event.event_type,
                    execute_at_turn=next_turn,
                    params=event.params,
                    one_time=False,
                    repeating=True,
                    repeat_interval=event.repeat_interval,
                    description=event.description,
                    triggered_by=f"Repeat of {event.event_id}"
                )

        return events_to_execute

    def has_pending_events(self) -> bool:
        """Check if there are any pending events.

        Returns:
            True if there are scheduled events, False otherwise
        """
        return len(self.events) > 0

    def get_all_events(self) -> List[GameEvent]:
        """Get all scheduled events.

        Returns:
            List of all scheduled events, sorted by turn number
        """
        return sorted(self.events, key=lambda e: e.execute_at_turn)
