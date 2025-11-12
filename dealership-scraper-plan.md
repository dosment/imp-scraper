# Dealership Web Scraper - Comprehensive Implementation Plan

## Executive Summary

A Python-based web scraper that takes dealership URLs as input and automatically extracts comprehensive business data including contact information, hours, service URLs, website providers, and embedded credit application providers.

---

## Requirements Summary

✅ **Modular Architecture**: Max 500 lines per file, lego-methodology
✅ **Input**: CLI accepts one URL, many URLs, or CSV file of URLs before scraping starts
✅ **Browser**: Playwright + Chromium (Python 3.12+)
✅ **Address Source**: Scrape from dealership website (extremely reliable)
✅ **Concurrency**: Process up to 5 dealerships simultaneously
✅ **Multi-location**: Extract ALL locations separately
✅ **Phone**: Main/sales number only
✅ **Data Quality**: Output everything found, mark missing as 'Unsure'
✅ **Logging**: Verbose console logs + optional `--debug` mode
✅ **Politeness**: Respect robots.txt, 2-5 second delays
✅ **Recovery**: Save progress checkpoints, resume on crash
✅ **Output**: Single markdown file per run using original_prompt.md format (code block per dealer in input order)
✅ **No Caching**: Fresh scrape every time
✅ **No Metrics**: Just data output

---

## Project Structure

```
dealership-scraper/
├── config.yaml                      # User configuration
├── requirements.txt                 # Python 3.12+ dependencies
├── .checkpoints/                    # Progress tracking (gitignored)
├── main.py                          # ~100 lines - CLI entry point
│
├── scraper/
│   ├── __init__.py                  # Plugin registration system
│   ├── orchestrator.py              # ~250 lines - main coordinator
│   ├── models.py                    # ~200 lines - Pydantic data models
│   ├── checkpoint.py                # ~150 lines - progress save/resume
│   │
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── manager.py               # ~200 lines - browser pool management
│   │   ├── context.py               # ~150 lines - isolated browser contexts
│   │   ├── navigation.py            # ~150 lines - page navigation helpers
│   │   └── robotstxt.py             # ~100 lines - robots.txt parser
│   │
│   ├── extractors/
│   │   ├── __init__.py              # ~50 lines - extractor registry
│   │   ├── base.py                  # ~100 lines - abstract base extractor
│   │   ├── location_detector.py     # ~250 lines - detect multiple locations
│   │   ├── address.py               # ~300 lines - multi-strategy address extraction
│   │   ├── phone.py                 # ~150 lines - sales phone extraction
│   │   ├── hours_finder.py          # ~200 lines - locate hours pages
│   │   ├── hours_parser.py          # ~250 lines - parse hours text
│   │   ├── url_service.py           # ~200 lines - service scheduler URL
│   │   ├── url_credit.py            # ~200 lines - credit application URL
│   │   ├── url_facebook.py          # ~150 lines - Facebook page URL
│   │   ├── provider_website.py      # ~250 lines - website provider detection
│   │   └── provider_credit.py       # ~250 lines - credit app iframe/script detection
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── county_census.py         # ~200 lines - Census Bureau API client
│   │   ├── normalizer_phone.py      # ~100 lines - phone number formatting
│   │   ├── normalizer_hours.py      # ~150 lines - hours formatting
│   │   ├── normalizer_url.py        # ~100 lines - URL cleaning
│   │   └── retry_handler.py         # ~200 lines - smart retry with fallbacks
│   │
│   ├── output/
│   │   ├── __init__.py              # ~40 lines - wiring + dependency injection
│   │   ├── template.py              # ~220 lines - builds blocks using original_prompt.md format
│   │   ├── aggregator.py            # ~180 lines - ensures single markdown file per run, preserves order
│   │   └── writer.py                # ~90 lines - buffered writes + atomic save to `output/dealers.md`
│   │
│   └── utils/
│       ├── __init__.py
│       ├── patterns.py              # ~200 lines - regex patterns library
│       ├── validators.py            # ~150 lines - data validators
│       └── logger.py                # ~150 lines - logging + debug mode
│
├── data/
│   ├── provider_fingerprints.yaml   # Website provider detection patterns
│   └── credit_fingerprints.yaml     # Credit provider detection patterns
│
└── output/                          # Generated single-file markdown output
    └── [Dealership Name].md
```

**Total**: ~30+ files, ~4000-5000 lines of code

---

## Architecture Principles

### Lego-Methodology (Plug-and-Play)

1. **Clear Interfaces**: All components communicate through defined protocols
2. **Dependency Injection**: Easy to swap implementations
3. **Plugin Architecture**: Extractors and outputs register dynamically
4. **Single Responsibility**: Each module does one thing well
5. **Testable**: Components can be tested independently

### Base Extractor Interface

