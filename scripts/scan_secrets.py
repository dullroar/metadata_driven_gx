#!/usr/bin/env python3
"""Scan context Markdown for credentials and personal data. Usage: scan_secrets.py [ROOT].

Run me when: I added examples, logs, or paths to context files, and before every pull request.
"""
import sys

from scan_context_secrets import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
