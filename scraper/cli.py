"""
CLI argument parser for the dealership scraper.
Supports multiple URL input methods as specified in original_prompt.md.
"""

import sys
import csv
from pathlib import Path
from typing import List, Optional
import click
import yaml

from .models import ScraperConfig
from .utils import get_logger


class URLInputProcessor:
    """Process and deduplicate URLs from various input sources."""

    def __init__(self):
        self.urls: List[str] = []
        self.seen_urls: set = set()
        self.sources: List[str] = []

    def add_url(self, url: str, source: str = "CLI"):
        """Add a single URL (deduplicates automatically)."""
        url = url.strip()
        if not url:
            return

        # Normalize URL for deduplication
        normalized = url.lower().rstrip('/')

        if normalized not in self.seen_urls:
            self.urls.append(url)  # Keep original casing
            self.seen_urls.add(normalized)
            if source not in self.sources:
                self.sources.append(source)

    def add_urls_from_list(self, urls: List[str], source: str = "CLI"):
        """Add multiple URLs from a list."""
        for url in urls:
            self.add_url(url, source)

    def add_urls_from_file(self, file_path: str):
        """Add URLs from a text file (one per line)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"URL file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    self.add_url(line, f"file:{file_path}")

    def add_urls_from_csv(self, csv_path: str, column: str = "url"):
        """Add URLs from a CSV file."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if column not in reader.fieldnames:
                raise ValueError(
                    f"Column '{column}' not found in CSV. "
                    f"Available columns: {', '.join(reader.fieldnames)}"
                )

            for row in reader:
                url = row.get(column, '').strip()
                if url:
                    self.add_url(url, f"csv:{csv_path}")

    def get_urls(self) -> List[str]:
        """Get the deduplicated list of URLs in input order."""
        return self.urls

    def get_summary(self) -> str:
        """Get a summary of URL sources."""
        return (
            f"Loaded {len(self.urls)} unique URL(s) "
            f"from {len(self.sources)} source(s): {', '.join(self.sources)}"
        )


@click.command()
@click.option(
    '--url',
    multiple=True,
    help='Single dealership URL (can be repeated for multiple URLs)'
)
@click.option(
    '--urls',
    help='Space-separated list of dealership URLs'
)
@click.option(
    '--url-file',
    type=click.Path(exists=True),
    help='Path to text file with URLs (one per line)'
)
@click.option(
    '--csv-file',
    type=click.Path(exists=True),
    help='Path to CSV file with URLs'
)
@click.option(
    '--csv-column',
    default='url',
    help='Column name containing URLs in CSV file (default: "url")'
)
@click.option(
    '--config',
    type=click.Path(exists=True),
    default='config.yaml',
    help='Path to configuration file (default: config.yaml)'
)
@click.option(
    '--output-file',
    help='Override output file path from config'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode (screenshots, HTML snapshots, detailed logs)'
)
@click.option(
    '--resume',
    is_flag=True,
    help='Resume from last checkpoint'
)
@click.option(
    '--headed',
    is_flag=True,
    help='Run browser in headed mode (show browser window)'
)
@click.option(
    '--timezone',
    help='Override timezone for timestamps (default: America/Chicago)'
)
@click.version_option(version='1.0.0', prog_name='Dealership Scraper')
def main(
    url: tuple,
    urls: Optional[str],
    url_file: Optional[str],
    csv_file: Optional[str],
    csv_column: str,
    config: str,
    output_file: Optional[str],
    debug: bool,
    resume: bool,
    headed: bool,
    timezone: Optional[str]
):
    """
    Dealership Data + URL Discovery Automation

    Extract comprehensive business data from dealership websites including
    contact information, hours, service URLs, website providers, and
    embedded credit application providers.

    Examples:

      # Single URL
      python main.py --url https://dealer.com

      # Multiple URLs
      python main.py --url https://dealer1.com --url https://dealer2.com

      # URLs from file
      python main.py --url-file dealerships.txt

      # URLs from CSV
      python main.py --csv-file dealerships.csv --csv-column url

      # Debug mode
      python main.py --url https://dealer.com --debug
    """

    # Load configuration
    config_data = load_config(config)

    # Process URL inputs
    processor = URLInputProcessor()

    # Priority: CLI arguments > config file
    # Add from --url flags
    if url:
        for u in url:
            processor.add_url(u, "CLI:--url")

    # Add from --urls (space-separated)
    if urls:
        url_list = urls.split()
        processor.add_urls_from_list(url_list, "CLI:--urls")

    # Add from --url-file
    if url_file:
        try:
            processor.add_urls_from_file(url_file)
        except Exception as e:
            click.echo(f"Error reading URL file: {e}", err=True)
            sys.exit(1)

    # Add from --csv-file
    if csv_file:
        try:
            processor.add_urls_from_csv(csv_file, csv_column)
        except Exception as e:
            click.echo(f"Error reading CSV file: {e}", err=True)
            sys.exit(1)

    # If no CLI URLs provided, check config file
    if not processor.get_urls():
        config_urls = config_data.get('input', {}).get('urls', [])
        config_url_file = config_data.get('input', {}).get('url_file')
        config_csv_file = config_data.get('input', {}).get('csv_file')

        if config_urls:
            processor.add_urls_from_list(config_urls, "config.yaml")

        if config_url_file:
            try:
                processor.add_urls_from_file(config_url_file)
            except Exception as e:
                click.echo(f"Error reading config URL file: {e}", err=True)
                sys.exit(1)

        if config_csv_file:
            try:
                csv_col = config_data.get('input', {}).get('csv_column', 'url')
                processor.add_urls_from_csv(config_csv_file, csv_col)
            except Exception as e:
                click.echo(f"Error reading config CSV file: {e}", err=True)
                sys.exit(1)

    # Validate that we have at least one URL
    final_urls = processor.get_urls()
    if not final_urls:
        click.echo("Error: No URLs provided.", err=True)
        click.echo("\nPlease provide URLs via:", err=True)
        click.echo("  --url <url>", err=True)
        click.echo("  --urls '<url1> <url2> ...'", err=True)
        click.echo("  --url-file <file>", err=True)
        click.echo("  --csv-file <file>", err=True)
        click.echo("\nOr configure them in config.yaml", err=True)
        sys.exit(1)

    # Print pre-flight summary
    click.echo("\n" + "=" * 60)
    click.echo("  Dealership Data + URL Discovery Automation")
    click.echo("=" * 60)
    click.echo()
    click.echo(processor.get_summary())
    click.echo()

    if debug:
        click.echo("Debug mode: ENABLED")
        click.echo("  - Screenshots will be saved to ./debug/screenshots/")
        click.echo("  - HTML snapshots will be saved to ./debug/html/")
        click.echo("  - Detailed logs will be written to ./debug/debug.log")
        click.echo()

    if resume:
        click.echo("Resume mode: ENABLED")
        click.echo("  - Will resume from last checkpoint if available")
        click.echo()

    # Build configuration
    scraper_config = build_scraper_config(
        config_data=config_data,
        urls=final_urls,
        output_file=output_file,
        debug=debug,
        headed=headed,
        timezone=timezone
    )

    # Import and run orchestrator
    try:
        from .orchestrator import run_scraper
        import asyncio

        # Run the scraper
        asyncio.run(run_scraper(scraper_config, resume=resume))

    except ImportError as e:
        click.echo(f"\nError: Missing dependency or module: {e}", err=True)
        click.echo("\nPlease ensure all dependencies are installed:", err=True)
        click.echo("  pip install -r requirements.txt", err=True)
        click.echo("  playwright install chromium", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)

    if not path.exists():
        click.echo(f"Warning: Config file not found: {config_path}", err=True)
        click.echo("Using default configuration", err=True)
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        click.echo(f"Error loading config file: {e}", err=True)
        sys.exit(1)


