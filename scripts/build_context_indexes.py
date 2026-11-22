#!/usr/bin/env python3
"""Compatibility command for build_indexes.py [--check] [ROOT].

Run me when: I need the original command name for build_indexes.py.
"""
import sys

from build_indexes import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
