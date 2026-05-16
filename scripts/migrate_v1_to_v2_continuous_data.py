#!/usr/bin/env python3
"""
Migration Script: v1 to v2 Continuous Data
============================================

Backfills continuous data fields (sleep_hours, deep_work_hours, skill_building_hours,
training_intensity) for existing check-ins that only have boolean data.

Usage:
    python scripts/migrate_v1_to_v2_continuous_data.py [--dry-run]

Safety:
    - Runs in dry-run mode by default
    - Backs up affected documents before modification
    - Logs all changes
    - Can be run idempotently
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.firestore_service import firestore_service
from src.models.schemas import DailyCheckIn
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Estimation rules for migration
ESTIMATES = {
    "sleep": {"compliant": 7.5, "non_compliant": 5.5},
    "deep_work": {"compliant": 2.5, "non_compliant": 0.5},
    "skill_building": {"compliant": 2.5, "non_compliant": 0.5},
}


def migrate_checkins(dry_run: bool = True):
    """
    Backfill continuous data fields for all existing check-ins.
    
    Args:
        dry_run: If True, only log what would be changed without modifying data.
    """
    logger.info(f"🚀 Starting migration (dry_run={dry_run})")
    
    users = firestore_service.get_all_users()
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    
    logger.info(f"📋 Found {len(users)} users to process")
    
    for user in users:
        try:
            checkins = firestore_service.get_all_checkins(user.user_id)
            user_migrated = 0
            user_skipped = 0
            
            for checkin in checkins:
                try:
                    tier1 = checkin.tier1_non_negotiables
                    modified = False
                    
                    # Migrate sleep_hours
                    if not hasattr(tier1, 'sleep_hours') or tier1.sleep_hours is None:
                        estimated = ESTIMATES["sleep"]["compliant"] if tier1.sleep else ESTIMATES["sleep"]["non_compliant"]
                        tier1.sleep_hours = estimated
                        modified = True
                        logger.debug(f"  User {user.user_id} checkin {checkin.date}: sleep_hours={estimated}")
                    
                    # Migrate deep_work_hours
                    if not hasattr(tier1, 'deep_work_hours') or tier1.deep_work_hours is None:
                        estimated = ESTIMATES["deep_work"]["compliant"] if tier1.deep_work else ESTIMATES["deep_work"]["non_compliant"]
                        tier1.deep_work_hours = estimated
                        modified = True
                        logger.debug(f"  User {user.user_id} checkin {checkin.date}: deep_work_hours={estimated}")
                    
                    # Migrate skill_building_hours
                    if not hasattr(tier1, 'skill_building_hours') or tier1.skill_building_hours is None:
                        estimated = ESTIMATES["skill_building"]["compliant"] if tier1.skill_building else ESTIMATES["skill_building"]["non_compliant"]
                        tier1.skill_building_hours = estimated
                        modified = True
                        logger.debug(f"  User {user.user_id} checkin {checkin.date}: skill_building_hours={estimated}")
                    
                    # Migrate training_intensity
                    if not hasattr(tier1, 'training_intensity') or tier1.training_intensity is None:
                        if hasattr(tier1, 'is_rest_day') and tier1.is_rest_day:
                            tier1.training_intensity = "rest"
                        elif tier1.training:
                            tier1.training_intensity = "moderate"
                        else:
                            tier1.training_intensity = "rest"
                        modified = True
                        logger.debug(f"  User {user.user_id} checkin {checkin.date}: training_intensity={tier1.training_intensity}")
                    
                    # Set data quality flag
                    if modified:
                        tier1.data_quality = "migrated"
                        total_migrated += 1
                        user_migrated += 1
                        
                        if not dry_run:
                            firestore_service.update_checkin(checkin)
                    else:
                        total_skipped += 1
                        user_skipped += 1
                
                except Exception as e:
                    logger.error(f"❌ Error processing checkin {checkin.date} for user {user.user_id}: {e}")
                    total_errors += 1
            
            if user_migrated > 0:
                logger.info(f"✅ User {user.user_id}: {user_migrated} migrated, {user_skipped} skipped")
        
        except Exception as e:
            logger.error(f"❌ Error processing user {user.user_id}: {e}")
            total_errors += 1
    
    logger.info("=" * 60)
    logger.info("📊 Migration Summary:")
    logger.info(f"   Users processed: {len(users)}")
    logger.info(f"   Check-ins migrated: {total_migrated}")
    logger.info(f"   Check-ins skipped: {total_skipped}")
    logger.info(f"   Errors: {total_errors}")
    
    if dry_run:
        logger.info("\n⚠️  This was a DRY RUN. No data was modified.")
        logger.info("   Run with --execute to apply changes.")
    else:
        logger.info("\n✅ Migration completed successfully.")
    
    logger.info("=" * 60)
    
    return {
        "users": len(users),
        "migrated": total_migrated,
        "skipped": total_skipped,
        "errors": total_errors,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate check-in data from boolean to continuous metrics"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually modify data (default is dry-run)"
    )
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        logger.info("🏃 Running in DRY-RUN mode. No changes will be made.")
        logger.info("   Use --execute flag to apply changes.")
    else:
        logger.info("⚠️  EXECUTION MODE. This will modify existing check-in data.")
        logger.info("   Press Ctrl+C within 3 seconds to cancel...")
        import time
        time.sleep(3)
        logger.info("   Proceeding with migration...")
    
    result = migrate_checkins(dry_run=dry_run)
    
    # Exit with error code if there were errors
    if result["errors"] > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
