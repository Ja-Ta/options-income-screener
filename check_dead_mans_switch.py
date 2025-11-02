#!/usr/bin/env python3
"""
Dead Man's Switch - Check if pipeline is running regularly.

This script should be run daily via cron to ensure the pipeline
hasn't stopped running. If no pipeline run is detected within
the configured threshold, an alert is sent.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_app'))

from dotenv import load_dotenv
load_dotenv()

from src.services.monitoring_service import MonitoringService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run dead man's switch check."""
    logger.info("="*60)
    logger.info("DEAD MAN'S SWITCH CHECK")
    logger.info("="*60)

    monitoring = MonitoringService()

    # Check if pipeline has run recently
    monitoring.check_dead_mans_switch()

    # Get health status
    health = monitoring.get_health_status()

    logger.info(f"Health Status: {health['status']}")
    logger.info(f"Health Score: {health['health_score']}")

    if health['last_run']:
        logger.info(f"Last Run: {health['last_run']['started_at']}")
        logger.info(f"Last Run Status: {health['last_run']['status']}")
    else:
        logger.warning("No pipeline runs found!")

    logger.info("="*60)
    logger.info("DEAD MAN'S SWITCH CHECK COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    main()
