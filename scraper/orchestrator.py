"""
Main orchestrator for the dealership scraper.
Coordinates browser, extractors, and output generation.
"""

import asyncio
import time
from datetime import datetime
from typing import List

from .models import ScraperConfig, DealerData, Evidence
from .browser import BrowserManager, DealerContext, RobotsTxtChecker
from .checkpoint import CheckpointManager
from .output import MarkdownWriter
from .services import CensusBureauClient, CountyLookupService
from .utils import init_logger, get_logger


async def run_scraper(config: ScraperConfig, resume: bool = False):
    """
    Main entry point for running the scraper.

    Args:
        config: Scraper configuration
        resume: Resume from last checkpoint if available
    """
    # Initialize logger
    logger = init_logger(
        debug_mode=config.debug_mode,
        debug_log_file=config.debug_log_file if config.debug_mode else None
    )

    logger.print_header("Dealership Data + URL Discovery Automation")

    start_time = time.time()

    # Initialize checkpoint manager
    checkpoint = CheckpointManager()

    # Try to resume if requested
    if resume:
        latest_session = checkpoint.find_latest_checkpoint()
        if latest_session:
            logger.info(f"Resuming from checkpoint: {latest_session}")
            if checkpoint.load(latest_session):
                # Get pending URLs
                urls_to_process = checkpoint.get_pending_urls()
                logger.info(f"Resuming with {len(urls_to_process)} pending URL(s)")
            else:
                logger.warning("Failed to load checkpoint, starting fresh")
                urls_to_process = config.urls
        else:
            logger.warning("No checkpoint found, starting fresh")
            urls_to_process = config.urls
    else:
        # Fresh run
        urls_to_process = config.urls
        checkpoint.add_pending(urls_to_process)

    if not urls_to_process:
        logger.warning("No URLs to process")
        return

    # Initialize components
    logger.info("Initializing components...")

    robots_checker = RobotsTxtChecker()
    census_client = CensusBureauClient(config.census_api_url) if config.census_enabled else None
    county_service = CountyLookupService(census_client) if census_client else None

    # Initialize output writer
    writer = MarkdownWriter(
        output_file=config.output_file,
        timezone=config.timezone
    )

    # Clear output file if not resuming
    if not resume:
        writer.clear()

    # Process dealerships
    logger.print_section("Processing Dealerships")

    successful = 0
    failed = 0

    async with BrowserManager(config) as browser_manager:
        # Process dealerships sequentially (for now)
        # TODO: Implement concurrent processing with semaphore
        for url in urls_to_process:
            logger.info(f"\nProcessing: {url}")

            # Check robots.txt
            is_allowed, crawl_delay = await robots_checker.is_allowed(url, config.respect_robots_txt)

            if not is_allowed:
                logger.warning(f"robots.txt disallows scraping {url}")
                if config.respect_robots_txt:
                    checkpoint.mark_failed(url, "Disallowed by robots.txt")
                    failed += 1
                    continue

            # Apply crawl delay if specified
            if crawl_delay and crawl_delay > config.delay_between_pages_sec:
                logger.info(f"Applying robots.txt crawl-delay of {crawl_delay}s")
                await asyncio.sleep(crawl_delay)

            try:
                # Process dealership
                dealer_data = await process_dealership(
                    url=url,
                    browser_manager=browser_manager,
                    config=config,
                    county_service=county_service
                )

                if dealer_data:
                    # Write to output
                    writer.append_dealer(dealer_data)

                    # Mark as completed
                    checkpoint.mark_completed(url)
                    successful += 1

                    logger.success(f"Completed: {dealer_data.name or url}")
                else:
                    checkpoint.mark_failed(url, "Failed to extract data")
                    failed += 1
                    logger.error(f"Failed to extract data from {url}")

            except Exception as e:
                logger.error(f"Error processing {url}: {e}", exc_info=True)
                checkpoint.mark_failed(url, str(e))
                failed += 1

    # Print summary
    duration = time.time() - start_time
    logger.print_summary(
        total=successful + failed,
        successful=successful,
        failed=failed,
        duration=duration
    )

    # Print checkpoint stats
    checkpoint.print_summary()

    # Cleanup old checkpoints
    checkpoint.cleanup_old_checkpoints(keep_last_n=10)

    logger.info(f"\nOutput written to: {config.output_file}")


async def process_dealership(
    url: str,
    browser_manager: BrowserManager,
    config: ScraperConfig,
    county_service: CountyLookupService
) -> DealerData:
    """
    Process a single dealership.

    This is a stub implementation that will be expanded with full extractors.

    Args:
        url: Dealership URL
        browser_manager: Browser manager
        config: Scraper configuration
        county_service: County lookup service

    Returns:
        DealerData or None if processing fails
    """
    logger = get_logger()

    # Create browser context
    context_handle = await browser_manager.create_context()

    try:
        dealer_context = DealerContext(context_handle, url, config)

        # Navigate to homepage
        page = await dealer_context.navigate(url)

        if not page:
            logger.warning(f"Failed to load homepage: {url}")
            return None

        # Extract dealer name from page title
        dealer_name = await page.title()

        logger.debug(f"Dealer name: {dealer_name}")

        # Create dealer data with stub values
        # TODO: Implement full extractors
        dealer_data = DealerData(
            name=dealer_name,
            website=url,
            processed_at=datetime.now(),
            evidence=Evidence(
                dealer_homepage_phone=url,
                captured_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M") + f" ({config.timezone})"
            )
        )

        logger.info("✓ Basic data extracted (using stub implementation)")

        return dealer_data

    except Exception as e:
        logger.error(f"Error in process_dealership: {e}", exc_info=True)
        return None

    finally:
        # Close browser context
        await browser_manager.close_context(context_handle)
