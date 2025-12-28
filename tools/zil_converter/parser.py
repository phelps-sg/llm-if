"""ZIL S-expression parser.

Parses ZIL (Zork Implementation Language) files into Python data structures
using S-expression parsing.
"""

from typing import List, Any
import sexpdata
from sexpdata import Symbol


class ZILParser:
    """Parser for ZIL S-expressions."""

    def parse_file(self, filepath: str) -> List[Any]:
        """Parse a .zil file into S-expressions.

        Args:
            filepath: Path to .zil file

        Returns:
            List of S-expression forms
        """
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        try:
            sexps = []

            # Extract specific form types (ROOM, OBJECT, GLOBAL, ROUTINE, etc.)
            # using angle-bracket matching since ZIL uses < > for these
            form_types_to_extract = ['ROOM', 'OBJECT', 'GLOBAL', 'ROUTINE']

            for form_type in form_types_to_extract:
                start_idx = 0

                while True:
                    # Find next occurrence of this form type
                    # Handle '<ROOM ', '<ROOM\n', and '<ROOM\t' patterns
                    pattern_space = f'<{form_type} '
                    pattern_newline = f'<{form_type}\n'
                    pattern_tab = f'<{form_type}\t'

                    pos_space = content.find(pattern_space, start_idx)
                    pos_newline = content.find(pattern_newline, start_idx)
                    pos_tab = content.find(pattern_tab, start_idx)

                    # Use whichever pattern appears first
                    positions = [(pos_space, 'space'), (pos_newline, 'newline'), (pos_tab, 'tab')]
                    valid_positions = [(pos, typ) for pos, typ in positions if pos >= 0]

                    if not valid_positions:
                        break

                    start_idx = min(valid_positions, key=lambda x: x[0])[0]

                    # Find the matching closing >
                    depth = 0
                    i = start_idx
                    while i < len(content):
                        if content[i] == '<':
                            depth += 1
                        elif content[i] == '>':
                            depth -= 1
                            if depth == 0:
                                # Found complete form
                                form_text = content[start_idx:i+1]

                                # Convert to S-exp and parse
                                form_text_converted = self._convert_zil_to_sexp(form_text)
                                try:
                                    parsed = sexpdata.loads(form_text_converted)
                                    sexps.append(parsed)
                                except Exception as e:
                                    # Skip unparseable forms
                                    pass

                                break
                        i += 1

                    # Move past this form for next search
                    start_idx = i + 1 if i < len(content) else len(content)

            return sexps
        except Exception as e:
            raise ValueError(f"Failed to parse ZIL file {filepath}: {e}")

    def _convert_zil_to_sexp(self, zil_content: str) -> str:
        """Convert ZIL angle brackets to parentheses.

        ZIL uses <...> but sexpdata expects (...).
        """
        # Remove leading junk before first < or (
        # (copyright notices, standalone strings, etc.)
        first_angle = zil_content.find('<')
        first_paren = zil_content.find('(')

        if first_angle >= 0 and (first_paren < 0 or first_angle < first_paren):
            zil_content = zil_content[first_angle:]
        elif first_paren >= 0:
            zil_content = zil_content[first_paren:]

        # Remove comments (lines starting with ;)
        # Comments in ZIL don't contain meaningful closing brackets - they're just documentation
        lines = []
        for line in zil_content.split('\n'):
            stripped = line.lstrip()
            # If line starts with ;, it's a comment - skip it entirely
            if not stripped.startswith(';'):
                lines.append(line)

        content = '\n'.join(lines)

        # Convert angle brackets to parentheses
        content = content.replace('<', '(')
        content = content.replace('>', ')')

        return content

    def find_forms(self, sexps: List[Any], form_type: str) -> List[Any]:
        """Find all forms of a specific type (ROOM, OBJECT, etc.).

        Args:
            sexps: List of S-expressions
            form_type: Form type to find (e.g., "ROOM", "OBJECT")

        Returns:
            List of matching forms
        """
        results = []
        for sexp in sexps:
            if isinstance(sexp, list) and len(sexp) > 0:
                first = sexp[0]
                # Check if this is the form type we're looking for
                if isinstance(first, Symbol) and str(first).upper() == form_type.upper():
                    results.append(sexp)
        return results

    def find_all_form_types(self, sexps: List[Any]) -> set:
        """Find all unique form types in the S-expressions.

        Useful for discovering what's in a ZIL file.

        Args:
            sexps: List of S-expressions

        Returns:
            Set of form type names
        """
        form_types = set()
        for sexp in sexps:
            if isinstance(sexp, list) and len(sexp) > 0:
                first = sexp[0]
                if isinstance(first, Symbol):
                    form_types.add(str(first).upper())
        return form_types
