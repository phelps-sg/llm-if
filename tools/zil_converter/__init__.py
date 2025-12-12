"""ZIL to JSON converter for Infocom games.

This tool converts classic Infocom ZIL (Zork Implementation Language) files
to the LLM-IF JSON world format, enabling classic games like Planetfall
and Zork to run with our LLM-based DM.

Usage:
    python -m tools.zil_converter path/to/zil/files/ -o output.json
"""

__version__ = "0.1.0"
