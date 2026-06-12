#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
import numpy as np

def run_comparison():
    db = firestore.Client(project='accountability-agent')
    print("⚡ Connected to Firestore. Querying user profiles...")
    
    users_ref = db.collection('users')
    users_docs = list(users_ref.stream())
    
    # Deployment threshold
    # Deployed At: 2026-06-02 10:26:26 UTC
    deployment_time = datetime(2026, 6, 2, 10, 26, 26, tzinfo=timezone.utc)
    print(f"Deployment Threshold: {deployment_time} UTC\n")
    
    pre_checkins = []
    post_checkins = []
    
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
            
            if comp_at:
                if comp_at.tzinfo is None:
                    comp_at = comp_at.replace(tzinfo=timezone.utc)
                
                # Attach parsed completed_at and user_id
                c['_parsed_completed_at'] = comp_at
                c['_user_id'] = user_id
                
                if comp_at < deployment_time:
                    pre_checkins.append(c)
                else:
                    post_checkins.append(c)
                    
    print(f"Total Pre-Update Check-ins:  {len(pre_checkins)}")
    print(f"Total Post-Update Check-ins: {len(post_checkins)}")
    print("-" * 50)
    
    def analyze_group(name, checkins):
        print(f"\n📈 ANALYSIS FOR: {name} (N = {len(checkins)})")
        if not checkins:
            print("No check-ins in this period.")
            return
            
        # 1. Quick check-in rate
        quick_count = sum(1 for c in checkins if c.get('is_quick_checkin', False))
        quick_pct = (quick_count / len(checkins)) * 100
        print(f"  - Quick Check-ins: {quick_count} ({quick_pct:.1f}%)")
        
        # 2. Average Duration
        durations = [c.get('duration_seconds', 0) for c in checkins if c.get('duration_seconds', 0) > 0]
        if durations:
            print(f"  - Average Duration: {np.mean(durations):.1f} seconds (Median: {np.median(durations):.1f}s)")
        else:
            print("  - Average Duration: N/A")
            
        # 3. Compliance Scores
        compliance = [c.get('compliance_score') for c in checkins if c.get('compliance_score') is not None]
        if compliance:
            print(f"  - Average Compliance Score: {np.mean(compliance):.1f}% (Median: {np.median(compliance):.1f}%)")
        else:
            print("  - Average Compliance Score: N/A")
            
        # 4. Habits breakdown
        habit_keys = ['sleep', 'training', 'deep_work', 'skill_building', 'zero_porn', 'boundaries']
        habit_completions = {k: 0 for k in habit_keys}
        
        for c in checkins:
            tier1 = c.get('tier1_non_negotiables', {})
            
            sh = tier1.get('sleep_hours')
            sleep_met = (sh >= 7.0) if sh is not None else tier1.get('sleep', False)
            if sleep_met: habit_completions['sleep'] += 1
            
            dwh = tier1.get('deep_work_hours')
            dw_met = (dwh >= 2.0) if dwh is not None else tier1.get('deep_work', False)
            if dw_met: habit_completions['deep_work'] += 1
            
            sbh = tier1.get('skill_building_hours')
            sb_met = (sbh >= 2.0) if sbh is not None else tier1.get('skill_building', False)
            if sb_met: habit_completions['skill_building'] += 1
            
            ti = tier1.get('training_intensity')
            train_met = (ti in ('light', 'moderate', 'intense')) if ti is not None else tier1.get('training', False)
            if train_met: habit_completions['training'] += 1
            
            if tier1.get('zero_porn', False): habit_completions['zero_porn'] += 1
            if tier1.get('boundaries', False): habit_completions['boundaries'] += 1
            
        print("  - Habit Met Rates:")
        for h in habit_keys:
            pct = (habit_completions[h] / len(checkins)) * 100
            print(f"    * {h:<15}: {pct:.1f}% ({habit_completions[h]} times)")
            
        # 5. Rest Day Analysis
        rest_days = sum(1 for c in checkins if c.get('tier1_non_negotiables', {}).get('is_rest_day', False))
        print(f"  - Rest Days Logged: {rest_days} ({(rest_days/len(checkins))*100:.1f}%)")

    analyze_group("PRE-UPDATE (Before June 2, 2026)", pre_checkins)
    analyze_group("POST-UPDATE (Since June 2, 2026)", post_checkins)
    
    # Calculate check-in frequency (days with check-ins per user)
    print("\n--- USER ENGAGEMENT PATTERNS ---")
    for doc in users_docs:
        user_id = doc.id
        u_checkins = [c for c in pre_checkins + post_checkins if c['_user_id'] == user_id]
        
        pre_u = [c for c in u_checkins if c['_parsed_completed_at'] < deployment_time]
        post_u = [c for c in u_checkins if c['_parsed_completed_at'] >= deployment_time]
        
        print(f"\nUser: {user_id}")
        
        # Pre metrics
        if pre_u:
            pre_dates = sorted(list(set(c['_parsed_completed_at'].date() for c in pre_u)))
            pre_span = (pre_dates[-1] - pre_dates[0]).days + 1
            pre_freq = len(pre_dates) / max(1, pre_span)
            print(f"  Pre-Update:  {len(pre_u)} checkins over {pre_span} days span ({pre_freq*100:.1f}% active days)")
        else:
            print("  Pre-Update:  No checkins")
            
        # Post metrics
        if post_u:
            post_dates = sorted(list(set(c['_parsed_completed_at'].date() for c in post_u)))
            post_span = (post_dates[-1] - post_dates[0]).days + 1
            post_freq = len(post_dates) / max(1, post_span)
            print(f"  Post-Update: {len(post_u)} checkins over {post_span} days span ({post_freq*100:.1f}% active days)")
        else:
            print("  Post-Update: No checkins")

if __name__ == "__main__":
    run_comparison()
