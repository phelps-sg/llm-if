"""Command-line interface for ZIL to JSON converter."""

import click
import json
import glob
import os
from pathlib import Path
from typing import Dict

from .parser import ZILParser
from .extractor import GameExtractor
from .converter import WorldConverter
from .pattern_matcher import SmartConverter


@click.command()
@click.argument('zil_dir', type=click.Path(exists=True))
@click.option('--output', '-o', default='world_converted.json', help='Output JSON file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--extract-only', is_flag=True, help='Extract only, no smart conversion')
@click.option('--notes', '-n', default=None, help='Output file for adaptation notes (default: <output>_NOTES.md)')
def convert(zil_dir, output, verbose, extract_only, notes):
    """Convert ZIL game files to LLM-IF JSON format.

    ZIL_DIR: Directory containing .zil files (e.g., ../planetfall-invclues/)

    Examples:

        \b
        # Basic conversion
        python -m tools.zil_converter ../planetfall-invclues/ -o worlds/planetfall.json

        \b
        # Extract only, no smart pattern matching
        python -m tools.zil_converter ../planetfall-invclues/ --extract-only -o planetfall_raw.json

        \b
        # Verbose mode with custom notes file
        python -m tools.zil_converter ../planetfall-invclues/ -v -n PLANETFALL_NOTES.md
    """
    click.echo("🔧 ZIL to JSON Converter")
    click.echo("=" * 50)

    # Set up notes file path
    if notes is None:
        notes = output.replace('.json', '_NOTES.md')

    # 1. Find and parse all .zil files
    zil_pattern = os.path.join(zil_dir, "*.zil")
    zil_files = glob.glob(zil_pattern)

    if not zil_files:
        click.echo(f"❌ No .zil files found in {zil_dir}", err=True)
        return

    click.echo(f"\n📂 Found {len(zil_files)} ZIL files:")
    for zil_file in sorted(zil_files):
        click.echo(f"   - {os.path.basename(zil_file)}")

    # 2. Parse all ZIL files
    click.echo("\n📖 Parsing ZIL files...")
    parser = ZILParser()
    all_sexps = []

    for zil_file in zil_files:
        if verbose:
            click.echo(f"   Parsing {os.path.basename(zil_file)}...")
        try:
            sexps = parser.parse_file(zil_file)
            all_sexps.extend(sexps)
            if verbose:
                click.echo(f"      ✓ {len(sexps)} forms parsed")
        except Exception as e:
            click.echo(f"   ⚠️  Error parsing {os.path.basename(zil_file)}: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()

    if verbose:
        # Show form types found
        form_types = parser.find_all_form_types(all_sexps)
        click.echo(f"\n   Form types found: {', '.join(sorted(form_types))}")

    # 3. Extract entities
    click.echo("\n🔍 Extracting game entities...")
    extractor = GameExtractor()
    game_data = extractor.extract(all_sexps)

    rooms_count = len(game_data['rooms'])
    objects_count = len(game_data['objects'])
    npcs_count = len(game_data['npcs'])
    todos_count = len(game_data['todos'])

    click.echo(f"   ✓ {rooms_count} rooms")
    click.echo(f"   ✓ {objects_count} objects")
    click.echo(f"   ✓ {npcs_count} NPCs")
    if todos_count > 0:
        click.echo(f"   ⚠️  {todos_count} items need manual review")

    if verbose and rooms_count > 0:
        click.echo(f"\n   Sample rooms: {', '.join([r['id'] for r in game_data['rooms'][:5]])}")
    if verbose and objects_count > 0:
        click.echo(f"   Sample objects: {', '.join([o['id'] for o in game_data['objects'][:5]])}")

    # 4. Convert to JSON format
    click.echo("\n🔄 Converting to JSON world format...")
    converter = WorldConverter()
    json_world = converter.convert(game_data, smart=not extract_only)

    # 5. Apply smart conversions if enabled
    if not extract_only:
        click.echo("   Applying smart pattern matching...")
        smart_converter = SmartConverter()
        json_world = smart_converter.apply_smart_conversions(game_data, json_world)

        puzzles_count = len(json_world.get("puzzles", {}))
        if puzzles_count > 0:
            click.echo(f"   ✓ {puzzles_count} puzzles auto-generated")

        # Collect todos from smart conversion
        smart_todos = smart_converter.get_todos()
        game_data['todos'].extend(smart_todos)

    # 6. Write output JSON
    click.echo(f"\n💾 Writing output to {output}...")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output, 'w') as f:
        json.dump(json_world, f, indent=2)

    click.echo(f"   ✓ World JSON saved")

    # 7. Write adaptation notes
    click.echo(f"\n📝 Writing adaptation notes to {notes}...")
    notes_content = _generate_notes(game_data, json_world, converter)

    with open(notes, 'w') as f:
        f.write(notes_content)

    click.echo(f"   ✓ Notes saved")

    # 8. Summary
    click.echo("\n" + "=" * 50)
    click.echo("✅ Conversion complete!")
    click.echo(f"\n📊 Summary:")
    click.echo(f"   Locations: {len(json_world['locations'])}")
    click.echo(f"   Items: {len(json_world['items'])}")
    click.echo(f"   NPCs: {len(json_world['npcs'])}")
    click.echo(f"   Puzzles: {len(json_world.get('puzzles', {}))}")
    click.echo(f"   Manual TODOs: {len(game_data['todos'])}")

    click.echo(f"\n📂 Output files:")
    click.echo(f"   - World JSON: {output}")
    click.echo(f"   - Adaptation notes: {notes}")

    if game_data['todos']:
        click.echo(f"\n⚠️  Please review {notes} for manual adaptation tasks!")


