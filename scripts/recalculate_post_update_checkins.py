#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from src.models.schemas import Tier1NonNegotiables
from src.utils.compliance import calculate_compliance_score

def run_recalculation():
    db = firestore.Client(project='accountability-agent')
    print("⚡ Connected to Firestore. Querying user profiles...")
    
    users_ref = db.collection('users')
    users_docs = list(users_ref.stream())
    
    deployment_time = datetime(2026, 6, 2, 10, 26, 26, tzinfo=timezone.utc)
    print(f"Deployment Threshold: {deployment_time} UTC\n")
    
    updated_count = 0
    
    for doc in users_docs:
        user_id = doc.id
        checkin_docs = list(db.collection('daily_checkins').document(user_id).collection('checkins').stream())
        
        for c_doc in checkin_docs:
            c = c_doc.to_dict()
            comp_at = c.get('completed_at')
            if isinstance(comp_at, str):
                comp_at = datetime.fromisoformat(comp_at.replace('Z', '+00:00'))
            elif not isinstance(comp_at, datetime):
                try:
                    comp_at = datetime.strptime(c.get('date', ''), '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except:
                    comp_at = None
            
            if comp_at and comp_at >= deployment_time:
                # This is a post-update check-in.
                tier1_dict = c.get('tier1_non_negotiables', {})
                sleep_hours = tier1_dict.get('sleep_hours')
                dw_hours = tier1_dict.get('deep_work_hours')
                sb_hours = tier1_dict.get('skill_building_hours')
                intensity = tier1_dict.get('training_intensity', 'rest').lower()
                
                # Re-calculate correct legacy booleans using full targets
                new_sleep = sleep_hours >= 7.0 if sleep_hours is not None else tier1_dict.get('sleep', False)
                new_dw = dw_hours >= 2.0 if dw_hours is not None else tier1_dict.get('deep_work', False)
                new_sb = sb_hours >= 2.0 if sb_hours is not None else tier1_dict.get('skill_building', False)
                
                tier1 = Tier1NonNegotiables(
                    sleep_hours=sleep_hours,
                    deep_work_hours=dw_hours,
                    skill_building_hours=sb_hours,
                    training_intensity=intensity,
                    sleep=new_sleep,
                    training=intensity in ('light', 'moderate', 'intense'),
                    deep_work=new_dw,
                    skill_building=new_sb,
                    is_rest_day=intensity == 'rest',
                    zero_porn=tier1_dict.get('zero_porn', False),
                    boundaries=tier1_dict.get('boundaries', False),
                    data_quality=tier1_dict.get('data_quality', 'actual')
                )
                
                new_score = calculate_compliance_score(tier1)
                
                # Check if values actually changed
                if (tier1_dict.get('sleep') != new_sleep or 
                    tier1_dict.get('deep_work') != new_dw or 
                    tier1_dict.get('skill_building') != new_sb or 
                    abs(c.get('compliance_score', 0) - new_score) > 0.01):
                    
                    print(f"✏️ Updating check-in for {user_id} on {c.get('date')}:")
                    print(f"  Old: sleep={tier1_dict.get('sleep')}, dw={tier1_dict.get('deep_work')}, sb={tier1_dict.get('skill_building')}, score={c.get('compliance_score')}%")
                    print(f"  New: sleep={new_sleep}, dw={new_dw}, sb={new_sb}, score={new_score}%")
                    
                    c_doc.reference.update({
                        "tier1_non_negotiables": tier1.model_dump(),
                        "compliance_score": new_score
                    })
                    updated_count += 1
                    
    print(f"\n✅ Finished. Updated {updated_count} check-ins.")

if __name__ == "__main__":
    run_recalculation()