```python
class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, page, context: DealerContext) -> ExtractionResult:
        """Extract specific data from page"""

    @abstractmethod
    def get_fallback_strategies(self) -> List[Strategy]:
        """Return ordered fallback strategies"""
```

### Markdown Template Builder Interface

```python
class MarkdownBlockBuilder(ABC):
    @abstractmethod
    def build_block(self, dealer_data: DealerData) -> str:
        """Return a markdown code block exactly matching original_prompt.md format"""
```

---

## Key Components

### 1. Multi-Location Detector (`location_detector.py` ~250 lines)

**Purpose**: Identify and extract all physical locations from a dealership website

**Strategy**:
1. Check for locations page (`/locations`, `/dealerships`, `/stores`)
2. Parse page for multiple addresses + unique links
3. Look for:
   - Multiple addresses on same page
   - Repeated schema.org LocalBusiness entries
   - Links with `/location/`, `/store/`, city names
4. Extract each location's unique URL or identifier
5. Create separate `DealerContext` for each location

**Output**: `List[LocationInfo]` with URLs/identifiers for each location

---

### 2. Address Extractor (`address.py` ~300 lines)

**Purpose**: Extremely reliable address extraction using multiple fallback strategies

**6 Fallback Strategies** (~40-50 lines each):

1. **Schema.org JSON-LD** (Highest priority)
   - Search for `<script type="application/ld+json">`
   - Extract `LocalBusiness.address`
   - Most reliable method

2. **Structured Microdata**
   - Check schema.org microdata attributes
   - `itemprop="streetAddress"`, `itemprop="addressLocality"`, etc.

3. **Contact Page Parsing**
   - Navigate to `/contact`, `/contact-us`
   - Regex patterns for US addresses
   - Pattern: `\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|...)`

4. **Footer Section**
   - Parse `<footer>` element for address text
   - Look for address icons/labels

5. **Header/Top Section**
   - Parse `<header>` or top navigation
   - Some sites display address prominently at top

6. **About/Locations Page**
   - Fallback to `/about`, `/locations`, `/about-us`
   - Similar regex extraction

**Validation** (~40 lines):
- Verify street number, city, state, ZIP present
- Validate state (2-letter abbreviation)
- Validate ZIP (5 or 9 digits)
- Assign confidence score (high/medium/low)
- Mark "Unsure" if confidence is low

---

### 3. Hours Extractor (Split into 2 modules)

#### `hours_finder.py` (~200 lines)
**Purpose**: Discover pages containing business hours

**Strategy**:
1. Try common URL patterns: `/hours`, `/contact`, `/locations`, `/about`
2. Search navigation menu for "Hours", "Contact Us", "Visit Us"
3. Check footer for hours information
4. Look for "Hours" heading on homepage

#### `hours_parser.py` (~250 lines)
**Purpose**: Parse hours text into structured format

**Capabilities**:
- Parse various formats: "Mon-Fri: 9:00 AM - 6:00 PM"
- Handle split hours: "Mon: 9-1; 2-6"
- Recognize "Closed", "By Appointment"
- Extract sales, service, and parts hours separately
- Normalize to en dash separator
- Output Monday-Sunday order

---

### 4. Provider Detectors (2 separate modules)

#### `provider_website.py` (~250 lines)
**Purpose**: Identify website platform provider

**Detection Methods**:
1. Footer branding ("Powered by Dealer.com")
2. Legal pages (privacy policy, terms, accessibility)
3. Page source fingerprints (meta tags, comments)
4. Network requests (analytics, CDN domains)
5. Structured data (`softwareVersion`, `publisher`)

**Fingerprints** (loaded from YAML):
- Dealer.com (Cox Automotive)
- Dealer Inspire
- DealerOn
- Dealer eProcess
- Team Velocity / Apollo Sites
- Sokal
- Dealer Spike
- Dealer Alchemist
- Jazel Auto
- Carsforsale.com (SiteFLEX)

#### `provider_credit.py` (~250 lines)
**Purpose**: Detect embedded credit application provider

**Detection Methods**:
1. Inspect credit app page for `<iframe>` src domains
2. Check `<script>` tags for credit provider URLs
3. Examine canonical/data-* attributes
4. Monitor network requests
5. Search page source/comments for vendor hints

**Supported Providers** (from original prompt):
- 700Credit
- RouteOne
- Dealertrack
- Secure Accelerate (Dealer.com)
- AutoFi
- eLEND Solutions
- Darwin Automotive
- CUDL
- Informativ (formerly Credit Bureau Connection)

---

### 5. Checkpoint Manager (`checkpoint.py` ~150 lines)

**Purpose**: Enable crash recovery and resume functionality

**Checkpoint Format** (`.checkpoints/session_[timestamp].json`):
```json
{
  "session_id": "20251112_145030",
  "started": "2025-11-12T14:50:30",
  "completed": [
    {
      "url": "https://dealer1.com",
      "status": "success",
      "locations_found": 2,
      "completed_at": "2025-11-12T14:52:15"
    }
  ],
  "failed": [
    {
      "url": "https://dealer2.com",
      "error": "Timeout",
      "attempted_at": "2025-11-12T14:55:00"
    }
  ],
  "pending": [
    "https://dealer3.com",
    "https://dealer4.com"
  ]
}
```

