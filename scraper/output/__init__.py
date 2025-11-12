"""
Output generation module.
Builds markdown output matching original_prompt.md template.
"""

from .template import MarkdownTemplateBuilder
from .writer import MarkdownWriter

__all__ = [
    'MarkdownTemplateBuilder',
    'MarkdownWriter',
]
