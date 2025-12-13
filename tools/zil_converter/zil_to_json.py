"""Convert ZIL S-expressions to JSON for easier LLM interpretation."""

from typing import Any, Union, List, Dict
from sexpdata import Symbol


def zil_to_json(sexp: Any) -> Union[str, int, float, bool, List, Dict]:
    """Convert a ZIL S-expression to JSON-compatible structure.

    This makes ZIL code easier for LLMs to parse and understand.

    Args:
        sexp: S-expression (nested lists, symbols, strings, etc.)

    Returns:
        JSON-compatible Python structure (dict, list, str, int, float, bool)
    """
    if sexp is None:
        return None

    elif isinstance(sexp, bool):
        return sexp

    elif isinstance(sexp, (int, float)):
        return sexp

    elif isinstance(sexp, str):
        # String literals - keep as is
        return sexp

    elif isinstance(sexp, Symbol):
        # Symbols become strings (uppercase)
        return str(sexp).upper()

    elif isinstance(sexp, list):
        if not sexp:
            return []

        # Check if this looks like a function call
        if isinstance(sexp[0], Symbol):
            func_name = str(sexp[0]).upper()

            # Special forms that should be structured
            if func_name == "COND":
                # COND is a list of conditions
                return {
                    "op": "COND",
                    "cases": [zil_to_json(case) for case in sexp[1:]]
                }

            elif func_name in ["VERB?", "EQUAL?", "==?", "G?", "L?", "FSET?", "IN?", "AND", "OR", "NOT"]:
                # Predicates and logical operators
                return {
                    "op": func_name,
                    "args": [zil_to_json(arg) for arg in sexp[1:]]
                }

            elif func_name == "TELL":
                # TELL prints text
                return {
                    "op": "TELL",
                    "text": [zil_to_json(arg) for arg in sexp[1:]]
                }

            elif func_name == "SETG":
                # SETG sets a global variable
                if len(sexp) >= 3:
                    return {
                        "op": "SETG",
                        "variable": zil_to_json(sexp[1]),
                        "value": zil_to_json(sexp[2])
                    }

            elif func_name in ["REMOVE-CAREFULLY", "JIGS-UP", "OPEN-CLOSE", "DO-WALK", "CRLF", "CR", "RTRUE"]:
                # Common ZIL functions
                return {
                    "op": func_name,
                    "args": [zil_to_json(arg) for arg in sexp[1:]]
                }

            else:
                # Generic function call
                return {
                    "op": func_name,
                    "args": [zil_to_json(arg) for arg in sexp[1:]]
                }

        else:
            # Plain list
            return [zil_to_json(item) for item in sexp]

    else:
        return str(sexp)


def format_routine_as_json(routine_sexp: List[Any]) -> Dict:
    """Convert a ROUTINE S-expression to structured JSON.

    Args:
        routine_sexp: Full ROUTINE s-expression like (ROUTINE NAME (ARGS) ...)

    Returns:
        Dict with routine name, args, and body as JSON
    """
    if not isinstance(routine_sexp, list) or len(routine_sexp) < 3:
        return {"error": "Invalid routine structure"}

    routine_type = str(routine_sexp[0]).upper() if isinstance(routine_sexp[0], Symbol) else str(routine_sexp[0])
    if routine_type != "ROUTINE":
        return {"error": f"Expected ROUTINE, got {routine_type}"}

    name = str(routine_sexp[1]).upper() if isinstance(routine_sexp[1], Symbol) else str(routine_sexp[1])

    # Arguments list
    args = []
    if isinstance(routine_sexp[2], list):
        args = [str(arg).upper() if isinstance(arg, Symbol) else str(arg) for arg in routine_sexp[2]]

    # Body (rest of the routine)
    body = [zil_to_json(stmt) for stmt in routine_sexp[3:]]

    return {
        "type": "ROUTINE",
        "name": name,
        "args": args,
        "body": body
    }
