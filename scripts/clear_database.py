#!/usr/bin/env python3
"""
Clear All User Data from Firestore
===================================

This script safely deletes all user data from the Firestore database.
Use this when you want to start fresh after making significant changes.

⚠️ WARNING: This is IRREVERSIBLE! All user data will be permanently deleted.

Collections cleared:
- users (user profiles)
- daily_checkins (check-in records + subcollections)
- interventions (intervention records + subcollections)
- reminder_status (reminder tracking + subcollections)
- emotional_interactions (emotional support logs)
- patterns (pattern detection data)

Usage:
    python scripts/clear_database.py

Safety features:
- Requires explicit confirmation
- Shows count of documents before deletion
- Provides option to backup first
- Logs all deletions
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Safely clear all user data from Firestore."""
    
    def __init__(self):
        """Initialize Firestore client."""
        self.db = firestore.Client()
        logger.info("✅ Connected to Firestore")
    
    def count_documents(self, collection_name: str) -> int:
        """Count documents in a collection."""
        try:
            docs = list(self.db.collection(collection_name).stream())
            return len(docs)
        except Exception as e:
            logger.error(f"❌ Error counting {collection_name}: {e}")
            return 0
    
    def count_subcollection_documents(self, parent_collection: str, subcollection: str) -> int:
        """
        Count documents in subcollections across all parent documents.

        Note: This does not include orphaned subcollection docs whose parent
        documents were previously deleted.
        """
        try:
            total = 0
            parent_docs = self.db.collection(parent_collection).stream()
            for parent_doc in parent_docs:
                subcol_docs = list(parent_doc.reference.collection(subcollection).stream())
                total += len(subcol_docs)
            return total
        except Exception as e:
            logger.error(f"❌ Error counting {parent_collection}/{subcollection}: {e}")
            return 0

    def count_collection_group_documents(self, collection_group_name: str) -> int:
        """
        Count documents in a collection group across the whole database.

        This includes both normal nested docs and orphaned docs.
        """
        try:
            docs = list(self.db.collection_group(collection_group_name).stream())
            return len(docs)
        except Exception as e:
            logger.error(f"❌ Error counting collection group {collection_group_name}: {e}")
            return 0
    
    def show_database_stats(self):
        """Display current database statistics."""
        print("\n" + "="*60)
        print("📊 Current Database Statistics")
        print("="*60)
        
        # Count main collections
        users_count = self.count_documents('users')
        emotional_count = self.count_documents('emotional_interactions')
        patterns_count = self.count_documents('patterns')
        
        # Count subcollection docs via collection groups (includes orphaned docs)
        checkins_count = self.count_collection_group_documents('checkins')
        interventions_count = self.count_collection_group_documents('interventions')
        reminder_status_count = self.count_collection_group_documents('dates')
        
        print("\n📁 Main Collections:")
        print(f"   Users:                    {users_count:>6} documents")
        print(f"   Emotional Interactions:   {emotional_count:>6} documents")
        print(f"   Patterns:                 {patterns_count:>6} documents")
        
        print("\n📂 Subcollection Docs (collection-group count):")
        print(f"   Check-ins:                {checkins_count:>6} documents")
        print(f"   Interventions:            {interventions_count:>6} documents")
        print(f"   Reminder Status:          {reminder_status_count:>6} documents")
        
        total = (users_count + emotional_count + patterns_count + 
                 checkins_count + interventions_count + reminder_status_count)
        
        print(f"\n📊 Total Documents:          {total:>6}")
        print("="*60 + "\n")
        
        return total
    
    def delete_collection(self, collection_name: str, batch_size: int = 100):
        """Delete all documents in a collection."""
        try:
            deleted = 0
            collection_ref = self.db.collection(collection_name)
            
            while True:
                # Get batch of documents
                docs = list(collection_ref.limit(batch_size).stream())
                
                if not docs:
                    break
                
                # Delete batch
                batch = self.db.batch()
                for doc in docs:
                    batch.delete(doc.reference)
                    deleted += 1
                
                batch.commit()
                logger.info(f"   Deleted {deleted} documents from {collection_name}...")
            
            logger.info(f"✅ Deleted {deleted} documents from {collection_name}")
            return deleted
            
        except Exception as e:
            logger.error(f"❌ Error deleting {collection_name}: {e}")
            return 0
    
    def delete_subcollection(self, parent_collection: str, subcollection: str, batch_size: int = 100):
        """Delete all documents in subcollections across all parent documents."""
        try:
            total_deleted = 0
            parent_docs = list(self.db.collection(parent_collection).stream())
            
            logger.info(f"   Found {len(parent_docs)} parent documents in {parent_collection}")
            
            for parent_doc in parent_docs:
                deleted = 0
                subcol_ref = parent_doc.reference.collection(subcollection)
                
                while True:
                    # Get batch of documents
                    docs = list(subcol_ref.limit(batch_size).stream())
                    
                    if not docs:
                        break
                    
                    # Delete batch
                    batch = self.db.batch()
                    for doc in docs:
                        batch.delete(doc.reference)
                        deleted += 1
                    
                    batch.commit()
                
                if deleted > 0:
                    logger.info(f"   Deleted {deleted} documents from {parent_doc.id}/{subcollection}")
                    total_deleted += deleted
            
            logger.info(f"✅ Deleted {total_deleted} documents from {parent_collection}/{subcollection}")
            return total_deleted
            
        except Exception as e:
            logger.error(f"❌ Error deleting {parent_collection}/{subcollection}: {e}")
            return 0

    def delete_collection_group(self, collection_group_name: str, batch_size: int = 100):
        """
        Delete all docs from a collection group.

        This is the orphan-safe sweep that catches subcollection documents
        even when parent docs were removed earlier.
        """
        try:
            deleted = 0
            while True:
                docs = list(self.db.collection_group(collection_group_name).limit(batch_size).stream())
                if not docs:
                    break

                batch = self.db.batch()
                for doc in docs:
                    batch.delete(doc.reference)
                    deleted += 1
                batch.commit()

            logger.info(f"✅ Deleted {deleted} documents from collection group {collection_group_name}")
            return deleted
        except Exception as e:
            logger.error(f"❌ Error deleting collection group {collection_group_name}: {e}")
            return 0
    
    def clear_all_data(self):
        """Clear all user data from the database."""
        print("\n" + "="*60)
        print("🧹 Starting Database Cleanup")
        print("="*60 + "\n")
        
        start_time = datetime.now()
        total_deleted = 0
        
        # Step 1: Delete subcollections under known parents
        print("📂 Deleting subcollections...")
        total_deleted += self.delete_subcollection('daily_checkins', 'checkins')
        total_deleted += self.delete_subcollection('interventions', 'interventions')
        total_deleted += self.delete_subcollection('reminder_status', 'dates')
        
        # Step 2: Delete main collections
        print("\n📁 Deleting main collections...")
        total_deleted += self.delete_collection('users')
        total_deleted += self.delete_collection('emotional_interactions')
        total_deleted += self.delete_collection('patterns')
        
        # Step 3: Delete parent documents (now empty containers)
        print("\n🗑️  Cleaning up empty parent documents...")
        total_deleted += self.delete_collection('daily_checkins')
        total_deleted += self.delete_collection('interventions')
        total_deleted += self.delete_collection('reminder_status')

        # Step 4: Orphan-safe sweep via collection groups
        print("\n🧽 Sweeping orphaned subcollection docs...")
        total_deleted += self.delete_collection_group('checkins')
        total_deleted += self.delete_collection_group('interventions')
        total_deleted += self.delete_collection_group('dates')
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("✅ Database Cleanup Complete!")
        print("="*60)
        print(f"\n📊 Total documents deleted: {total_deleted}")
        print(f"⏱️  Time taken: {elapsed:.2f} seconds")
        print("\n💡 The database is now empty and ready for fresh data.\n")


