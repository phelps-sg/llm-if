#!/usr/bin/env python3
"""Debug sexpdata parsing failures."""

import sys
sys.path.insert(0, '.')
from tools.zil_converter.parser import ZILParser
import sexpdata

parser = ZILParser()

# Read the file
with open("../trinity/places.zil", 'r') as f:
    content = f.read()

# Manually extract forms and try to parse them
form_type = 'OBJECT'
start_idx = 0
parsed_count = 0
failed_count = 0
failed_samples = []

while True:
    # Find next occurrence
    pattern_space = f'<{form_type} '
    pattern_newline = f'<{form_type}\n'
    pattern_tab = f'<{form_type}\t'

    pos_space = content.find(pattern_space, start_idx)
    pos_newline = content.find(pattern_newline, start_idx)
    pos_tab = content.find(pattern_tab, start_idx)

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
                form_text_converted = parser._convert_zil_to_sexp(form_text)
                try:
                    parsed = sexpdata.loads(form_text_converted)
                    parsed_count += 1
                except Exception as e:
                    failed_count += 1
                    if failed_count <= 5:  # Keep first 5 failures
                        # Extract object name
                        lines = form_text.split('\n')
                        first_line = lines[0] if lines else form_text[:50]
                        failed_samples.append({
                            'name': first_line,
                            'error': str(e),
                            'converted': form_text_converted[:500]
                        })

                break
        i += 1

    # Move past this form for next search
    start_idx = i + 1 if i < len(content) else len(content)

print(f"Parsed successfully: {parsed_count}")
print(f"Failed to parse: {failed_count}")

if failed_samples:
    print("\n" + "="*80)
    print("FAILED PARSE EXAMPLES:")
    print("="*80)
    for i, sample in enumerate(failed_samples, 1):
        print(f"\n{i}. {sample['name']}")
        print(f"   Error: {sample['error']}")
        print(f"   Converted (first 300 chars):")
        print(f"   {sample['converted'][:300]}")
