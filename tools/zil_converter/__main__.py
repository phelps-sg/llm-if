"""Make the ZIL converter package runnable as a module.

Usage:
    python -m tools.zil_converter <zil_dir> [options]
"""

from .cli import convert

if __name__ == '__main__':
    convert()