**Behavior**:
- Save checkpoint after each completed dealership
- On startup: load checkpoint, skip completed URLs
- Continue from pending list
- Option to retry failed URLs

---

### 6. Robots.txt Handler (`robotstxt.py` ~100 lines)

**Purpose**: Respect website scraping policies

**Functionality**:
- Fetch and parse `robots.txt` before scraping
- Check if User-agent is disallowed
- Respect `Crawl-delay` directive
- Log warning if scraping is disallowed
- Allow override in config (for authorized scraping)

---

### 7. Debug Mode (`logger.py` ~150 lines)

**Normal Mode**:
- Verbose console output with progress bars (using `rich` library)
- Real-time status updates
- Summary of completed dealerships

**Debug Mode** (activated with `--debug` flag):
- **Screenshots**: Save failed pages to `./debug/screenshots/[dealership]_[page]_[timestamp].png`
- **HTML Snapshots**: Save to `./debug/html/[dealership]_[page]_[timestamp].html`
- **Detailed Logs**: Write to `./debug/debug.log`
- **Network Trace**: Log all HTTP requests/responses
- **Timing Info**: Record time spent on each operation
- **Stack Traces**: Full error details

---

### 8. Markdown Block Builder & Aggregator

**Purpose**: Produce a single markdown file whose per-dealer sections exactly match `output_format.markdown_per_dealer` from `original_prompt.md`.

**Template Builder (`template.py` ~220 lines)**:
1. Accepts normalized `DealerData`.
2. Fills the original template verbatim (county under address, en dash hours, evidence bullets).
3. Wraps each dealer in a fenced code block (` ```markdown ... ``` `) to satisfy `output_style: markdown_codebox_per_dealer`.
4. Includes guard rails (assertions/tests) that ensure labels/order never drift from the prompt.

**Aggregator (`aggregator.py` ~180 lines)**:
1. Preserves input order by collecting dealer blocks in-memory (or streaming with async queue).
2. Applies optional checkpoints so partially written runs can resume without breaking the single file.
3. On completion, writes/overwrites `output/dealership-data.md`.
4. Adds run header (timestamp) plus sequential dealer blocks.

**Writer (`writer.py` ~90 lines)**:
- Handles atomic writes (temp file + rename) to avoid truncated single output.
- Supports `append=False` semantics so reruns start clean unless `--resume` is set.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                           │
│    • Load config.yaml                                        │
│    • Parse input URLs                                        │
│    • Check for checkpoint file → resume if exists           │
│    • Initialize browser pool                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ROBOTS.TXT CHECK                                         │
│    • Fetch robots.txt for each domain                       │
│    • Check if scraping is allowed                           │
│    • Note crawl-delay requirements                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CONCURRENT PROCESSING (up to 5 dealerships)             │
│    For each dealership URL:                                 │
│                                                              │
│    ┌─────────────────────────────────────────┐             │
│    │ 3a. LAUNCH BROWSER CONTEXT              │             │
│    │     • Isolated browser session           │             │
│    │     • Navigate to homepage               │             │
│    └─────────────────────────────────────────┘             │
│                     ↓                                        │
│    ┌─────────────────────────────────────────┐             │
│    │ 3b. MULTI-LOCATION DETECTION            │             │
│    │     • Scan for locations page            │             │
│    │     • Extract all location URLs          │             │
│    │     • Create List[LocationInfo]          │             │
│    └─────────────────────────────────────────┘             │
│                     ↓                                        │
│    ┌─────────────────────────────────────────┐             │
│    │ 3c. FOR EACH LOCATION:                  │             │
│    │                                          │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ • Extract Address (6 strategies)│    │             │
│    │  │ • Extract Phone (header/footer) │    │             │
│    │  │ • Identify site navigation       │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ • Visit hours/contact page      │    │             │
│    │  │ • Extract Sales hours           │    │             │
│    │  │ • Extract Service hours         │    │             │
│    │  │ • Extract Parts hours           │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ • Discover service scheduler    │    │             │
│    │  │ • Discover credit app page      │    │             │
│    │  │ • Discover Facebook URL         │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ • Detect website provider       │    │             │
│    │  │ • Detect credit app provider    │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ • Lookup county (Census API)    │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ NORMALIZE ALL DATA:             │    │             │
│    │  │ • Phone: (XXX) XXX-XXXX format  │    │             │
│    │  │ • Hours: en dash, Mon-Sun order │    │             │
│    │  │ • URLs: remove tracking params  │    │             │
│    │  └────────────────────────────────┘    │             │
│    │              ↓                           │             │
│    │  ┌────────────────────────────────┐    │             │
│    │  │ GENERATE OUTPUT:                │    │             │
    │    │  │ • Build markdown block (prompt format) │ │         │
    │    │  │ • Append to single run-level .md file  │ │         │
    │    │  │ • Persist evidence + checkpoints       │ │         │
