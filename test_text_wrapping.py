"""Test script for text wrapping functionality."""

from src.utils.text_formatter import set_text_width, print_narrative, print_separator

# Test with different widths
long_text = """You stand in the grand entrance hall of an ancient castle. Towering stone pillars rise toward a vaulted ceiling lost in shadow. Massive wooden doors behind you are now sealed shut, their iron bands glowing with an eerie blue light. Before you, a wide staircase ascends into darkness. To your left, an archway leads to what appears to be a great hall, and to your right, a narrow corridor disappears around a corner. The air is thick with dust and the faint scent of decay."""

print("=" * 80)
print("Testing with width=80 (default):")
print("=" * 80)
set_text_width(80)
print_narrative(long_text)

print("\n\n" + "=" * 60)
print("Testing with width=60:")
print("=" * 60)
set_text_width(60)
print_narrative(long_text)

print("\n\n" + "=" * 40)
print("Testing with width=40:")
print("=" * 40)
set_text_width(40)
print_narrative(long_text)

print("\n\n" + "=" * 100)
print("Testing with width=100:")
print("=" * 100)
set_text_width(100)
print_narrative(long_text)

print("\n\nText wrapping test complete!")
