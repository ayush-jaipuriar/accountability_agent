#!/usr/bin/env python3
"""
Backup Firestore Database
==========================

Creates a JSON backup of all user data before clearing the database.

Usage:
    python scripts/backup_database.py

Output:
    backups/firestore_backup_YYYY-MM-DD_HH-MM-SS.json
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Create JSON backup of Firestore data."""
    
    def __init__(self):
        self.db = firestore.Client()
        logger.info("✅ Connected to Firestore")
    
    def backup_collection(self, collection_name: str) -> list:
        """Backup a collection to list of dicts."""
        docs = []
        for doc in self.db.collection(collection_name).stream():
            docs.append({
                'id': doc.id,
                'data': doc.to_dict()
            })
        return docs
    
    def backup_subcollection(self, parent_collection: str, subcollection: str) -> dict:
        """Backup subcollections across all parent documents."""
        backup = {}
        parent_docs = self.db.collection(parent_collection).stream()
        
        for parent_doc in parent_docs:
            subcol_docs = []
            for doc in parent_doc.reference.collection(subcollection).stream():
                subcol_docs.append({
                    'id': doc.id,
                    'data': doc.to_dict()
                })
            if subcol_docs:
                backup[parent_doc.id] = subcol_docs
        
        return backup
    
    def create_backup(self) -> dict:
        """Create complete backup of all collections."""
        print("\n📦 Creating database backup...")
        
        backup = {
            'timestamp': datetime.now().isoformat(),
            'collections': {}
        }
        
        # Backup main collections
        print("   Backing up users...")
        backup['collections']['users'] = self.backup_collection('users')
        
        print("   Backing up emotional_interactions...")
        backup['collections']['emotional_interactions'] = self.backup_collection('emotional_interactions')
        
        print("   Backing up patterns...")
        backup['collections']['patterns'] = self.backup_collection('patterns')
        
        # Backup subcollections
        print("   Backing up check-ins...")
        backup['collections']['daily_checkins'] = self.backup_subcollection('daily_checkins', 'checkins')
        
        print("   Backing up interventions...")
        backup['collections']['interventions'] = self.backup_subcollection('interventions', 'interventions')
        
        print("   Backing up reminder_status...")
        backup['collections']['reminder_status'] = self.backup_subcollection('reminder_status', 'dates')
        
        return backup
    
    def save_backup(self, backup: dict) -> str:
        """Save backup to JSON file."""
        # Create backups directory
        backup_dir = project_root / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = backup_dir / f'firestore_backup_{timestamp}.json'
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(backup, f, indent=2, default=str)
        
        return str(filename)


def main():
    print("\n" + "="*60)
    print("📦 Firestore Database Backup Tool")
    print("="*60 + "\n")
    
    try:
        backup_tool = DatabaseBackup()
        backup = backup_tool.create_backup()
        filename = backup_tool.save_backup(backup)
        
        print("\n✅ Backup complete!")
        print(f"📁 Saved to: {filename}")
        
        # Show stats
        total_docs = sum(
            len(v) if isinstance(v, list) else sum(len(subcol) for subcol in v.values())
            for v in backup['collections'].values()
        )
        print(f"📊 Total documents backed up: {total_docs}\n")
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
