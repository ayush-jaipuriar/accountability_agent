#!/usr/bin/env python3
"""
Engagement Trend Analysis
=========================
Fetches all check-ins from Firestore and computes day-by-day
and week-by-week engagement trends:
  - Daily check-in count (how many check-ins happened each day)
  - Unique daily users
  - Rolling 7-day active users (WAU per day)
  - Average compliance score per week
  - Habit adherence trends per week
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore

def fetch_all_checkins(db):
    users_docs = list(db.collection('users').stream())
    print(f"👥 Found {len(users_docs)} users.")

    all_checkins = []   # list of dicts with user_id and parsed date
    for doc in users_docs:
        user_id = doc.id
        checkin_docs = list(
            db.collection('daily_checkins')
              .document(user_id)
              .collection('checkins')
              .stream()
        )
        for c_doc in checkin_docs:
            c = c_doc.to_dict()
            comp_at = c.get('completed_at')
            if isinstance(comp_at, str):
                try:
                    comp_at = datetime.fromisoformat(comp_at.replace('Z', '+00:00'))
                except Exception:
                    comp_at = None
            elif not isinstance(comp_at, datetime):
                try:
                    comp_at = datetime.strptime(
                        c.get('date', ''), '%Y-%m-%d'
                    ).replace(tzinfo=timezone.utc)
                except Exception:
                    comp_at = None

            if comp_at:
                if comp_at.tzinfo is None:
                    comp_at = comp_at.replace(tzinfo=timezone.utc)
                c['_ts'] = comp_at
                c['_date'] = comp_at.date()
                c['_user_id'] = user_id
                all_checkins.append(c)

    all_checkins.sort(key=lambda x: x['_ts'])
    print(f"📋 Total check-ins fetched: {len(all_checkins)}\n")
    return all_checkins


def daily_trend(all_checkins):
    """Day-by-day: check-in count + unique users."""
    by_day = defaultdict(list)
    for c in all_checkins:
        by_day[c['_date']].append(c)

    if not by_day:
        return

    start = min(by_day)
    end   = max(by_day)
    total_days = (end - start).days + 1

    print("=" * 70)
    print("📅  DAILY TREND  (check-ins per day + unique active users)")
    print("=" * 70)
    print(f"{'Date':<13} {'Check-ins':>10} {'Unique Users':>13} {'Avg Compliance':>15}")
    print("-" * 55)

    current = start
    while current <= end:
        day_checkins = by_day.get(current, [])
        count = len(day_checkins)
        unique = len(set(c['_user_id'] for c in day_checkins))
        scores = [c['compliance_score'] for c in day_checkins
                  if c.get('compliance_score') is not None]
        avg_score = f"{sum(scores)/len(scores):.1f}%" if scores else "—"
        bar = "█" * count
        print(f"{str(current):<13} {count:>10}  {unique:>12}  {avg_score:>15}  {bar}")
        current += timedelta(days=1)
    print()


def weekly_trend(all_checkins):
    """ISO-week buckets: check-ins, unique users, compliance, habit adherence."""
    by_week = defaultdict(list)
    for c in all_checkins:
        iso = c['_ts'].isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        by_week[week_key].append(c)

    if not by_week:
        return

    habit_keys = ['sleep', 'training', 'deep_work', 'skill_building', 'zero_porn', 'boundaries']

    print("=" * 70)
    print("📆  WEEKLY TREND")
    print("=" * 70)

    for week in sorted(by_week):
        wc = by_week[week]
        unique = len(set(c['_user_id'] for c in wc))
        scores = [c['compliance_score'] for c in wc if c.get('compliance_score') is not None]
        avg_score = f"{sum(scores)/len(scores):.1f}%" if scores else "—"

        # Habit adherence
        hab = {k: 0 for k in habit_keys}
        for c in wc:
            t1 = c.get('tier1_non_negotiables', {})
            sh   = t1.get('sleep_hours')
            if (sh >= 7.0 if sh is not None else t1.get('sleep', False)): hab['sleep'] += 1
            dwh  = t1.get('deep_work_hours')
            if (dwh >= 2.0 if dwh is not None else t1.get('deep_work', False)): hab['deep_work'] += 1
            sbh  = t1.get('skill_building_hours')
            if (sbh >= 2.0 if sbh is not None else t1.get('skill_building', False)): hab['skill_building'] += 1
            ti   = t1.get('training_intensity')
            if (ti in ('light','moderate','intense') if ti is not None else t1.get('training', False)): hab['training'] += 1
            if t1.get('zero_porn', False):   hab['zero_porn'] += 1
            if t1.get('boundaries', False):  hab['boundaries'] += 1

        n = len(wc)
        print(f"\n  {week}  |  {n} check-ins  |  {unique} active users  |  Compliance: {avg_score}")
        print(f"  {'Habit':<20} {'Rate':>6}  {'Bar'}")
        print(f"  {'-'*45}")
        for h in habit_keys:
            rate = hab[h] / n * 100 if n else 0
            bar = "▓" * int(rate / 10)
            print(f"  {h:<20} {rate:>5.1f}%  {bar}")
    print()


def rolling_wau(all_checkins):
    """For each day, compute 7-day rolling unique active users."""
    by_day = defaultdict(set)
    for c in all_checkins:
        by_day[c['_date']].add(c['_user_id'])

    if not by_day:
        return

    start = min(by_day)
    end   = max(by_day)

    print("=" * 70)
    print("📊  ROLLING 7-DAY ACTIVE USERS (WAU) — sampled every 7 days")
    print("=" * 70)
    print(f"{'Date':<13} {'7d Active Users':>16}  Bar")
    print("-" * 45)

    current = start + timedelta(days=6)
    while current <= end:
        window_start = current - timedelta(days=6)
        active = set()
        d = window_start
        while d <= current:
            active |= by_day.get(d, set())
            d += timedelta(days=1)
        bar = "█" * len(active)
        print(f"{str(current):<13} {len(active):>16}  {bar}")
        current += timedelta(days=7)
    print()


def streak_trend(db, all_checkins):
    """Show how many users were on a positive streak each week."""
    # Derive streaks from check-in continuity per user
    by_user = defaultdict(list)
    for c in all_checkins:
        by_user[c['_user_id']].append(c['_date'])

    # Compute daily streak per user
    user_daily_streak = {}
    for uid, dates in by_user.items():
        dates_sorted = sorted(set(dates))
        streak_map = {}
        streak = 0
        prev = None
        for d in dates_sorted:
            if prev is not None and (d - prev).days == 1:
                streak += 1
            else:
                streak = 1
            streak_map[d] = streak
            prev = d
        user_daily_streak[uid] = streak_map

    if not user_daily_streak:
        return

    all_dates = sorted(set(d for sm in user_daily_streak.values() for d in sm))
    if not all_dates:
        return

    print("=" * 70)
    print("🔥  STREAK TREND — avg streak length per active day (sampled weekly)")
    print("=" * 70)
    print(f"{'Date':<13} {'Avg Streak':>11}  {'Max Streak':>11}")
    print("-" * 40)

    # Sample weekly
    by_week = defaultdict(list)
    for d in all_dates:
        iso = d.isocalendar()
        by_week[f"{iso[0]}-W{iso[1]:02d}"].append(d)

    for week in sorted(by_week):
        streaks_this_week = []
        for d in by_week[week]:
            for uid, sm in user_daily_streak.items():
                if d in sm:
                    streaks_this_week.append(sm[d])
        if streaks_this_week:
            avg_s = sum(streaks_this_week) / len(streaks_this_week)
            max_s = max(streaks_this_week)
            print(f"{week:<13} {avg_s:>11.1f}  {max_s:>11}")
    print()


def main():
    db = firestore.Client(project='accountability-agent')
    print("⚡ Connected to Firestore.\n")

    all_checkins = fetch_all_checkins(db)
    if not all_checkins:
        print("No check-in data found.")
        return

    daily_trend(all_checkins)
    weekly_trend(all_checkins)
    rolling_wau(all_checkins)
    streak_trend(db, all_checkins)


if __name__ == "__main__":
    main()