def _generate_notes(game_data: Dict, json_world: Dict, converter: WorldConverter) -> str:
    """Generate adaptation notes markdown."""
    notes = "# ZIL Conversion - Adaptation Notes\n\n"
    notes += f"Generated from ZIL source files\n\n"

    # Conversion summary
    notes += "## Conversion Summary\n\n"
    notes += f"- **Locations**: {len(json_world['locations'])}\n"
    notes += f"- **Items**: {len(json_world['items'])}\n"
    notes += f"- **NPCs**: {len(json_world['npcs'])}\n"
    notes += f"- **Puzzles**: {len(json_world.get('puzzles', {}))}\n"
    notes += f"- **Manual review items**: {len(game_data['todos'])}\n\n"

    # TODO items
    if game_data['todos']:
        notes += "## Manual Review Required\n\n"
        notes += "The following items need manual review and possible implementation:\n\n"

        for i, todo in enumerate(game_data['todos'], 1):
            notes += f"### {i}. {todo.split(':')[0] if ':' in todo else 'TODO'}\n\n"
            notes += f"{todo}\n\n"
    else:
        notes += "## Manual Review\n\n"
        notes += "✅ No manual adaptations needed - conversion was clean!\n\n"

    # Conversion notes from converters
    converter_notes = converter.get_todo_notes()
    if "No manual adaptations" not in converter_notes:
        notes += "## Additional Conversion Notes\n\n"
        notes += converter_notes + "\n\n"

    # Next steps
    notes += "## Next Steps\n\n"
    notes += "1. **Review** this file and prioritize adaptations\n"
    notes += "2. **Test** the converted world in the LLM-IF engine\n"
    notes += "3. **Implement** custom behaviors for NPCs with action routines\n"
    notes += "4. **Add** puzzle logic for conditional exits\n"
    notes += "5. **Polish** descriptions and attributes based on playtesting\n"
    notes += "6. **Validate** that the LLM DM correctly interprets ZIL attributes\n\n"

    # Reference
    notes += "## Reference\n\n"
    notes += "### ZIL Flags Preserved\n\n"
    notes += "The converter preserves ZIL flags as `zil_flags` attributes.\n"
    notes += "The LLM DM can interpret these for game behavior.\n\n"

    notes += "Common flags:\n"
    notes += "- `takebit` - Item can be taken\n"
    notes += "- `contbit` - Container\n"
    notes += "- `doorbit` - Door\n"
    notes += "- `lockedbit` - Locked\n"
    notes += "- `lightbit` - Light source\n"
    notes += "- `actorbit` - NPC\n"
    notes += "- `villainbit` - Hostile NPC\n\n"

    return notes


if __name__ == '__main__':
    convert()
