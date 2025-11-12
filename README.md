# Dealership Data + URL Discovery Automation

A Python-based web scraper that extracts comprehensive business data from dealership websites including contact information, hours, service URLs, website providers, and embedded credit application providers.

## Features

- **Multi-source input**: Single URL, multiple URLs, text file, or CSV
- **Comprehensive extraction**: Address, phone, hours, URLs, providers, county
- **Google Maps integration**: Address verification from Google Maps
- **Census Bureau lookup**: County verification via U.S. Census Bureau
- **Multi-location support**: Handles dealerships with multiple rooftops
- **Checkpoint recovery**: Resume interrupted scraping sessions
- **Concurrent processing**: Process up to 5 dealerships simultaneously
- **Respectful scraping**: Honors robots.txt and rate limits
- **Debug mode**: Screenshots, HTML snapshots, detailed logs

## Installation

```bash
# Clone or create project
cd dealership-scraper

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```bash
# Run with single URL
python main.py --url https://dealer.com

# Run with multiple URLs
python main.py --urls https://dealer1.com https://dealer2.com

# Run with URL file
python main.py --url-file dealerships.txt

# Run with CSV file
python main.py --csv-file dealerships.csv --csv-column url

# Enable debug mode
python main.py --url https://dealer.com --debug
```

## Configuration

Edit `config.yaml` to customize scraping behavior, output settings, and extraction priorities.

## Output

Results are written to `output/dealership-data.md` as a single Markdown file with one code block per dealership.

## Documentation

See `dealership-scraper-plan.md` for comprehensive implementation details.

## License

Internal use only.
