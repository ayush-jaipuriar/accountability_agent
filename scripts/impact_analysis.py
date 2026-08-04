#!/usr/bin/env python3
"""
Deep Impact Analysis — Has the app actually improved user outcomes?
===================================================================
Splits each user's check-in history into thirds (early / mid / recent)
and compares habit adherence, compliance scores, streak resilience,
and check-in consistency across phases to determine whether there is
genuine improvement, stagnation, or regression.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore


def parse_ts(c):
    comp_at = c.get('completed_at')
    if isinstance(comp_at, str):
        try:
            return datetime.fromisoformat(comp_at.replace('Z', '+00:00'))
        except:
            pass
    elif isinstance(comp_at, datetime):
        if comp_at.tzinfo is None:
            return comp_at.replace(tzinfo=timezone.utc)
        return comp_at
    try:
        return datetime.strptime(c.get('date', ''), '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except:
        return None


def extract_habits(c):
    """Return dict of habit booleans + continuous values from a check-in."""
    t1 = c.get('tier1_non_negotiables', {})
    sh = t1.get('sleep_hours')
    dwh = t1.get('deep_work_hours')
    sbh = t1.get('skill_building_hours')
    ti = t1.get('training_intensity')

    return {
        'sleep_met': (sh >= 7.0) if sh is not None else bool(t1.get('sleep', False)),
        'training_met': (ti in ('light', 'moderate', 'intense')) if ti is not None else bool(t1.get('training', False)),
        'deep_work_met': (dwh >= 2.0) if dwh is not None else bool(t1.get('deep_work', False)),
        'skill_building_met': (sbh >= 2.0) if sbh is not None else bool(t1.get('skill_building', False)),
        'zero_porn_met': bool(t1.get('zero_porn', False)),
        'boundaries_met': bool(t1.get('boundaries', False)),
        'sleep_hours': sh,
        'deep_work_hours': dwh,
        'skill_building_hours': sbh,
        'training_intensity': ti,
        'compliance_score': c.get('compliance_score'),
        'is_quick': c.get('is_quick_checkin', False),
        'duration_seconds': c.get('duration_seconds', 0),
    }


def split_into_phases(checkins, n_phases=3):
    """Split sorted checkins into n equal-ish phases by count."""
    if not checkins:
        return []
    k, m = divmod(len(checkins), n_phases)
    phases = []
    idx = 0
    for i in range(n_phases):
        size = k + (1 if i < m else 0)
        if size > 0:
            phases.append(checkins[idx:idx + size])
        idx += size
    return phases


def phase_stats(checkins):
    """Compute aggregate stats for a list of parsed check-ins."""
    n = len(checkins)
    if n == 0:
        return None

    dates = sorted(set(c['_date'] for c in checkins))
    span_days = (dates[-1] - dates[0]).days + 1

    habits = [extract_habits(c) for c in checkins]

    # Habit adherence rates
    habit_keys = ['sleep_met', 'training_met', 'deep_work_met',
                  'skill_building_met', 'zero_porn_met', 'boundaries_met']
    rates = {}
    for k in habit_keys:
        rates[k] = sum(1 for h in habits if h[k]) / n * 100

    # Compliance scores
    scores = [h['compliance_score'] for h in habits if h['compliance_score'] is not None]
    avg_compliance = sum(scores) / len(scores) if scores else None

    # Continuous metrics
    sleep_hrs = [h['sleep_hours'] for h in habits if h['sleep_hours'] is not None]
    dw_hrs = [h['deep_work_hours'] for h in habits if h['deep_work_hours'] is not None]
    sb_hrs = [h['skill_building_hours'] for h in habits if h['skill_building_hours'] is not None]

    avg_sleep = sum(sleep_hrs) / len(sleep_hrs) if sleep_hrs else None
    avg_dw = sum(dw_hrs) / len(dw_hrs) if dw_hrs else None
    avg_sb = sum(sb_hrs) / len(sb_hrs) if sb_hrs else None

    # Streak analysis: consecutive days with check-ins
    streaks = []
    streak = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            streak += 1
        else:
            streaks.append(streak)
            streak = 1
    streaks.append(streak)
    avg_streak = sum(streaks) / len(streaks) if streaks else 0
    max_streak = max(streaks) if streaks else 0

    # Check-in consistency: what % of days in the span had a check-in?
    consistency = len(dates) / span_days * 100 if span_days > 0 else 0

    # Quick check-in ratio
    quick_ratio = sum(1 for h in habits if h['is_quick']) / n * 100

    return {
        'n': n,
        'date_range': f"{dates[0]} → {dates[-1]}",
        'span_days': span_days,
        'active_days': len(dates),
        'consistency': consistency,
        'avg_compliance': avg_compliance,
        'rates': rates,
        'avg_sleep': avg_sleep,
        'avg_dw': avg_dw,
        'avg_sb': avg_sb,
        'avg_streak': avg_streak,
        'max_streak': max_streak,
        'quick_ratio': quick_ratio,
    }


def delta_arrow(early, late):
    """Return a delta string with arrow."""
    if early is None or late is None:
        return "N/A"
    diff = late - early
    if abs(diff) < 0.5:
        return f"→ {late:.1f} (flat)"
    arrow = "↑" if diff > 0 else "↓"
    return f"{arrow} {late:.1f} ({diff:+.1f})"


def analyze_user(user_id, checkins):
    """Run full trajectory analysis for one user."""
    checkins.sort(key=lambda c: c['_ts'])
    phases = split_into_phases(checkins, 3)
    labels = ['EARLY', 'MID', 'RECENT']

    print(f"\n{'='*70}")
    print(f"  USER: {user_id}")
    print(f"  Total check-ins: {len(checkins)}")
    print(f"  First: {checkins[0]['_date']}  |  Latest: {checkins[-1]['_date']}")
    total_span = (checkins[-1]['_date'] - checkins[0]['_date']).days + 1
    print(f"  Total span: {total_span} days")
    print(f"{'='*70}")

    stats_list = []
    for i, phase in enumerate(phases):
        s = phase_stats(phase)
        stats_list.append(s)
        print(f"\n  --- Phase {i+1}: {labels[i]} ({s['n']} check-ins, {s['date_range']}) ---")
        print(f"  Days spanned: {s['span_days']}  |  Active days: {s['active_days']}  |  Consistency: {s['consistency']:.1f}%")
        print(f"  Avg Compliance: {s['avg_compliance']:.1f}%" if s['avg_compliance'] is not None else "  Avg Compliance: N/A")
        print(f"  Avg Streak: {s['avg_streak']:.1f} days  |  Max Streak: {s['max_streak']} days")
        print(f"  Quick Check-in Ratio: {s['quick_ratio']:.1f}%")
        print(f"  Habit Adherence:")
        for k, v in s['rates'].items():
            label = k.replace('_met', '')
            print(f"    {label:<20}: {v:5.1f}%")
        if s['avg_sleep'] is not None:
            print(f"  Avg Sleep Hours: {s['avg_sleep']:.2f}")
        if s['avg_dw'] is not None:
            print(f"  Avg Deep Work Hours: {s['avg_dw']:.2f}")
        if s['avg_sb'] is not None:
            print(f"  Avg Skill Building Hours: {s['avg_sb']:.2f}")

    # VERDICT: Compare EARLY vs RECENT
    e = stats_list[0]
    r = stats_list[-1]

    print(f"\n  {'─'*60}")
    print(f"  📊 EARLY → RECENT COMPARISON (Improvement Assessment)")
    print(f"  {'─'*60}")

    print(f"  Compliance:     {delta_arrow(e['avg_compliance'], r['avg_compliance'])}")
    print(f"  Consistency:    {delta_arrow(e['consistency'], r['consistency'])}")
    print(f"  Avg Streak:     {delta_arrow(e['avg_streak'], r['avg_streak'])}")
    print(f"  Max Streak:     {e['max_streak']} → {r['max_streak']}")
    print(f"  Quick Ratio:    {delta_arrow(e['quick_ratio'], r['quick_ratio'])}")

    habit_keys = ['sleep_met', 'training_met', 'deep_work_met',
                  'skill_building_met', 'zero_porn_met', 'boundaries_met']
    improved = 0
    regressed = 0
    flat = 0
    print(f"\n  Habit-by-Habit Trajectory:")
    for k in habit_keys:
        label = k.replace('_met', '')
        ev = e['rates'][k]
        rv = r['rates'][k]
        diff = rv - ev
        if diff > 5:
            verdict = "✅ IMPROVED"
            improved += 1
        elif diff < -5:
            verdict = "❌ REGRESSED"
            regressed += 1
        else:
            verdict = "➡️ FLAT"
            flat += 1
        print(f"    {label:<20}: {ev:5.1f}% → {rv:5.1f}% ({diff:+.1f}pp)  {verdict}")

    # Continuous metrics comparison
    if e['avg_sleep'] is not None and r['avg_sleep'] is not None:
        print(f"    sleep hours avg   : {e['avg_sleep']:.2f} → {r['avg_sleep']:.2f}")
    if e['avg_dw'] is not None and r['avg_dw'] is not None:
        print(f"    deep work hrs avg : {e['avg_dw']:.2f} → {r['avg_dw']:.2f}")
    if e['avg_sb'] is not None and r['avg_sb'] is not None:
        print(f"    skill bld hrs avg : {e['avg_sb']:.2f} → {r['avg_sb']:.2f}")

    # Overall verdict
    print(f"\n  ┌──────────────────────────────────────────────┐")
    compliance_delta = (r['avg_compliance'] or 0) - (e['avg_compliance'] or 0)
    consistency_delta = r['consistency'] - e['consistency']
    streak_delta = r['avg_streak'] - e['avg_streak']

    score = 0
    score += 1 if compliance_delta > 3 else (-1 if compliance_delta < -3 else 0)
    score += 1 if consistency_delta > 5 else (-1 if consistency_delta < -5 else 0)
    score += 1 if streak_delta > 0.5 else (-1 if streak_delta < -0.5 else 0)
    score += improved - regressed

    if score >= 3:
        verdict = "📈 CLEAR IMPROVEMENT — the app is working"
    elif score >= 1:
        verdict = "↗️  MARGINAL IMPROVEMENT — some habits improved, some stagnant"
    elif score >= -1:
        verdict = "➡️  STAGNATION — no meaningful improvement detected"
    elif score >= -3:
        verdict = "↘️  SLIGHT REGRESSION — user is doing worse than early days"
    else:
        verdict = "📉 SIGNIFICANT REGRESSION — app has not helped"

    print(f"  │ VERDICT: {verdict}")
    print(f"  │ Score: {score} (habits: +{improved}/-{regressed}/={flat}, ")
    print(f"  │   compliance Δ={compliance_delta:+.1f}, consistency Δ={consistency_delta:+.1f})")
    print(f"  └──────────────────────────────────────────────┘")

    return {
        'user_id': user_id,
        'score': score,
        'verdict': verdict,
        'compliance_delta': compliance_delta,
        'improved': improved,
        'regressed': regressed,
        'flat': flat,
    }


def monthly_rolling_compliance(all_checkins):
    """Show 30-day rolling avg compliance to reveal long-term trend."""
    print(f"\n{'='*70}")
    print("📉 30-DAY ROLLING AVERAGE COMPLIANCE (sampled bi-weekly)")
    print(f"{'='*70}")

    all_checkins.sort(key=lambda c: c['_ts'])
    if not all_checkins:
        return

    start = all_checkins[0]['_date']
    end = all_checkins[-1]['_date']

    current = start + timedelta(days=30)
    print(f"{'Date':<13} {'30d Avg Compliance':>20} {'30d Check-ins':>14}  Visual")
    print("-" * 65)

    while current <= end + timedelta(days=1):
        window_start = current - timedelta(days=30)
        window_cks = [c for c in all_checkins
                      if window_start <= c['_date'] <= current]
        scores = [c.get('compliance_score') for c in window_cks
                  if c.get('compliance_score') is not None]
        avg = sum(scores) / len(scores) if scores else None

        if avg is not None:
            bar = "█" * int(avg / 5)
            print(f"{str(current):<13} {avg:>18.1f}% {len(window_cks):>14}  {bar}")
        else:
            print(f"{str(current):<13} {'N/A':>20} {len(window_cks):>14}")

        current += timedelta(days=14)  # bi-weekly sampling


def main():
    db = firestore.Client(project='accountability-agent')
    print("⚡ Connected to Firestore.\n")

    users_docs = list(db.collection('users').stream())
    print(f"👥 Found {len(users_docs)} users.\n")

    all_checkins = []
    user_checkins = {}

    for doc in users_docs:
        user_id = doc.id
        checkin_docs = list(
            db.collection('daily_checkins')
              .document(user_id)
              .collection('checkins')
              .stream()
        )
        parsed = []
        for c_doc in checkin_docs:
            c = c_doc.to_dict()
            ts = parse_ts(c)
            if ts:
                c['_ts'] = ts
                c['_date'] = ts.date()
                c['_user_id'] = user_id
                parsed.append(c)
                all_checkins.append(c)

        user_checkins[user_id] = parsed
        print(f"  {user_id}: {len(parsed)} check-ins")

    print()

    # Per-user trajectory analysis
    verdicts = []
    for uid, cks in user_checkins.items():
        if len(cks) >= 6:  # need minimum data to split into phases
            v = analyze_user(uid, cks)
            verdicts.append(v)
        else:
            print(f"\n  {uid}: Too few check-ins ({len(cks)}) for trajectory analysis.")

    # Rolling compliance
    monthly_rolling_compliance(all_checkins)

    # Final summary
    print(f"\n{'='*70}")
    print("🏁 OVERALL IMPACT ASSESSMENT")
    print(f"{'='*70}")
    for v in verdicts:
        print(f"  {v['user_id']}: {v['verdict']}")
        print(f"    Habits improved: {v['improved']}, regressed: {v['regressed']}, flat: {v['flat']}")
        print(f"    Compliance change: {v['compliance_delta']:+.1f}%")
    print()

    total_improved = sum(v['improved'] for v in verdicts)
    total_regressed = sum(v['regressed'] for v in verdicts)
    total_flat = sum(v['flat'] for v in verdicts)
    avg_compliance_delta = sum(v['compliance_delta'] for v in verdicts) / len(verdicts) if verdicts else 0

    print(f"  Across all users:")
    print(f"    Total habit improvements: {total_improved}")
    print(f"    Total habit regressions:  {total_regressed}")
    print(f"    Total habits flat:        {total_flat}")
    print(f"    Average compliance Δ:     {avg_compliance_delta:+.1f}%")

    if avg_compliance_delta > 3 and total_improved > total_regressed:
        print(f"\n  🟢 THE APP IS HELPING USERS IMPROVE.")
    elif avg_compliance_delta > -3 and total_improved >= total_regressed:
        print(f"\n  🟡 MIXED RESULTS — some improvement, but not transformative.")
    else:
        print(f"\n  🔴 THE APP HAS NOT DRIVEN MEANINGFUL IMPROVEMENT.")
        print(f"     Users are essentially at the same level or worse than when they started.")


if __name__ == "__main__":
    main()
