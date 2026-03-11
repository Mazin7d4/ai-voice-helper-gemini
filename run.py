"""
run.py — Entry point for the AI Voice Helper application.

Launches the full GUI with voice, vision, and action execution.
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.overlay import main

if __name__ == "__main__":
    main()
