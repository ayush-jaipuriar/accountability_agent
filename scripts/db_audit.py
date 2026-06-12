#!/usr/bin/env python3
"""
Database Audit & Usage Metrics Script
======================================

Connects to Firestore to query user data, check-ins, and pattern/interventions history,
and calculates engagement metrics (DAU, WAU, MAU, compliance rates, habit breakdown).
This script aggregates data to keep user responses and personal details private.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseAuditor:
    def __init__(self):
        self.db = firestore.Client()
        print("⚡ Connected to Firestore successfully.")

    def run_audit(self):
        print("🔍 Commencing database audit...")
        
        # 1. Fetch all users
        users_ref = self.db.collection('users')
        users_docs = list(users_ref.stream())
        total_users = len(users_docs)
        print(f"👥 Found {total_users} user profiles in database.")
        
        if total_users == 0:
            print("⚠️ No users found in database.")
            return

        users_data = []
        all_checkins = {}
        all_interventions = {}
        
        # Current UTC time for activity calculations
        now_utc = datetime.now(timezone.utc)
        
        print("📥 Fetching user subcollections (check-ins and interventions)...")
        for idx, doc in enumerate(users_docs):
            user_id = doc.id
            data = doc.to_dict()
            users_data.append(data)
            
            # Fetch check-ins
            checkins_ref = doc.reference.collection('checkins')
            # Alternatively check daily_checkins/{user_id}/checkins which is the path in firestore_service
            # Let's check both paths to be safe.
            # In firestore_service.py:
            # checkin_ref = self.db.collection('daily_checkins').document(user_id).collection('checkins')
            checkin_docs = list(self.db.collection('daily_checkins').document(user_id).collection('checkins').stream())
            user_checkins = [d.to_dict() for d in checkin_docs]
            all_checkins[user_id] = user_checkins
            
            # Fetch interventions
            intervention_docs = list(self.db.collection('interventions').document(user_id).collection('interventions').stream())
            user_interventions = [d.to_dict() for d in intervention_docs]
            all_interventions[user_id] = user_interventions
            
            sys.stdout.write(f"\r⏳ Progress: {idx+1}/{total_users} users processed")
            sys.stdout.flush()
        print("\n✅ Data retrieval complete.\n")
        
        # Perform aggregations
        self.aggregate_metrics(users_data, all_checkins, all_interventions, now_utc)

    def aggregate_metrics(self, users, checkins_map, interventions_map, now_utc):
        print("📊 ===================================================")
        print("📊 ACCOUNTABILITY AGENT METRICS & AUDIT REPORT")
        print("📊 ===================================================")
        
        total_users = len(users)
        
        # Time-based windows
        one_day_ago = now_utc - timedelta(days=1)
        seven_days_ago = now_utc - timedelta(days=7)
        thirty_days_ago = now_utc - timedelta(days=30)
        
        # 1. User Profiles & Modes
        constitution_modes = Counter([u.get('constitution_mode', 'unknown') for u in users])
        career_modes = Counter([u.get('career_mode', 'unknown') for u in users])
        timezones = Counter([u.get('timezone', 'unknown') for u in users])
        leaderboard_opt = Counter([u.get('leaderboard_opt_in', True) for u in users])
        partners_linked = sum(1 for u in users if u.get('accountability_partner_id') is not None)
        
        print("\n--- USER PROFILES ---")
        print(f"Total Registered Users: {total_users}")
        print("\nConstitution Modes:")
        for mode, count in constitution_modes.items():
            print(f"  - {mode}: {count} ({count/total_users*100:.1f}%)")
            
        print("\nCareer Modes:")
        for mode, count in career_modes.items():
            print(f"  - {mode}: {count} ({count/total_users*100:.1f}%)")
            
        print("\nTimezones Distribution:")
        for tz, count in timezones.most_common(5):
            print(f"  - {tz}: {count} ({count/total_users*100:.1f}%)")
            
        print(f"\nAccountability Partnerships: {partners_linked} users linked ({partners_linked/total_users*100:.1f}%)")
        print(f"Leaderboard Opt-In Rate: {leaderboard_opt.get(True, 0)} users ({leaderboard_opt.get(True, 0)/total_users*100:.1f}%)")
        
        # 2. Activity Metrics (DAU / WAU / MAU)
        # We calculate active status based on completed_at in checkins
        active_1d = set()
        active_7d = set()
        active_30d = set()
        
        total_checkins_count = 0
        all_checkin_dates = []
        checkin_counts_per_user = []
        
        # For habits analysis
        habit_completions = {
            'sleep': 0, 'training': 0, 'deep_work': 0, 'skill_building': 0,
            'zero_porn': 0, 'boundaries': 0
        }
        sleep_hours_list = []
        deep_work_hours_list = []
        skill_building_hours_list = []
        training_intensities = []
        compliance_scores = []
        duration_seconds_list = []
        quick_checkins_count = 0
        
        for user_id, u_checkins in checkins_map.items():
            checkin_counts_per_user.append(len(u_checkins))
            total_checkins_count += len(u_checkins)
            
            for c in u_checkins:
                # Get completed_at
                comp_at = c.get('completed_at')
                if isinstance(comp_at, str):
                    comp_at = datetime.fromisoformat(comp_at.replace('Z', '+00:00'))
                elif not isinstance(comp_at, datetime):
                    # Check fallback: date string
                    try:
                        comp_at = datetime.strptime(c.get('date', ''), '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    except:
                        comp_at = None
                
                if comp_at:
                    if comp_at.tzinfo is None:
                        comp_at = comp_at.replace(tzinfo=timezone.utc)
                    
                    if comp_at >= one_day_ago:
                        active_1d.add(user_id)
                    if comp_at >= seven_days_ago:
                        active_7d.add(user_id)
                    if comp_at >= thirty_days_ago:
                        active_30d.add(user_id)
                
                # Compliance score
                score = c.get('compliance_score')
                if score is not None:
                    compliance_scores.append(score)
                
                # Check-in duration
                dur = c.get('duration_seconds', 0)
                if dur > 0:
                    duration_seconds_list.append(dur)
                    
                # Is quick check-in
                if c.get('is_quick_checkin', False):
                    quick_checkins_count += 1
                
                # Habits
                tier1 = c.get('tier1_non_negotiables', {})
                
                # Continuous variables
                sh = tier1.get('sleep_hours')
                if sh is not None: sleep_hours_list.append(sh)
                
                dwh = tier1.get('deep_work_hours')
                if dwh is not None: deep_work_hours_list.append(dwh)
                
                sbh = tier1.get('skill_building_hours')
                if sbh is not None: skill_building_hours_list.append(sbh)
                
                ti = tier1.get('training_intensity')
                if ti is not None: training_intensities.append(ti)
                
                # Boolean completion rates
                # Read properties or fallback
                # For sleep: met if sleep_hours >= 7 or sleep == True
                sleep_met = (sh >= 7.0) if sh is not None else tier1.get('sleep', False)
                if sleep_met: habit_completions['sleep'] += 1
                
                dw_met = (dwh >= 2.0) if dwh is not None else tier1.get('deep_work', False)
                if dw_met: habit_completions['deep_work'] += 1
                
                sb_met = (sbh >= 2.0) if sbh is not None else tier1.get('skill_building', False)
                if sb_met: habit_completions['skill_building'] += 1
                
                train_met = (ti in ('light', 'moderate', 'intense')) if ti is not None else tier1.get('training', False)
                if train_met: habit_completions['training'] += 1
                
                if tier1.get('zero_porn', False): habit_completions['zero_porn'] += 1
                if tier1.get('boundaries', False): habit_completions['boundaries'] += 1
        
        dau = len(active_1d)
        wau = len(active_7d)
        mau = len(active_30d)
        
        print("\n--- ENGAGEMENT METRICS ---")
        print(f"Daily Active Users (DAU - last 24h): {dau} ({dau/total_users*100:.1f}% of registered)")
        print(f"Weekly Active Users (WAU - last 7d):  {wau} ({wau/total_users*100:.1f}% of registered)")
        print(f"Monthly Active Users (MAU - last 30d): {mau} ({mau/total_users*100:.1f}% of registered)")
        if mau > 0:
            print(f"Engagement Stickiness (DAU/MAU): {dau/mau*100:.1f}%")
        else:
            print("Engagement Stickiness (DAU/MAU): N/A (MAU is 0)")
            
        print(f"Total Check-ins Completed: {total_checkins_count}")
        if total_users > 0:
            print(f"Average Check-ins per User: {total_checkins_count/total_users:.1f}")
        
        # 3. Streaks & Gamification
        streaks_data = [u.get('streaks', {}) for u in users]
        current_streaks = [s.get('current_streak', 0) for s in streaks_data]
        longest_streaks = [s.get('longest_streak', 0) for s in streaks_data]
        
        print("\n--- STREAKS & GAMIFICATION ---")
        print(f"Average Current Streak: {np.mean(current_streaks):.1f} days")
        print(f"Max Current Streak:     {max(current_streaks) if current_streaks else 0} days")
        print(f"Average Longest Streak: {np.mean(longest_streaks):.1f} days")
        print(f"Max Longest Streak:     {max(longest_streaks) if longest_streaks else 0} days")
        
        # Achievement unlock stats
        all_unlocked_achievements = []
        for u in users:
            all_unlocked_achievements.extend(u.get('achievements', []))
        achievement_counts = Counter(all_unlocked_achievements)
        
        print("\nAchievements Unlocked Distribution:")
        print(f"  Total Achievements Unlocked: {len(all_unlocked_achievements)}")
        for ach, count in achievement_counts.most_common(5):
            print(f"  - {ach}: {count} users")
            
        # Streak Shield Usage
        total_shields_used = sum(u.get('streak_shields', {}).get('used', 0) for u in users if 'streak_shields' in u)
        print(f"Total Streak Shields Used: {total_shields_used}")

        # 4. Habits & Compliance Analysis
        print("\n--- HABITS & COMPLIANCE ---")
        if compliance_scores:
            print(f"Average Compliance Score: {np.mean(compliance_scores):.1f}%")
            print(f"Median Compliance Score:  {np.median(compliance_scores):.1f}%")
        else:
            print("Average Compliance Score: N/A")
            
        if duration_seconds_list:
            print(f"Average Check-in Duration: {np.mean(duration_seconds_list):.1f} seconds")
            print(f"Quick Check-in usage: {quick_checkins_count} check-ins ({quick_checkins_count/max(1, total_checkins_count)*100:.1f}% of total)")
        
        print("\nHabit Adherence Rates (Percentage of check-ins meeting target):")
        if total_checkins_count > 0:
            for habit, count in habit_completions.items():
                print(f"  - {habit:<20}: {count/total_checkins_count*100:5.1f}% ({count} times)")
        else:
            print("  No check-in data available.")
            
        print("\nContinuous Habits Metrics (Averages when logged):")
        if sleep_hours_list:
            print(f"  - Avg Sleep:           {np.mean(sleep_hours_list):.2f} hours (N={len(sleep_hours_list)})")
        if deep_work_hours_list:
            print(f"  - Avg Deep Work:       {np.mean(deep_work_hours_list):.2f} hours (N={len(deep_work_hours_list)})")
        if skill_building_hours_list:
            print(f"  - Avg Skill Building:  {np.mean(skill_building_hours_list):.2f} hours (N={len(skill_building_hours_list)})")
        if training_intensities:
            intensity_counts = Counter(training_intensities)
            print("  - Training Intensity:")
            for intensity, count in intensity_counts.items():
                print(f"    * {intensity}: {count} times ({count/len(training_intensities)*100:.1f}%)")

        # 5. Streak Breaks & Churn Risk
        break_reasons_counter = Counter()
        for u in users:
            for br in u.get('break_reasons', []):
                reason = br.get('reason', 'unknown')
                break_reasons_counter[reason] += 1
                
        print("\n--- STREAK BREAKS & CHURN ---")
        print("Primary Reasons for Streak Breaks (from recovery surveys):")
        if break_reasons_counter:
            for reason, count in break_reasons_counter.most_common():
                print(f"  - {reason}: {count} times")
        else:
            print("  No streak break reasons logged yet.")
            
        churn_scores = [u.get('churn_risk_score', 0.0) for u in users if 'churn_risk_score' in u]
        if churn_scores:
            print(f"Average Churn Risk Score: {np.mean(churn_scores):.2f} (Scale 0.0-1.0)")
            high_risk_users = sum(1 for s in churn_scores if s >= 0.7)
            print(f"High Churn Risk Users (>=0.7): {high_risk_users} ({high_risk_users/total_users*100:.1f}%)")

        # 6. Anomalies / Pattern Detections & Interventions
        total_interventions = sum(len(ints) for ints in interventions_map.values())
        resolved_interventions = sum(sum(1 for i in ints if i.get('resolved', False)) for ints in interventions_map.values())
        
        intervention_patterns = Counter()
        for ints in interventions_map.values():
            for i in ints:
                pattern = i.get('pattern_type', 'unknown')
                intervention_patterns[pattern] += 1
                
        print("\n--- ANOMALIES & INTERVENTIONS ---")
        print(f"Total AI Interventions Triggered: {total_interventions}")
        if total_interventions > 0:
            print(f"Intervention Resolution Rate:    {resolved_interventions/total_interventions*100:.1f}%")
            print("Top Interventions by Pattern Type:")
            for pat, count in intervention_patterns.most_common(5):
                print(f"  - {pat}: {count} times")
        else:
            print("  No interventions recorded.")
            
        print("\n📊 ===================================================")

def main():
    try:
        auditor = DatabaseAuditor()
        auditor.run_audit()
    except Exception as e:
        logger.error(f"Audit run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
