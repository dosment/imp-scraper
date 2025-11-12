"""
Markdown output file writer.
Handles atomic writes to single output file.
"""

import os
from pathlib import Path
from typing import List
import tempfile
import shutil

from ..models import DealerData
from ..utils import get_logger
from .template import MarkdownTemplateBuilder


class MarkdownWriter:
    """
    Writes dealer data to single markdown file.
    Supports atomic writes and append mode for checkpoints.
    """

    def __init__(self, output_file: str, timezone: str = "America/Chicago"):
        self.output_file = Path(output_file)
        self.timezone = timezone
        self.logger = get_logger()
        self.template_builder = MarkdownTemplateBuilder(timezone=timezone)

        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def write_dealers(
        self,
        dealers: List[DealerData],
        include_header: bool = True,
        append: bool = False
    ):
        """
        Write dealer data to output file.

        Args:
            dealers: List of dealer data to write
            include_header: Include run header at top of file
            append: Append to existing file vs overwrite
        """
        self.logger.info(f"Writing {len(dealers)} dealer(s) to {self.output_file}")

        try:
            # Build content
            content_lines = []

            # Add run header if requested and not appending
            if include_header and not append:
                content_lines.append(self.template_builder.build_run_header())

            # Add dealer blocks in order
            for dealer in dealers:
                block = self.template_builder.build_dealer_block(dealer)
                content_lines.append(block)
                content_lines.append("")  # Blank line between dealers

            content = "\n".join(content_lines)

            # Write atomically
            if append and self.output_file.exists():
                # Append mode
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"Appended {len(dealers)} dealer(s)")
            else:
                # Overwrite mode with atomic write
                self._atomic_write(content)
                self.logger.info(f"Wrote {len(dealers)} dealer(s)")

        except Exception as e:
            self.logger.error(f"Error writing output file: {e}", exc_info=True)
            raise

    def _atomic_write(self, content: str):
        """
        Write content atomically using temp file + rename.
        Prevents corruption if process is interrupted.
        """
        # Create temp file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.output_file.parent,
            prefix='.tmp_',
            suffix='.md'
        )

        try:
            # Write to temp file
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)

            # Atomic rename
            shutil.move(temp_path, self.output_file)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

    def append_dealer(self, dealer: DealerData):
        """Append a single dealer to the output file."""
        self.write_dealers([dealer], include_header=False, append=True)

    def file_exists(self) -> bool:
        """Check if output file exists."""
        return self.output_file.exists()

    def get_content(self) -> str:
        """Read current content of output file."""
        if not self.output_file.exists():
            return ""

        with open(self.output_file, 'r', encoding='utf-8') as f:
            return f.read()

    def clear(self):
        """Delete output file if it exists."""
        if self.output_file.exists():
            self.output_file.unlink()
            self.logger.info(f"Cleared output file: {self.output_file}")
