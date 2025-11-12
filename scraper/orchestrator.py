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
    Process a single dealership with full extraction workflow.

    Args:
        url: Dealership URL
        browser_manager: Browser manager
        config: Scraper configuration
        county_service: County lookup service

    Returns:
        DealerData or None if processing fails
    """
    logger = get_logger()

    # Import extractors
    from .extractors import (
        PhoneExtractor,
        AddressExtractor,
        HoursExtractor,
        URLDiscoverer,
        ProviderDetector,
        CreditAppProviderDetector
    )

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
        logger.info(f"Processing: {dealer_name}")

        # Initialize evidence
        evidence = Evidence(
            dealer_homepage_phone=url,
            captured_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M") + f" ({config.timezone})"
        )

        # Extract phone number
        logger.debug("Extracting phone number...")
        phone_extractor = PhoneExtractor()
        phone_result = await phone_extractor.extract(dealer_context, page)
        phone = phone_result.data if phone_result.success else None

        if phone_result.evidence:
            evidence.dealer_homepage_phone = phone_result.evidence

        # Extract address
        logger.debug("Extracting address...")
        address_extractor = AddressExtractor()
        address_result = await address_extractor.extract(dealer_context, page)
        address = address_result.data if address_result.success else None

        # Lookup county if address found
        county = None
        if address and county_service:
            logger.debug("Looking up county...")
            county = await county_service.lookup_county(
                street=address.street,
                city=address.city,
                state=address.state,
                zip_code=address.zip_code
            )
            if county and county.verification_url:
                evidence.county_verification = county.verification_url

        # Extract hours
        logger.debug("Extracting hours...")
        hours_extractor = HoursExtractor()
        hours_result = await hours_extractor.extract(dealer_context)
        hours = hours_result.data if hours_result.success else None

        if hours_result.evidence:
            evidence.dealer_hours_page = hours_result.evidence

        # Discover URLs
        logger.debug("Discovering URLs...")
        url_discoverer = URLDiscoverer()
        url_result = await url_discoverer.extract(dealer_context, page)
        urls = url_result.data if url_result.success else None

        if urls:
            if urls.service_scheduler:
                evidence.service_verified_on = urls.service_scheduler
            if urls.credit_app:
                evidence.credit_app_verified_on = urls.credit_app
            if urls.facebook:
                evidence.facebook_final = urls.facebook
                if urls.facebook_source:
                    evidence.facebook_start = urls.facebook_source

        # Detect website provider
        logger.debug("Detecting website provider...")
        provider_detector = ProviderDetector()
        provider_result = await provider_detector.extract(dealer_context, page)
        website_provider = provider_result.data if provider_result.success else None

        if provider_result.evidence:
            evidence.provider_verification = provider_result.evidence

        # Detect credit app provider
        credit_app_provider = None
        if urls and urls.credit_app:
            logger.debug("Detecting credit app provider...")
            credit_detector = CreditAppProviderDetector()
            credit_result = await credit_detector.extract(dealer_context, urls.credit_app)
            credit_app_provider = credit_result.data if credit_result.success else None

            if credit_result.evidence:
                evidence.credit_app_embedded_evidence = credit_result.evidence

        # Build dealer data
        dealer_data = DealerData(
            name=dealer_name,
            website=url,
            address=address,
            county=county,
            phone=phone,
            hours=hours,
            urls=urls,
            website_provider=website_provider,
            credit_app_provider=credit_app_provider,
            evidence=evidence,
            processed_at=datetime.now()
        )

        logger.success(f"Completed extraction: {dealer_name}")

        return dealer_data

    except Exception as e:
        logger.error(f"Error in process_dealership: {e}", exc_info=True)
        return None

    finally:
        # Close browser context
        await browser_manager.close_context(context_handle)