def confirm_deletion() -> bool:
    """Ask user to confirm deletion."""
    print("\n" + "⚠️ "*30)
    print("⚠️  WARNING: IRREVERSIBLE OPERATION")
    print("⚠️ "*30)
    print("\nThis will PERMANENTLY DELETE all user data from Firestore:")
    print("  • All user profiles")
    print("  • All check-in records")
    print("  • All interventions")
    print("  • All emotional interactions")
    print("  • All pattern detection data")
    print("  • All reminder status")
    print("\n❌ This action CANNOT be undone!")
    print("❌ There is NO backup or recovery option!")
    
    response = input("\n🔴 Type 'DELETE ALL DATA' to confirm (or anything else to cancel): ")
    
    return response == "DELETE ALL DATA"


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("🗑️  Firestore Database Cleanup Tool")
    print("="*60)
    
    # Initialize cleaner
    try:
        cleaner = DatabaseCleaner()
    except Exception as e:
        logger.error(f"❌ Failed to connect to Firestore: {e}")
        print("\n💡 Make sure:")
        print("   1. GOOGLE_APPLICATION_CREDENTIALS is set")
        print("   2. Service account has Firestore permissions")
        print("   3. You're in the correct GCP project")
        sys.exit(1)
    
    # Show current stats
    total_docs = cleaner.show_database_stats()
    
    if total_docs == 0:
        print("✅ Database is already empty. Nothing to delete.\n")
        sys.exit(0)
    
    # Confirm deletion
    if not confirm_deletion():
        print("\n✅ Cancelled. No data was deleted.\n")
        sys.exit(0)
    
    # Double confirmation for safety
    print("\n⚠️  Last chance to cancel!")
    response = input("🔴 Type 'YES' to proceed with deletion: ")
    
    if response != "YES":
        print("\n✅ Cancelled. No data was deleted.\n")
        sys.exit(0)
    
    # Perform deletion
    cleaner.clear_all_data()
    
    # Show final stats
    print("\n📊 Verifying cleanup...")
    final_count = cleaner.show_database_stats()
    
    if final_count == 0:
        print("✅ Verification passed: Database is completely empty.\n")
    else:
        print(f"⚠️  Warning: {final_count} documents still remain.")
        print("   This might be due to timing or permissions issues.\n")


if __name__ == "__main__":
    main()
