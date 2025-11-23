"""Rule engine for evaluating and executing game rules."""

from typing import Any, Dict, List, Optional, Callable, Union
import re

from .rule import Rule, RuleTrigger, RuleEffect
from ..models.game_state import GameState
from ..utils.dice import d20_check, roll_from_notation


class RuleContext:
    """Context for rule evaluation, providing access to game state and event data."""

    def __init__(self, game_state: GameState, event_data: Dict[str, Any]):
        self.game_state = game_state
        self.event_data = event_data
        self.results: Dict[str, Any] = {}

    def get_value(self, path: str) -> Any:
        """Resolve a value path like 'actor.hp' or 'target.armor_class'.

        Paths can reference:
        - event_data fields: 'action_type', 'actor', 'target'
        - entity attributes: 'actor.hp', 'target.armor_class'
        - game state: 'game.turn_count'
        """
        parts = path.split(".")

        # Start with event data or game state
        if parts[0] == "game":
            current = self.game_state
            parts = parts[1:]
        elif parts[0] in self.event_data:
            current = self.event_data[parts[0]]
            parts = parts[1:]
        else:
            return None

        # Navigate the path
        for part in parts:
            if hasattr(current, "attributes") and hasattr(
                current.attributes, "__contains__"
            ):
                # Pydantic model with attributes dict
                if part in current.attributes:
                    current = current.attributes[part]
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return None
            elif hasattr(current, part):
                # Pydantic model field
                current = getattr(current, part)
            elif isinstance(current, dict):  # type: ignore[unreachable]
                # Plain dict - check attributes dict
                if "attributes" in current and part in current["attributes"]:
                    current = current["attributes"][part]
                elif part in current:
                    current = current[part]
                else:
                    return None
            else:
                return None

        return current

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression.

        Supports:
        - Simple comparisons: 'actor.hp > 0'
        - Property checks: 'actor.has_weapon'
        - Existence checks: 'target.armor_class'
        """
        condition = condition.strip()

        # Handle simple boolean property checks
        if (
            ">" not in condition
            and "<" not in condition
            and "==" not in condition
            and "!=" not in condition
        ):
            value = self.get_value(condition)
            return bool(value)

        # Handle comparisons
        for op in [">=", "<=", "==", "!=", ">", "<"]:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self.get_value(left.strip())
                right_val = self.get_value(right.strip())

                # Try to parse right side as literal if not found in context
                if right_val is None:
                    try:
                        right_val = eval(right.strip())
                    except:
                        return False

                if left_val is None:
                    return False

                # Perform comparison
                if op == ">":
                    return bool(left_val > right_val)
                elif op == "<":
                    return bool(left_val < right_val)
                elif op == ">=":
                    return bool(left_val >= right_val)
                elif op == "<=":
                    return bool(left_val <= right_val)
                elif op == "==":
                    return bool(left_val == right_val)
                elif op == "!=":
                    return bool(left_val != right_val)

        return False


class RuleEngine:
    """Engine for managing and executing game rules."""

    def __init__(self) -> None:
        self.rules: Dict[str, Rule] = {}
        self.effect_handlers: Dict[str, Callable[..., None]] = {}
        self._register_default_handlers()

    def register_rule(self, rule: Rule) -> None:
        """Register a rule with the engine."""
        self.rules[rule.id] = rule

    def register_rules(self, rules: List[Rule]) -> None:
        """Register multiple rules."""
        for rule in rules:
            self.register_rule(rule)

    def load_rules_from_dict(self, rules_data: List[Dict[str, Any]]) -> None:
        """Load rules from dictionary data."""
        for rule_data in rules_data:
            rule = Rule.model_validate(rule_data)
            self.register_rule(rule)

    def register_effect_handler(
        self, effect_type: str, handler: Callable[..., None]
    ) -> None:
        """Register a handler for an effect type."""
        self.effect_handlers[effect_type] = handler

    def _register_default_handlers(self) -> None:
        """Register default effect handlers."""
        self.register_effect_handler("d20_check", self._handle_d20_check)
        self.register_effect_handler("damage", self._handle_damage)
        self.register_effect_handler("heal", self._handle_heal)
        self.register_effect_handler("modify_attribute", self._handle_modify_attribute)
        self.register_effect_handler("set_flag", self._handle_set_flag)

    def get_applicable_rules(
        self, trigger: RuleTrigger, event_data: Dict[str, Any]
    ) -> List[Rule]:
        """Get all rules that apply to a trigger and match the event data."""
        applicable = []

        for rule in self.rules.values():
            if rule.trigger != trigger:
                continue

            # Check trigger filters
            if rule.trigger_filter:
                matches = all(
                    event_data.get(key) == value
                    for key, value in rule.trigger_filter.items()
                )
                if not matches:
                    continue

            applicable.append(rule)

        # Sort by priority (highest first)
        applicable.sort(key=lambda r: r.priority, reverse=True)
        return applicable

    def evaluate_rule(
        self, rule: Rule, game_state: GameState, event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a rule and execute its effects if conditions pass.

        Returns results dictionary if rule fired, None otherwise.
        """
        context = RuleContext(game_state, event_data)

        # Check all conditions
        for condition in rule.conditions:
            if not context.evaluate_condition(condition):
                return None  # Condition failed

        # All conditions passed, execute effects
        for effect in rule.effects:
            self._execute_effect(effect, context)

        return context.results

    def process_event(
        self, trigger: RuleTrigger, game_state: GameState, event_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process an event through the rule engine.

        Returns list of results from all rules that fired.
        """
        applicable_rules = self.get_applicable_rules(trigger, event_data)
        results = []

        for rule in applicable_rules:
            result = self.evaluate_rule(rule, game_state, event_data)
            if result is not None:
                result["rule_id"] = rule.id
                result["rule_name"] = rule.name
                results.append(result)

        return results

    def _execute_effect(self, effect: RuleEffect, context: RuleContext) -> None:
        """Execute an effect using registered handlers."""
        handler = self.effect_handlers.get(effect.type)
        if handler:
            handler(effect, context)

    # Default effect handlers

    def _handle_d20_check(self, effect: RuleEffect, context: RuleContext) -> None:
        """Handle d20 check effect."""
        params = effect.params
        modifier = context.get_value(params.get("modifier", "0"))
        if modifier is None:
            modifier = 0

        dc = context.get_value(params.get("dc", "10"))
        if dc is None:
            dc = 10

        # Perform d20 check
        result = d20_check(modifier=int(modifier))
        success = result["total"] >= dc

        context.results["d20_check"] = result
        context.results["success"] = success
        context.results["dc"] = dc

        # Handle success/failure effects
        if success and "on_success" in params:
            success_effect = RuleEffect(
                type=params["on_success"].get("type"), params=params["on_success"]
            )
            self._execute_effect(success_effect, context)
        elif not success and "on_failure" in params:
            failure_effect = RuleEffect(
                type=params["on_failure"].get("type"), params=params["on_failure"]
            )
            self._execute_effect(failure_effect, context)

    def _handle_damage(self, effect: RuleEffect, context: RuleContext) -> None:
        """Handle damage effect."""
        params = effect.params
        damage_dice = params.get("damage_dice", "1d6")

        # Resolve damage dice from context if it's a path
        if isinstance(damage_dice, str) and "." in damage_dice:
            resolved = context.get_value(damage_dice)
            if resolved:
                damage_dice = resolved

        # Roll damage
        damage_result = roll_from_notation(damage_dice)
        damage_amount = damage_result["total"]

        # Apply critical hit multiplier if applicable
        if context.results.get("d20_check", {}).get("is_critical"):
            damage_amount *= 2

        context.results["damage"] = damage_result
        context.results["damage_amount"] = damage_amount
        context.results["damage_type"] = params.get("damage_type", "untyped")

    def _handle_heal(self, effect: RuleEffect, context: RuleContext) -> None:
        """Handle healing effect."""
        params = effect.params
        heal_dice = params.get("heal_dice", "1d4")

        heal_result = roll_from_notation(heal_dice)
        context.results["heal"] = heal_result
        context.results["heal_amount"] = heal_result["total"]

    def _handle_modify_attribute(
        self, effect: RuleEffect, context: RuleContext
    ) -> None:
        """Handle attribute modification."""
        params = effect.params
        context.results["modify_attribute"] = params

    def _handle_set_flag(self, effect: RuleEffect, context: RuleContext) -> None:
        """Handle setting a game flag."""
        params = effect.params
        flag_name = params.get("flag")
        flag_value = params.get("value", True)

        if flag_name:
            context.game_state.flags[flag_name] = flag_value
            context.results["flag_set"] = {flag_name: flag_value}
