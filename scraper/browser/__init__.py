"""
Browser automation module.
Provides Playwright-based browser management and navigation.
"""

from .manager import BrowserManager
from .context import DealerContext
from .robotstxt import RobotsTxtChecker

__all__ = [
    'BrowserManager',
    'DealerContext',
    'RobotsTxtChecker',
]
