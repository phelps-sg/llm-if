"""ZIL serializer - converts S-expressions back to readable ZIL format.

This preserves the original ZIL code for LLM interpretation.
"""

from typing import Any, List
from sexpdata import Symbol


def serialize_zil(sexp: Any, indent: int = 0) -> str:
    """Convert an S-expression back to readable ZIL format.

    Args:
        sexp: S-expression (nested lists, symbols, strings, etc.)
        indent: Current indentation level

    Returns:
        Formatted ZIL code as a string
    """
    indent_str = "  " * indent

    if sexp is None:
        return "NIL"

    elif isinstance(sexp, bool):
        return "T" if sexp else "NIL"

    elif isinstance(sexp, (int, float)):
        return str(sexp)

    elif isinstance(sexp, str):
        # String literals
        if "\n" in sexp:
            # Multi-line string
            lines = sexp.split("\n")
            return '"\n' + '\n'.join(lines) + '"'
        else:
            return f'"{sexp}"'

    elif isinstance(sexp, Symbol):
        return str(sexp).upper()

    elif isinstance(sexp, list):
        if not sexp:
            return "()"

        # Check if this is a simple property (2 elements)
        if len(sexp) == 2 and not isinstance(sexp[1], list):
            return f"({serialize_zil(sexp[0])} {serialize_zil(sexp[1])})"

        # Multi-element list - format nicely
        result = "("
        for i, item in enumerate(sexp):
            if i > 0:
                result += " "
            result += serialize_zil(item, indent)
        result += ")"
        return result

    else:
        return str(sexp)


def serialize_zil_entity(entity_type: str, name: Any, properties: List[Any]) -> str:
    """Serialize a complete ZIL entity (ROOM, OBJECT, etc.).

    Args:
        entity_type: "ROOM", "OBJECT", etc.
        name: Entity name symbol
        properties: List of property s-expressions

    Returns:
        Formatted ZIL entity definition
    """
    lines = [f"<{entity_type} {serialize_zil(name)}"]

    for prop in properties:
        if isinstance(prop, list) and len(prop) > 0:
            # Format property on its own line with indentation
            prop_str = serialize_zil(prop, indent=1)
            lines.append(f"  {prop_str}")
        else:
            lines.append(f"  {serialize_zil(prop)}")

    lines.append(">")
    return "\n".join(lines)


def extract_raw_zil(sexp_list: List[Any]) -> str:
    """Extract the raw ZIL from a parsed entity.

    Args:
        sexp_list: The full s-expression for a ROOM, OBJECT, or other entity

    Returns:
        Formatted ZIL code as a multi-line string
    """
    if not isinstance(sexp_list, list) or len(sexp_list) < 2:
        return ""

    entity_type = str(sexp_list[0]).upper() if isinstance(sexp_list[0], Symbol) else str(sexp_list[0])
    name = sexp_list[1]
    properties = sexp_list[2:]

    return serialize_zil_entity(entity_type, name, properties)