│    │  └────────────────────────────────┘    │             │
│    │                                          │             │
│    └─────────────────────────────────────────┘             │
│                     ↓                                        │
│    ┌─────────────────────────────────────────┐             │
│    │ 3d. SAVE CHECKPOINT                     │             │
│    │     • Mark dealership as completed       │             │
│    │     • Save progress to checkpoint file   │             │
│    └─────────────────────────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. CLEANUP                                                  │
│    • Close all browser contexts                             │
│    • Display completion summary                             │
│    • Report path to aggregated markdown file                │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration File (config.yaml)

```yaml
# ============================================================
# INPUT URLS
# ============================================================
input:
  # Option 1: Direct list
  urls:
    - https://www.exampledealer1.com/
    - https://www.exampledealer2.com/

  # Option 2: Load from file (one URL per line)
  # url_file: ./dealerships.txt

  # Option 3: Load from CSV (column name "url")
  # csv_file: ./dealerships.csv

# ============================================================
# SCRAPING BEHAVIOR
# ============================================================
scraper:
  # Maximum number of concurrent dealerships to process
  max_concurrent: 5

  # Page load timeout in milliseconds
  page_timeout_ms: 30000

  # Delay between page visits (seconds) - politeness
  delay_between_pages_sec: 3

  # Number of retry attempts for failed operations
  retry_attempts: 3

  # Respect robots.txt (recommended: true)
  respect_robots_txt: true

  # Run browser in headless mode (false for debugging)
  headless: true

  # User agent string (leave default for realistic UA)
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============================================================
# OUTPUT SETTINGS
# ============================================================
output:
  # Single markdown file written per run (matches original_prompt.md template)
  file: ./output/dealership-data.md

  # Optional header injected at top of the file
  run_header: "# Dealership Data + URL Discovery — Run started at {{timestamp}}"

  # Timezone for timestamps
  timezone: America/Chicago

  # Overwrite existing files
  # If true, overwrite file on fresh run; otherwise append (used only with --resume)
  overwrite_existing: true

# ============================================================
# EXTERNAL SERVICES
# ============================================================
census:
  # Enable county lookup via Census Bureau API
  enabled: true

  # Census Geocoder API endpoint
  api_url: https://geocoding.geo.census.gov/geocoder

# ============================================================
# MULTI-LOCATION SETTINGS
# ============================================================
multi_location:
  # Enable multi-location detection
  enabled: true

  # Maximum locations to extract per website
  max_locations_per_site: 10

# ============================================================
# DEBUG SETTINGS (activated via --debug flag)
# ============================================================
debug:
  # Save screenshots of failed pages
  save_screenshots: true

  # Save HTML snapshots of failed pages
  save_html: true

  # Debug log file path
  log_file: ./debug/debug.log

  # Log all network requests
  log_network: true

# ============================================================
# EXTRACTION PRIORITIES (optional overrides)
# ============================================================
extractors:
  address:
    # Ordered list of strategies to try
    strategies:
      - schema_org
      - microdata
      - contact_page
      - footer
      - header
      - about_page

  hours:
    # Priority order for finding hours pages
    page_priority:
      - hours
      - contact
      - locations
      - about
```

---

## CLI Usage

### Installation

```bash
# Clone or create project
cd dealership-scraper

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Basic Usage

```bash
# Run with config file
python main.py --config config.yaml

# Run with direct URLs
python main.py --urls https://dealer1.com https://dealer2.com

# Run with URL file (one per line)
python main.py --url-file dealerships.txt
```

### Advanced Options

```bash
# Enable debug mode (screenshots, HTML snapshots, detailed logs)
python main.py --config config.yaml --debug

# Resume from checkpoint (after crash)
python main.py --config config.yaml --resume

# Write aggregate markdown to a custom location
python main.py --config config.yaml --output-file ./results/dealership-data.md

# Override default timezone (if needed)
python main.py --config config.yaml --timezone America/Denver

# Run in headed mode (see browser, for debugging)
python main.py --config config.yaml --headed
```

### Examples

```bash
# Scrape 3 dealerships with debug mode
python main.py --urls \
  https://dealer1.com \
  https://dealer2.com \
  https://dealer3.com \
  --debug

# Resume interrupted scraping session
python main.py --config config.yaml --resume

# Scrape with custom aggregate output file
python main.py \
  --url-file dealerships.txt \
  --output-file ./results/dealership-data-2025-11-12.md

