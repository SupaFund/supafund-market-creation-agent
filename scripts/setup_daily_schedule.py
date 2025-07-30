#!/usr/bin/env python3
"""
Script to set up daily scheduling for market resolution system.
This can be run as a cron job or scheduled task.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.daily_scheduler import run_daily_resolution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'logs', 'daily_schedule.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for scheduled execution"""
    logger.info("Starting scheduled daily market resolution cycle")
    
    try:
        # Run the daily resolution cycle
        summary = await run_daily_resolution()
        
        logger.info(f"Daily resolution cycle completed successfully")
        logger.info(f"Summary: {summary}")
        
        # Exit with success code
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Daily resolution cycle failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Run the async main function
    asyncio.run(main())