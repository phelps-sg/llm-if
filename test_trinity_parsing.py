#!/usr/bin/env python3
"""Test Trinity location detection."""

import sys
sys.path.insert(0, '.')

from tools.zil_converter.parser import ZILParser
from tools.zil_converter.extractor import GameExtractor
from sexpdata import Symbol

# Parse Trinity places.zil
parser = ZILParser()
sexps = parser.parse_file("../trinity/places.zil")

print(f"Total S-expressions: {len(sexps)}")

# Count OBJECT forms
object_count = 0
location_count = 0
location_flag_count = 0
loc_rooms_count = 0

for sexp in sexps:
    if not isinstance(sexp, list) or len(sexp) < 2:
        continue

    form_type = str(sexp[0]).upper() if isinstance(sexp[0], Symbol) else ""

    if form_type == "OBJECT":
        object_count += 1

        # Parse properties manually
        props = {}
        for item in sexp[2:]:
            if isinstance(item, list) and len(item) >= 2:
                prop_name = str(item[0]).upper() if isinstance(item[0], Symbol) else str(item[0])
                if prop_name in ["LOC", "FLAGS", "DESC"]:
                    if len(item) == 2:
                        props[prop_name] = item[1]
                    else:
                        props[prop_name] = item[1:]

        # Check LOC
        loc = props.get("LOC")
        if loc:
            loc_str = str(loc).upper() if hasattr(loc, '__str__') else ""
            if loc_str == "ROOMS":
                loc_rooms_count += 1
                name = str(sexp[1]) if len(sexp) > 1 else "unknown"
                print(f"  LOC ROOMS found: {name}")

        # Check FLAGS
        flags = props.get("FLAGS")
        if flags:
            flag_list = flags if isinstance(flags, (list, tuple)) else [flags]
            for f in flag_list:
                if str(f).upper() == "LOCATION":
                    location_flag_count += 1
                    location_count += 1
                    break
            if loc_str == "ROOMS" and str(sexp[1]) == "PAL-GATE":
                print(f"  PAL-GATE flags: {[str(f) for f in flag_list]}")

print(f"\nOBJECT forms: {object_count}")
print(f"With LOC ROOMS: {loc_rooms_count}")
print(f"With LOCATION flag: {location_flag_count}")
