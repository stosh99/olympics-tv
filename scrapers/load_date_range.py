#!/usr/bin/env python3
"""
Load Olympics event data for a date range
"""

from olympics_scraper import OlympicsScraper
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_date_range(start_date, end_date):
    """Load Olympics data for a date range"""
    scraper = OlympicsScraper()

    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    total_processed = 0
    total_inserted = 0
    failed_dates = []

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        try:
            logger.info(f"Scraping {date_str}...")
            result = scraper.run(date_str)
            total_processed += result.get('processed', 0)
            total_inserted += result.get('inserted', 0)
            logger.info(f"  ✓ {result['processed']} processed, {result['inserted']} inserted")
        except Exception as e:
            logger.error(f"  ✗ Failed to scrape {date_str}: {e}")
            failed_dates.append(date_str)

        current += timedelta(days=1)

    logger.info(f"\n{'='*60}")
    logger.info(f"Date range complete:")
    logger.info(f"  Total processed: {total_processed}")
    logger.info(f"  Total inserted: {total_inserted}")
    if failed_dates:
        logger.warning(f"  Failed dates: {', '.join(failed_dates)}")
    logger.info(f"{'='*60}")

    return {
        'total_processed': total_processed,
        'total_inserted': total_inserted,
        'failed_dates': failed_dates
    }

if __name__ == '__main__':
    # Load Feb 3-5 and Feb 7-22
    logger.info("Loading Feb 3-5...")
    result1 = load_date_range('2026-02-03', '2026-02-05')

    logger.info("\nLoading Feb 7-22...")
    result2 = load_date_range('2026-02-07', '2026-02-22')

    # Summary
    grand_total_processed = result1['total_processed'] + result2['total_processed']
    grand_total_inserted = result1['total_inserted'] + result2['total_inserted']
    all_failed = result1['failed_dates'] + result2['failed_dates']

    logger.info(f"\n{'='*60}")
    logger.info(f"GRAND TOTAL:")
    logger.info(f"  Total processed: {grand_total_processed}")
    logger.info(f"  Total inserted: {grand_total_inserted}")
    if all_failed:
        logger.warning(f"  Failed dates: {', '.join(all_failed)}")
    logger.info(f"{'='*60}")
