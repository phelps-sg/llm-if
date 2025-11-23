"""Dice rolling utilities for game mechanics."""

import random
import re
from typing import List, Tuple


def roll_die(sides: int) -> int:
    """Roll a single die with specified number of sides."""
    return random.randint(1, sides)


def roll_d20() -> int:
    """Roll a d20."""
    return roll_die(20)


def roll_dice(num_dice: int, sides: int) -> List[int]:
    """Roll multiple dice and return individual results."""
    return [roll_die(sides) for _ in range(num_dice)]


def roll_dice_sum(num_dice: int, sides: int, modifier: int = 0) -> int:
    """Roll multiple dice and return the sum plus modifier."""
    total = sum(roll_dice(num_dice, sides))
    return total + modifier


def parse_dice_notation(notation: str) -> Tuple[int, int, int]:
    """Parse dice notation like '2d6+3' or '1d20-1'.

    Returns: (num_dice, sides, modifier)
    Raises: ValueError if notation is invalid
    """
    notation = notation.strip().lower().replace(" ", "")

    # Match patterns like: 2d6, 2d6+3, 2d6-1, d20, d20+5
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, notation)

    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    num_dice = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    return num_dice, sides, modifier


def roll_from_notation(notation: str) -> dict:
    """Roll dice from notation and return detailed results.

    Args:
        notation: Dice notation like '2d6+3'

    Returns:
        Dictionary with:
        - rolls: List of individual die results
        - modifier: The modifier applied
        - total: Final sum
        - notation: The original notation
    """
    num_dice, sides, modifier = parse_dice_notation(notation)
    rolls = roll_dice(num_dice, sides)
    total = sum(rolls) + modifier

    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "num_dice": num_dice,
        "sides": sides,
    }


def advantage() -> int:
    """Roll d20 with advantage (roll twice, take higher)."""
    return max(roll_d20(), roll_d20())


def disadvantage() -> int:
    """Roll d20 with disadvantage (roll twice, take lower)."""
    return min(roll_d20(), roll_d20())


def d20_check(
    modifier: int = 0, has_advantage: bool = False, has_disadvantage: bool = False
) -> dict:
    """Make a d20 check with optional advantage/disadvantage.

    Args:
        modifier: Modifier to add to the roll
        has_advantage: Roll with advantage
        has_disadvantage: Roll with disadvantage

    Returns:
        Dictionary with roll details
    """
    if has_advantage and has_disadvantage:
        # They cancel out
        roll = roll_d20()
        condition = "normal"
    elif has_advantage:
        roll = advantage()
        condition = "advantage"
    elif has_disadvantage:
        roll = disadvantage()
        condition = "disadvantage"
    else:
        roll = roll_d20()
        condition = "normal"

    total = roll + modifier

    return {
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "condition": condition,
        "is_critical": roll == 20,
        "is_fumble": roll == 1,
    }