# Resume and append to existing aggregate file
python main.py --config config.yaml --resume --output-file ./results/dealership-data.md
```

## CLI Input Modes (Pre-Run)

All URLs must be supplied before scraping starts. Supported options:

- `--url https://dealer.com`: scrape a single dealership (flag can be repeated).
- `--urls https://dealer1.com https://dealer2.com`: pass multiple URLs in one flag invocation (space-delimited).
- `--url-file ./dealers.txt`: read newline-delimited URLs from a text file.
- `--csv-file ./dealers.csv --csv-column url_column_name`: load URLs from a CSV column (defaults to `url`).
- These inputs can be combined; duplicates are de-duplicated while preserving first-seen order.
- The CLI validates that at least one URL is provided and aborts early (before browser launch) if not.

---

## Dependencies (requirements.txt)

```
# Core dependencies
playwright==1.48.0           # Headless browser automation
beautifulsoup4==4.12.3       # HTML parsing
pydantic==2.10.0             # Data models and validation
pyyaml==6.0.2                # Configuration file parsing
httpx==0.27.0                # HTTP client (Census API)

# CLI and logging
rich==13.9.0                 # Progress bars and console formatting
click==8.1.7                 # CLI framework (optional)

# Performance
lxml==5.3.0                  # Faster HTML parsing

# Optional (for enhanced features)
python-dotenv==1.0.0         # Environment variables
```

**Python Version**: 3.12+

---

## Output File

**Target path**: `output/dealership-data.md`

- A single markdown file is produced per run (unless `--resume` continues an interrupted run).
- Every dealership/location becomes a fenced ` ```markdown … ``` ` block appended in the same order as the incoming URL list.
- Block content is copied verbatim from `output_format.markdown_per_dealer` in `original_prompt.md`, keeping County immediately under the Google Maps address and preserving label wording.
- Evidence bullets, embedded credit provider notes, and timestamp rows must remain identical so downstream QA scripts still parse them.
- The aggregator resets the file at the start of each fresh run, then flushes when all dealers complete (or when a checkpoint snapshot is taken).

### Verbatim Template (from `original_prompt.md`)

````markdown
```markdown
[DEALERSHIP NAME]
[GOOGLE MAPS ADDRESS]
County: [COUNTY NAME]
Phone: (XXX) XXX-XXXX
Phone (no dashes): XXXXXXXXXX
Website: https://www.exampledealer.com/
Provider: Example Provider

Sales Hours
Monday: 8:00 AM – 6:00 PM
Tuesday: 8:00 AM – 6:00 PM
Wednesday: 8:00 AM – 6:00 PM
Thursday: 8:00 AM – 6:00 PM
Friday: 8:00 AM – 6:00 PM
Saturday: 9:00 AM – 5:00 PM
Sunday: Closed

Service Hours
Monday: 8:00 AM – 5:00 PM
Tuesday: 8:00 AM – 5:00 PM
Wednesday: 8:00 AM – 5:00 PM
Thursday: 8:00 AM – 5:00 PM
Friday: 8:00 AM – 5:00 PM
Saturday: Closed
Sunday: Closed

Parts Hours
Monday: 8:00 AM – 5:00 PM
Tuesday: 8:00 AM – 5:00 PM
Wednesday: 8:00 AM – 5:00 PM
Thursday: 8:00 AM – 5:00 PM
Friday: 8:00 AM – 5:00 PM
Saturday: Closed
Sunday: Closed

Schedule Service: https://www.exampledealer.com/service-appointment/
Credit App: https://www.exampledealer.com/finance/apply-for-financing/
  • Embedded provider (if any):
Facebook: https://www.facebook.com/exampledealer/
Facebook Page ID:

Evidence
- Google Maps (address): https://goo.gl/maps/example
- County verification: https://<census-or-gis-lookup-url>
- Dealer homepage (header phone): https://www.exampledealer.com/
- Dealer hours page (hours): https://www.exampledealer.com/hours/
- Service verified on: https://www.exampledealer.com/service-appointment/
- Credit app verified on: https://www.exampledealer.com/finance/apply-for-financing/
- Credit app embedded provider evidence: <detected vendor + iframe/src or link; see template comment>
- Facebook start: exampledealer.com → final FB: https://www.facebook.com/exampledealer/
- Provider verification: https://www.exampledealer.com/footer-or-terms/
- Captured: YYYY-MM-DD HH:mm (America/Chicago)
```
````

---

## Error Handling & Retry Strategy

### Smart Retry with Fallbacks

**Retry Handler** (`retry_handler.py`):

1. **Exponential Backoff**: 1s → 2s → 4s between retries
2. **Strategy Fallbacks**: Try alternative extraction methods
3. **Graceful Degradation**: Mark as "Unsure" after all attempts
4. **Evidence Tracking**: Record all URLs/methods attempted

### Error Scenarios

