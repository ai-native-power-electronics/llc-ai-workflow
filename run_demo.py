#!/usr/bin/env python3
"""One-command entry point for power-electronics engineers new to Python."""

from __future__ import annotations

import sys

from llc_tool.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["demo", *sys.argv[1:]]))
