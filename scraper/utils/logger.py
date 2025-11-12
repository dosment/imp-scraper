"""
Logging utilities for the scraper.
Supports both normal mode (rich console output) and debug mode (detailed logs).
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Progress = None


class ScraperLogger:
    """
    Logger for the scraper with rich console output and optional debug mode.
    """

    def __init__(self, debug_mode: bool = False, debug_log_file: Optional[str] = None):
        self.debug_mode = debug_mode
        self.debug_log_file = debug_log_file

        # Initialize console (rich or fallback)
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        # Setup Python logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure Python logging."""
        # Create logger
        self.logger = logging.getLogger('dealership-scraper')
        self.logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler
        if RICH_AVAILABLE and not self.debug_mode:
            console_handler = RichHandler(rich_tracebacks=True)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)

        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

        # File handler for debug mode
        if self.debug_mode and self.debug_log_file:
            log_path = Path(self.debug_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path, mode='a')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def print_header(self, title: str):
        """Print a header/banner."""
        if self.console and RICH_AVAILABLE:
            self.console.print(Panel(title, style="bold blue"))
        else:
            print(f"\n{'=' * 60}")
            print(f"  {title}")
            print(f"{'=' * 60}\n")

    def print_section(self, title: str):
        """Print a section header."""
        if self.console and RICH_AVAILABLE:
            self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        else:
            print(f"\n{title}")
            print("-" * len(title))

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)

    def success(self, message: str):
        """Log success message."""
        if self.console and RICH_AVAILABLE:
            self.console.print(f"[green]✓[/green] {message}")
        else:
            self.logger.info(f"✓ {message}")

    def print_table(self, title: str, data: list, headers: list):
        """Print a formatted table."""
        if self.console and RICH_AVAILABLE:
            table = Table(title=title)
            for header in headers:
                table.add_column(header)
            for row in data:
                table.add_row(*[str(cell) for cell in row])
            self.console.print(table)
        else:
            print(f"\n{title}")
            print("-" * len(title))
            # Simple text table
            col_widths = [max(len(str(row[i])) for row in [headers] + data)
                         for i in range(len(headers))]
            row_format = "  ".join([f"{{:<{w}}}" for w in col_widths])
            print(row_format.format(*headers))
            print("-" * sum(col_widths))
            for row in data:
                print(row_format.format(*[str(cell) for cell in row]))
            print()

    def print_summary(self, total: int, successful: int, failed: int, duration: float):
        """Print completion summary."""
        self.print_section("Scraping Complete")

        data = [
            ["Total dealerships", total],
            ["Successful", successful],
            ["Failed", failed],
            ["Duration", f"{duration:.1f}s"],
        ]

        if self.console and RICH_AVAILABLE:
            table = Table(show_header=False)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="bold")
            for row in data:
                table.add_row(str(row[0]), str(row[1]))
            self.console.print(table)
        else:
            for metric, value in data:
                print(f"  {metric}: {value}")

    def create_progress(self, total: int) -> Optional['Progress']:
        """Create a progress bar for tracking."""
        if self.console and RICH_AVAILABLE and not self.debug_mode:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            )
        return None

    def save_debug_screenshot(self, screenshot_data: bytes, dealer_name: str, page_name: str):
        """Save screenshot in debug mode."""
        if not self.debug_mode:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_dealer = "".join(c for c in dealer_name if c.isalnum() or c in (' ', '_')).strip()
        safe_dealer = safe_dealer.replace(' ', '_')

        screenshot_dir = Path('./debug/screenshots')
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        filename = screenshot_dir / f"{safe_dealer}_{page_name}_{timestamp}.png"

        with open(filename, 'wb') as f:
            f.write(screenshot_data)

        self.debug(f"Screenshot saved: {filename}")

    def save_debug_html(self, html_content: str, dealer_name: str, page_name: str):
        """Save HTML snapshot in debug mode."""
        if not self.debug_mode:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_dealer = "".join(c for c in dealer_name if c.isalnum() or c in (' ', '_')).strip()
        safe_dealer = safe_dealer.replace(' ', '_')

        html_dir = Path('./debug/html')
        html_dir.mkdir(parents=True, exist_ok=True)

        filename = html_dir / f"{safe_dealer}_{page_name}_{timestamp}.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.debug(f"HTML snapshot saved: {filename}")


# Global logger instance
_logger_instance: Optional[ScraperLogger] = None


def get_logger() -> ScraperLogger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ScraperLogger()
    return _logger_instance


def init_logger(debug_mode: bool = False, debug_log_file: Optional[str] = None) -> ScraperLogger:
    """Initialize the global logger."""
    global _logger_instance
    _logger_instance = ScraperLogger(debug_mode=debug_mode, debug_log_file=debug_log_file)
    return _logger_instance