| Scenario | Handling |
|----------|----------|
| Page load timeout | Retry 3x, then mark "Unsure" |
| Network error | Exponential backoff, retry 3x |
| Element not found | Try alternative selectors, fallback strategies |
| Invalid data format | Validate, attempt normalization, mark "Unsure" if fails |
| Multiple locations found | Extract all separately |
| No address found | Try all 6 strategies, mark "Unsure" with evidence |
| Credit app page empty | Record URL, mark provider "Unsure", include iframe evidence |
| Robots.txt disallows | Log warning, respect (or override if config allows) |
| Census API down | Mark county "Unsure", continue scraping |

### "Unsure" Data Handling

When data cannot be reliably extracted:
- Field is marked: `"County: Unsure"`
- Evidence section includes:
  - All URLs attempted
  - Error messages
  - Alternative values found
  - Confidence scores

**Example**:
```markdown
County: Unsure

## Evidence
- County verification attempted:
  - Census Bureau: Connection timeout
  - Google Maps API: Not configured
  - Candidates found: "Kane County" or "DuPage County"
  - Requires manual verification
```

---

## Implementation Roadmap

### Phase 1: Foundation (Days 1-3, ~500 lines)
- ✅ Project structure setup
- ✅ Data models (Pydantic)
- ✅ Configuration loader
- ✅ Logger setup (normal + debug modes)
- ✅ Base extractor class
- ✅ Markdown block builder interface

### Phase 2: Browser Management (Days 4-6, ~600 lines)
- ✅ Browser pool manager
- ✅ Isolated browser contexts
- ✅ Navigation helpers
- ✅ Robots.txt parser and checker
- ✅ Page timeout handling

### Phase 3: Simple Extractors (Days 7-9, ~700 lines)
- ✅ Phone extractor
- ✅ URL discoverer (service scheduler)
- ✅ URL discoverer (credit app)
- ✅ URL discoverer (Facebook)
- ✅ Retry handler

### Phase 4: Complex Extractors (Days 10-13, ~1000 lines)
- ✅ Address extractor (6 strategies)
- ✅ Address validation
- ✅ Hours finder
- ✅ Hours parser
- ✅ Hours normalization

### Phase 5: Multi-Location Support (Days 14-15, ~250 lines)
- ✅ Location detector
- ✅ Multi-context handling
- ✅ Location URL extraction

### Phase 6: Provider Detection (Days 16-18, ~500 lines)
- ✅ Website provider detector
- ✅ Credit app provider detector (iframe/script)
- ✅ Fingerprint matching system
- ✅ YAML fingerprint files

### Phase 7: Services & Normalization (Days 19-20, ~650 lines)
- ✅ Census Bureau API client
- ✅ County lookup
- ✅ Phone normalizer
- ✅ Hours normalizer
- ✅ URL normalizer

### Phase 8: Output Generation (Days 21-22, ~650 lines)
- ✅ Markdown block builder (prompt-faithful)
- ✅ Single-file aggregator/writer
- ✅ Evidence formatter

### Phase 9: Checkpoint System (Day 23, ~150 lines)
- ✅ Checkpoint save/load
- ✅ Progress tracking
- ✅ Resume logic
- ✅ Failed URL retry

### Phase 10: Orchestrator & CLI (Days 24-25, ~350 lines)
- ✅ Main orchestrator
- ✅ Concurrency management (5 max)
- ✅ CLI argument parsing
- ✅ Progress display
- ✅ Completion summary

### Phase 11: Testing & Refinement (Days 26-30)
- ✅ Unit tests for extractors
- ✅ Integration tests
- ✅ Test with 10-20 real dealership sites
- ✅ Fix edge cases
- ✅ Performance optimization
- ✅ Documentation

**Total Estimated Time**: 25-30 development days

---

## Version Control & Automation

- Initialize a Git repository on day 0 (`git init`, `.gitignore`, initial commit capturing scaffolding).
- Configure the remote (e.g., `origin`) as soon as credentials are available and push the initial commit immediately after creation.
- Adopt small, frequent commits (per feature or fix) with descriptive messages; never allow large uncommitted changes to accumulate.
- Push after every meaningful commit so remote history mirrors local progress; use feature branches if multiple efforts run in parallel.
- Tag milestone releases (e.g., `v0.1`, `v1.0`) once QA passes to support rollbacks and traceability.

---

## Testing Strategy

### Unit Tests

Test each component independently:

```python
# Test address extractor
def test_address_extractor_schema_org():
    html = """
    <script type="application/ld+json">
    {"@type": "LocalBusiness", "address": {...}}
    </script>
    """
    result = AddressExtractor().extract_from_schema_org(html)
    assert result.street == "123 Main St"

# Test phone normalizer
def test_phone_normalizer():
    assert normalize_phone("217-555-1234") == "(217) 555-1234"
    assert normalize_phone("(217) 555-1234") == "(217) 555-1234"
    assert normalize_phone("2175551234") == "(217) 555-1234"

# Test hours parser
def test_hours_parser():
    text = "Mon-Fri: 9:00 AM - 6:00 PM"
    hours = HoursParser().parse(text)
    assert hours["monday"] == "9:00 AM – 6:00 PM"
```

