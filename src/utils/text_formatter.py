"""Text formatting utilities for terminal output."""

import textwrap
from typing import Optional


class TextFormatter:
    """Handles text formatting and wrapping for game output."""

    def __init__(self, width: int = 80):
        """Initialize text formatter with specified width.

        Args:
            width: Maximum width for text output in characters (default: 80)
        """
        self.width = width

    def wrap_text(self, text: str) -> str:
        """Wrap text to the specified width.

        Args:
            text: Text to wrap

        Returns:
            Wrapped text
        """
        # Split by paragraphs (double newlines) to preserve intentional breaks
        paragraphs = text.split('\n\n')
        wrapped_paragraphs = []

        for para in paragraphs:
            # Remove single newlines within paragraph (they're usually formatting artifacts)
            para = para.replace('\n', ' ')
            # Wrap the paragraph
            wrapped = textwrap.fill(para, width=self.width, break_long_words=False, break_on_hyphens=False)
            wrapped_paragraphs.append(wrapped)

        # Rejoin paragraphs with double newlines
        return '\n\n'.join(wrapped_paragraphs)

    def print(self, text: str, style: Optional[str] = None) -> None:
        """Print text with automatic wrapping.

        Args:
            text: Text to print
            style: Optional style (ignored for now, but kept for compatibility)
        """
        wrapped = self.wrap_text(text)
        print(wrapped)

    def print_separator(self, char: str = "=", length: Optional[int] = None) -> None:
        """Print a separator line.

        Args:
            char: Character to use for separator (default: "=")
            length: Length of separator (default: use text width)
        """
        sep_length = length if length is not None else self.width
        print(char * sep_length)

    def print_narrative(self, narrative: str) -> None:
        """Print narrative text with wrapping.

        Args:
            narrative: Narrative text to print
        """
        wrapped = self.wrap_text(narrative)
        print(f"\n{wrapped}")

    def print_heading(self, text: str) -> None:
        """Print a heading with styling.

        Args:
            text: Heading text
        """
        wrapped = self.wrap_text(text)
        print(f"\n{wrapped}")

    def print_error(self, text: str) -> None:
        """Print error text with styling.

        Args:
            text: Error text
        """
        wrapped = self.wrap_text(text)
        print(wrapped)

    def print_success(self, text: str) -> None:
        """Print success text with styling.

        Args:
            text: Success text
        """
        wrapped = self.wrap_text(text)
        print(wrapped)

    def print_info(self, text: str) -> None:
        """Print info text with styling.

        Args:
            text: Info text
        """
        wrapped = self.wrap_text(text)
        print(wrapped)


# Global formatter instance (can be configured)
_formatter: Optional[TextFormatter] = None


def get_formatter() -> TextFormatter:
    """Get the global text formatter instance.

    Returns:
        TextFormatter instance
    """
    global _formatter
    if _formatter is None:
        _formatter = TextFormatter()
    return _formatter


def set_text_width(width: int) -> None:
    """Set the text width for the global formatter.

    Args:
        width: Maximum width for text output in characters
    """
    global _formatter
    _formatter = TextFormatter(width=width)


def print_wrapped(text: str, style: Optional[str] = None) -> None:
    """Print text with automatic wrapping using the global formatter.

    Args:
        text: Text to print
        style: Optional rich style
    """
    get_formatter().print(text, style=style)


def print_narrative(narrative: str) -> None:
    """Print narrative text with wrapping using the global formatter.

    Args:
        narrative: Narrative text to print
    """
    get_formatter().print_narrative(narrative)


def print_separator(char: str = "=", length: Optional[int] = None) -> None:
    """Print a separator line using the global formatter.

    Args:
        char: Character to use for separator (default: "=")
        length: Length of separator (default: use text width)
    """
    get_formatter().print_separator(char, length)
