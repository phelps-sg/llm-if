"""Configuration constants for the interactive fiction engine.

This module defines the single source of truth for configuration values
used throughout the application, including tests.
"""

# LLM Model Configuration
# These models are used by the game engine and should be the same in tests
DEFAULT_DM_MODEL = "gemini-2.5-flash"  # Main DM model for action interpretation and narrative
DEFAULT_ZIL_TRANSLATOR_MODEL = "gemini-2.5-flash"  # Model for translating ZIL code to natural language

# Alternative models (commented out for reference)
# DEFAULT_DM_MODEL = "gemini-2.5-flash-lite"  # Faster/cheaper but less capable
# DEFAULT_DM_MODEL = "gemini-2.5-pro"  # More capable but slower/more expensive