### Integration Tests

Test full scraping workflow:

```python
# Test full dealership scrape
async def test_scrape_dealership():
    scraper = DealershipScraper(config)
    result = await scraper.scrape("https://testdealer.com")

    assert result.address is not None
    assert result.phone is not None
    assert len(result.hours) > 0
    assert result.provider is not None
```

### Real-World Testing

**Test Sites** (10-20 dealerships):
- Different website providers (Dealer.com, Dealer Inspire, etc.)
- Multi-location dealerships
- Various credit app providers
- Different hours formats
- Edge cases (closed days, split hours, seasonal hours)

**Validation**:
- Manual verification of extracted data
- Accuracy percentage by field
- Time per dealership
- Success rate

**Target Metrics**:
- Address accuracy: >95%
- Phone accuracy: >98%
- Hours accuracy: >90%
- Provider detection: >85%
- Average time per dealership: <2 minutes

---

## Edge Cases & Special Scenarios

### Multi-Location Dealerships

**Scenario**: Website has multiple physical locations

**Handling**:
1. Location detector scans for `/locations` page
2. Extracts all location URLs or identifiers
3. Creates separate context for each location (while still respecting the Google Maps “primary sales rooftop” rule)
4. Appends a distinct markdown block for every valid location to the single aggregate file

**Example**: "ABC Auto Group" with 3 qualifying rooftops → one `dealership-data.md` file containing 3 sequential code blocks.

### Address Not Found

**Scenario**: All 6 address strategies fail

**Handling**:
1. Mark address as "Unsure"
2. In Evidence section, list:
   - All strategies attempted
   - Any partial matches found
   - Suggested manual verification

### Credit App Page Empty

**Scenario**: Credit app URL exists but form doesn't load

**Handling**:
1. Record the Apply page URL
2. Mark embedded provider as "Unsure"
3. Include iframe/src attempts in Evidence
4. Note that manual verification is needed

### Conflicting Data

**Scenario**: Different hours found on different pages

**Handling**:
1. Use source priority (hours page > contact page > footer)
2. Record alternative values in Evidence
3. Note the conflict for manual review

### Seasonal/Temporary Hours

**Scenario**: Site shows "Holiday hours" or seasonal notices

**Handling**:
1. Prefer dated/temporary notices over standard hours
2. Note in Evidence: "Seasonal hours detected"
3. Include expiration date if present

### Phone Extensions

**Scenario**: Phone number includes extension (e.g., "x1234")

**Handling**:
1. Extract main number only (per requirements)
2. Ignore extensions
3. Note: Could be enhanced to extract dept-specific numbers if needed

### Toll-Free Numbers

**Scenario**: Dealership only shows 800/888/etc. number

**Handling**:
1. Extract and format normally
2. Note in Evidence: "Toll-free number"
3. Consider as valid sales contact

### No Facebook Presence

**Scenario**: No Facebook icon/link found

