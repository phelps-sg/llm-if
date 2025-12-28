#!/usr/bin/env python3
"""Debug ZIL parser on Trinity."""

# Read the places.zil file and manually count forms
with open("../trinity/places.zil", 'r') as f:
    content = f.read()

# Count <OBJECT occurrences
object_starts = content.count('<OBJECT ')
print(f"<OBJECT forms found by simple count: {object_starts}")

# Find each one and show first 100 chars
import re
pattern = r'<OBJECT\s+(\S+)'
matches = re.findall(pattern, content)
print(f"\nObject names found: {len(matches)}")
if len(matches) <= 20:
    print(f"Names: {matches}")
else:
    print(f"First 20: {matches[:20]}")
    print(f"Last 20: {matches[-20:]}")

# Now test the parser
print("\n" + "="*80)
print("Testing ZIL Parser:")
print("="*80)

import sys
sys.path.insert(0, '.')
from tools.zil_converter.parser import ZILParser

parser = ZILParser()

# Test the comment removal
sample = """<OBJECT PAL-GATE
	(LOC ROOMS)
	(DESC "Palace Gate")
	; This is a comment
	(FLAGS LIGHTED LOCATION WINDY)>"""

print("\nSample input:")
print(sample)
print("\nAfter _convert_zil_to_sexp:")
converted = parser._convert_zil_to_sexp(sample)
print(converted)

# Now parse the full file with debug
print("\n" + "="*80)
print("Parsing full file...")
print("="*80)

# Add instrumentation to understand what's happening
original_convert = parser._convert_zil_to_sexp

parse_count = 0
def debug_convert(zil_content):
    global parse_count
    parse_count += 1
    result = original_convert(zil_content)
    if parse_count <= 5 or parse_count > 130:
        print(f"\nForm {parse_count}:")
        print(f"  Input length: {len(zil_content)}")
        print(f"  First 100 chars: {zil_content[:100]}")
        print(f"  Output length: {len(result)}")
    return result

parser._convert_zil_to_sexp = debug_convert

try:
    sexps = parser.parse_file("../trinity/places.zil")
    print(f"\n\nTotal forms parsed: {len(sexps)}")
    print(f"Total conversion calls: {parse_count}")
except Exception as e:
    print(f"\nParser error: {e}")
    import traceback
    traceback.print_exc()
