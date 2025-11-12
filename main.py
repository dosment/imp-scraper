#!/usr/bin/env python3
"""
Dealership Data + URL Discovery Automation
Main entry point for the scraper.
"""

import sys
from pathlib import Path

# Add scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper.cli import main

if __name__ == "__main__":
    main()