**Handling**:
1. Leave Facebook URL blank (don't guess)
2. Note in Evidence: "No Facebook link found"
3. Don't attempt external search

### Robots.txt Disallows Scraping

**Scenario**: `robots.txt` blocks User-agent

**Handling**:
1. Log warning message
2. Respect by default (skip dealership)
3. If `config.respect_robots_txt = false`, proceed with warning
4. Note in Evidence: "robots.txt warning"

### Census API Rate Limit

**Scenario**: Too many requests to Census API

**Handling**:
1. Implement exponential backoff
2. Queue county lookups
3. If persistent failure, mark "Unsure"
4. Continue scraping other data

---

## Security & Ethics

### Responsible Scraping

1. **Respect robots.txt** by default
2. **Rate limiting**: 2-5 second delays between pages
3. **Realistic User-Agent**: Identify as legitimate browser
4. **No DDoS**: Limit concurrent connections (max 5)
5. **Data privacy**: Only extract public business information
6. **No authentication bypass**: Only scrape public pages
7. **Terms of Service**: Users must ensure compliance

### Data Usage

**Acceptable Use**:
- Business research
- Lead generation (with proper authorization)
- Market analysis
- Competitive intelligence (public data only)

**Prohibited Use**:
- Unauthorized commercial resale
- Harassment or spam
- Violating website ToS
- Accessing private/protected data

### Legal Considerations

**Disclaimer**: Users are responsible for:
- Ensuring legal right to scrape target websites
- Compliance with website Terms of Service
- Compliance with local data protection laws (GDPR, CCPA, etc.)
- Obtaining necessary permissions for commercial use

---

## Future Enhancements (Out of Scope for v1.0)

### Potential Features

1. **Google Maps Integration**
   - Optional Google Places API for address verification
   - Extract reviews and ratings
   - Get accurate lat/lng coordinates

2. **Social Media Expansion**
   - Extract Twitter/X URLs
   - Extract Instagram URLs
   - Extract YouTube channel

3. **Advanced Analytics**
   - Track changes over time
   - Alert on data updates
   - Competitive analysis reports

4. **AI-Powered Extraction**
   - LLM-based fallback for ambiguous data
   - Natural language processing for hours
   - Image OCR for address in images

5. **Database Integration**
   - PostgreSQL/MySQL storage option
   - Change tracking and versioning
   - Query interface for data

6. **Web UI Dashboard**
   - Browser-based interface
   - Real-time progress monitoring
   - Visual data validation

7. **Scheduling**
   - Cron job integration
   - Periodic re-scraping
   - Email notifications

8. **Export Formats**
   - Excel (XLSX)
   - Google Sheets integration
   - CRM import formats

9. **Enhanced Provider Detection**
   - More website platforms
   - More credit app providers
   - Chat widget providers
   - CRM detection

10. **Quality Scoring**
    - Confidence metrics per field
    - Data completeness score
    - Recommendation engine

---

## Appendix

### Provider Fingerprints (YAML)

**File**: `data/provider_fingerprints.yaml`

```yaml
dealer_com_cox:
  display_name: "Dealer.com (Cox Automotive)"
  footer_text_contains:
    - "Dealer.com"
    - "Cox Automotive"
  domain_clues:
    - "dealer.com"
  structured_data_clues:
    - "Dealer.com"

dealer_inspire:
  display_name: "Dealer Inspire"
  footer_text_contains:
    - "Dealer Inspire"
    - "Cars Commerce"
  domain_clues:
    - "dealerinspire.com"
    - "carscommerce.inc"
  indicative_hosts:
    - "secure.dealerinspire.com"

dealer_on:
  display_name: "DealerOn"
  footer_text_contains:
    - "DealerOn"
  domain_clues:
    - "dealeron.com"

dealer_eprocess:
  display_name: "Dealer eProcess"
  footer_text_contains:
    - "Dealer eProcess"
    - "DEP"
  domain_clues:
    - "dealereprocess.com"

# ... (additional providers)
```

### Credit Provider Fingerprints (YAML)

**File**: `data/credit_fingerprints.yaml`

```yaml
seven_hundred_credit:
  display_name: "700Credit"
  domains:
    - secure.700credit.com
    - 700credit.com
    - www.700dealer.com
    - 700dealer.com
  path_clues:
    - /creditapp
    - /apply
    - /prequal
    - /quickapplication
    - /QuickQualify
    - /quickqualify

routeone:
  display_name: "RouteOne"
  domains:
    - routeone.net
    - apps.routeone.net
    - www.routeone.net
    - digital-retail-ui.routeone.net
  path_clues:
    - /digital-retail-ui
    - /application
    - /apply
    - /creditapp

dealertrack:
  display_name: "Dealertrack"
  domains:
    - dealertrack.com
    - suite.dtdrs.dealertrack.com
    - dtprod.dealertrack.com
  path_clues:
    - /creditapp
    - /apply
    - /financing
    - /suite
    - /accountId=
    - /dealerId=

# ... (additional credit providers)
```

### Regex Patterns

**File**: `scraper/utils/patterns.py`

```python
import re

# US Address patterns
ADDRESS_STREET_PATTERN = re.compile(
    r'\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
    r'(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Court|Ct)',
    re.IGNORECASE
)

# Phone number patterns
PHONE_PATTERN = re.compile(r'\D*1?\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*')

# Hours patterns
HOURS_RANGE_PATTERN = re.compile(
    r'(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)\s*-\s*(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)'
)

# Day patterns
DAY_PATTERN = re.compile(
    r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)',
    re.IGNORECASE
)

# State abbreviation
STATE_PATTERN = re.compile(r'\b[A-Z]{2}\b')

# ZIP code
ZIP_PATTERN = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# URL patterns
URL_PATTERN = re.compile(r'https?://[^\s<>"]+')
```

---

## Conclusion

This dealership web scraper is designed as a modular, maintainable, and extensible system following the lego-methodology. With a clear separation of concerns, plug-and-play components, and comprehensive error handling, it can reliably extract detailed business data from dealership websites.

**Key Strengths**:
- ✅ Modular architecture (no file >500 lines)
- ✅ Extremely reliable address extraction (6 fallback strategies)
- ✅ Multi-location support
- ✅ Smart retry with fallbacks
- ✅ Crash recovery via checkpoints
- ✅ Respectful scraping (robots.txt, delays)
- ✅ Debug mode for troubleshooting
- ✅ Prompt-faithful single markdown output file
- ✅ Comprehensive evidence tracking

**Total Project Size**: ~30+ files, ~4000-5000 lines of code

**Development Time**: 25-30 days

---

**Version**: 1.0
**Last Updated**: 2025-11-12
**Author**: Implementation plan for AI-assisted development
