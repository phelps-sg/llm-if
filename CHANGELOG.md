# Changelog

## [Unreleased] - 2025-12-19

### Added

#### 📏 Configurable Text Formatting
- **Feature**: Professional text wrapping and formatting for all game output
- **Implementation**:
  - Added `--text-width` command-line option (default: 80 characters)
  - Uses Python's built-in `textwrap` module for reliable text wrapping
  - Automatic word wrapping preserves narrative flow and paragraph breaks
- **Usage**: `if-engine worlds/zork_original.json --text-width 100`
- **Files Changed**:
  - `src/utils/text_formatter.py` - New module for text formatting utilities
  - `src/main.py:338-343, 488` - Added text width option and configuration
  - `src/engine/game_loop.py:10, 591, 647, 717` - Updated to use text formatter
- **Benefits**:
  - Clean, readable output on terminals of any size
  - Professional appearance with proper word wrapping
  - Configurable for different display preferences
  - No external dependencies required (uses stdlib)

#### 🔍 Transparent Container Visibility
- **Feature**: Items inside transparent containers are now visible even when closed
- **Implementation**: Game engine checks for transparency via:
  - `transparent: true` or `is_transparent: true` attribute
  - `"transbit"` flag in ZIL imports
- **Example**: Glass bottle shows water contents without requiring player to open it first
- **Files Changed**:
  - `src/engine/game_loop.py:1220-1228` - Added transparency check in container visibility logic
  - Updated comments throughout to reflect "open or transparent" containers
- **Test**: `test_bottle_transparency.py` ✅

#### 🚫 Blocked Exit System
- **Feature**: Support for permanently blocked exits with custom messages
- **Implementation**:
  - Locations can have `blocked_exits` attribute: `{direction: message}`
  - Game loop passes blocked exits to LLM context
  - LLM prompt includes validation rules for blocked exits
- **Example**: Kitchen chimney blocks "down" with message "Only Santa Claus climbs down chimneys."
- **Files Changed**:
  - `worlds/zork_original.json:1531-1533` - Added `blocked_exits` to kitchen location
  - `src/engine/game_loop.py:1169-1177, 1260` - Extract and pass blocked exits to LLM
  - `src/llm/gemini_client.py:4113, 4241-4246` - Added blocked exit handling to prompt
- **Test**: `test_chimney_blocking.py` ✅

#### 🔄 ZIL Import Script Improvements
- **Feature**: ZIL→JSON converter now handles conditional exits with ELSE clauses
- **Implementation**:
  - Extractor detects `(DOWN TO STUDIO IF FALSE-FLAG ELSE "message")` format
  - Converts to `blocked_exits` in location attributes
  - Converter returns tuple `(connections, blocked_exits)` from `_convert_exits()`
- **Files Changed**:
  - `tools/zil_converter/extractor.py:170, 213-244` - Added ELSE clause detection
  - `tools/zil_converter/converter.py:21-42, 146-175` - Handle blocked exits in conversion
- **Result**: Running the import script on original ZIL now automatically captures blocked exits

### Fixed

#### Bug #1: Transparent Bottle Contents Invisible
- **Problem**: Water inside closed glass bottle wasn't visible despite `transbit` flag
- **Root Cause**: Engine only showed contents when `is_open=True`, ignoring transparency
- **Fix**: Added transparency check alongside open check
- **Impact**: All transparent containers now work correctly across all ZIL imports

#### Bug #2: Missing "Santa Claus" Chimney Message
- **Problem**: Players could descend kitchen chimney when they should be blocked
- **Root Cause**: ZIL conditional exit `(DOWN TO STUDIO IF FALSE-FLAG ELSE "message")` wasn't translated to JSON
- **Fix**:
  1. Added `blocked_exits` to kitchen location
  2. Updated import script to detect ELSE clauses
  3. Added LLM validation for blocked exits
- **Impact**: Blocked exits now work correctly for all ZIL imports with ELSE clauses

### Documentation

- Updated `README.md` with transparent containers and blocked exits features
- Updated `ZIL_CONVERTER_README.md` with ELSE clause handling
- Added examples for both features in documentation
- Created tests demonstrating both fixes

### Technical Details

#### Architectural Compliance
Both features follow CLAUDE.md principles:
- ✅ Separation of mechanics and narrative (mechanics detect features, LLM narrates)
- ✅ State-driven architecture (no ad-hoc modifications)
- ✅ LLM as DM (interprets from context, doesn't manage state)
- ✅ No brittle prompt engineering (general solutions work for all similar cases)

#### Backward Compatibility
- ✅ All changes are additive - no breaking changes
- ✅ Existing JSON files work without modification
- ✅ New features optional - containers default to non-transparent, locations have no blocked exits unless specified

## Version History

### [0.1.0] - Initial Release
- Core game loop and state management
- LLM integration with Gemini
- D&D 5e combat system
- Dynamic NPC dialogue
- Intelligent lighting system
- ZIL to JSON converter (basic)