def build_scraper_config(
    config_data: dict,
    urls: List[str],
    output_file: Optional[str],
    debug: bool,
    headed: bool,
    timezone: Optional[str]
) -> ScraperConfig:
    """Build ScraperConfig from config file and CLI overrides."""

    # Start with config file values
    scraper_section = config_data.get('scraper', {})
    output_section = config_data.get('output', {})
    census_section = config_data.get('census', {})
    multi_location_section = config_data.get('multi_location', {})
    normalize_section = config_data.get('normalize', {})
    evidence_section = config_data.get('evidence', {})
    regional_section = config_data.get('regional', {})
    debug_section = config_data.get('debug', {})

    return ScraperConfig(
        urls=urls,
        max_concurrent=scraper_section.get('max_concurrent', 5),
        page_timeout_ms=scraper_section.get('page_timeout_ms', 30000),
        delay_between_pages_sec=scraper_section.get('delay_between_pages_sec', 3),
        retry_attempts=scraper_section.get('retry_attempts', 3),
        respect_robots_txt=scraper_section.get('respect_robots_txt', True),
        headless=not headed if headed else scraper_section.get('headless', True),
        user_agent=scraper_section.get('user_agent'),
        output_file=output_file or output_section.get('file', './output/dealership-data.md'),
        timezone=timezone or output_section.get('timezone', 'America/Chicago'),
        locale=output_section.get('locale', 'en-US'),
        normalize_phone=normalize_section.get('phone', True),
        normalize_hours=normalize_section.get('hours', True),
        normalize_urls=normalize_section.get('urls', True),
        evidence_links_required=evidence_section.get('links_required', True),
        capture_confidence_scores=evidence_section.get('capture_scores', True),
        census_enabled=census_section.get('enabled', True),
        census_api_url=census_section.get('api_url', 'https://geocoding.geo.census.gov/geocoder'),
        multi_location_enabled=multi_location_section.get('enabled', True),
        max_locations_per_site=multi_location_section.get('max_locations_per_site', 10),
        use_regional_county_labels=regional_section.get('use_regional_county_labels', False),
        debug_mode=debug,
        debug_save_screenshots=debug_section.get('save_screenshots', True),
        debug_save_html=debug_section.get('save_html', True),
        debug_log_file=debug_section.get('log_file', './debug/debug.log'),
        debug_log_network=debug_section.get('log_network', True),
    )


if __name__ == '__main__':
    main()
