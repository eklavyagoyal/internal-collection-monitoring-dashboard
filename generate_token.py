#!/usr/bin/env python3
"""
One-time helper to generate token.json for Google Calendar OAuth.

Run this on a machine with a browser BEFORE starting Docker:

    python3 generate_token.py

It will open a browser for Google OAuth consent, then save token.json
in the project root.  Docker Compose mounts this file read-only.
"""

import os
import sys

# Ensure we can import the package
sys.path.insert(0, os.path.dirname(__file__))

from nexus_track.backend.gcal_sync import generate_token

if __name__ == "__main__":
    generate_token()
