# Phase 3: Automated Reports & Analytics Dashboard

**Product Requirements Document & Technical Specification**

---

## Document Information

**Version:** 1.0  
**Date:** February 4, 2026  
**Author:** Constitution Agent Team  
**Status:** Approved for Implementation  
**Estimated Implementation Time:** 10 days  
**Target Cost:** <$0.82/month (Phase 3 only), <$1.50/month (total system)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Product Requirements](#product-requirements)
4. [System Architecture](#system-architecture)
5. [Feature Specifications](#feature-specifications)
6. [Implementation Plan](#implementation-plan)
7. [Data Models](#data-models)
8. [Cost Analysis](#cost-analysis)
9. [Testing Strategy](#testing-strategy)
10. [Success Criteria](#success-criteria)
11. [Risks & Mitigations](#risks--mitigations)
12. [Rollout Plan](#rollout-plan)

---

## Executive Summary

### What We're Building

Phase 3 transforms the accountability agent from a reactive check-in system into a comprehensive analytics platform. We're adding:

1. **Automated Weekly Reports** - AI-generated insights delivered every Sunday with 4 visualizations
2. **Monthly Strategic Reviews** - Deep analysis with goal tracking and trajectory assessment
3. **Interactive Dashboard** - Streamlit web app for exploring historical data
4. **Data Visualizations** - Plotly-powered charts (sleep trends, workouts, compliance, domain radar)
5. **Export Capabilities** - Download reports and data in multiple formats

### Why This Matters

**Phase 2 Limitations:**
- No historical analysis - can see today's data but not trends over time
- No visual feedback - all text-based, hard to spot patterns
- Manual review required - user must remember to review past check-ins
- No goal tracking - can't see progress toward June 2026 targets
- Data locked in Firestore - no easy way to export or analyze

**Phase 3 Benefits:**
- **Insights:** AI analyzes 7-30 days of data and surfaces key trends
- **Visual:** Graphs make patterns obvious (sleep degradation, training consistency)
- **Automated:** Weekly/monthly reports generated without user action
- **Motivating:** See progress visually (streak calendar, compliance trending up)
- **Accessible:** Dashboard provides on-demand access to any historical period

### Success Metrics

**Functional:**
- ✅ Weekly reports auto-generated every Sunday at 9 AM IST
- ✅ Monthly reports on first Sunday of month
- ✅ 4+ graphs render correctly (sleep, workouts, compliance, radar)
- ✅ AI insights reference constitution and specific data points
- ✅ Dashboard loads in <3 seconds, works on mobile

**Performance:**
- ✅ Report generation <30 seconds
- ✅ Graph rendering <2 seconds per chart
- ✅ Dashboard page load <3 seconds
- ✅ Cloud Storage upload <5 seconds

**Cost:**
- ✅ Phase 3 cost <$1/month
- ✅ Total system cost <$2/month
- ✅ Cloud Storage <$0.05/month

**Quality:**
- ✅ Graphs visually clear on both desktop and mobile
- ✅ AI insights actionable (not generic)
- ✅ No missing data points in visualizations
- ✅ Reports formatted consistently

### Timeline

**Week 1 Implementation:**
- Days 1-2: Visualization service + Cloud Storage setup
- Days 3-4: Weekly report generation + AI insights
- Day 5: Monthly report generation

**Week 2 Implementation:**
- Days 1-3: Streamlit dashboard (5 pages)
- Days 4-5: Testing + deployment + documentation

---

## Current State Analysis

### Phase 2 Architecture

```
User → Telegram → Webhook → FastAPI
                               ↓
                         Supervisor Agent
                               ↓
            ┌──────────────────┼──────────────────┐
            ↓                  ↓                   ↓
       CheckIn Agent    Pattern Detection   Intervention Agent
            ↓                  ↓                   ↓
         Firestore ←──────── Firestore ←────── Firestore
            ↓
    AI Feedback (Gemini)
```

### Phase 2 Capabilities

**What Works:**
- Daily check-ins with AI-generated personalized feedback
- Pattern detection (sleep degradation, training abandonment, porn relapse, compliance decline)
- Proactive interventions sent via Telegram
- Scheduled scans every 6 hours
- Multi-agent architecture with Supervisor routing

**Data Collected:**
- Tier 1 non-negotiables (sleep, training, deep work, porn, boundaries)
- Sleep hours (tracked daily)
- Workout completion (tracked daily)
- Compliance scores (0-100%)
- User ratings (1-10)
- Challenges, priorities, obstacles (free text)
- Patterns detected with severity levels
- Interventions sent and their timestamps

### Phase 2 Limitations

**No Historical Analysis:**
```python
# Current: User can see TODAY's check-in result
# Missing: "How has my sleep trended over 4 weeks?"
# Missing: "Am I making progress toward June goals?"
# Missing: "Which patterns recur most often?"
```

**No Visualizations:**
- All feedback is text-based
- Hard to see trends (e.g., "sleep declining" vs seeing graph with downward slope)
- Pattern detection exists but no visual heatmap showing frequency
- Streak is a number but no calendar view showing consecutive days

**No Proactive Summaries:**
- User must manually review past check-ins to assess week/month
- Constitution requires weekly review but user must do it manually
- No automated "State of the Constitution" report

**No Goal Tracking:**
- Constitution has specific goals (₹28-42 LPA by June, 12% bodyfat, ₹5L emergency fund)
- System collects data but doesn't track progress toward these goals
- No trajectory assessment ("at current rate, will you hit June targets?")

**Data Accessibility:**
- All data in Firestore (not easily exportable)
- No way to explore custom date ranges
- Can't download history for external analysis

### What Phase 3 Adds

**Automated Weekly Reports:**
Every Sunday at 9 AM IST, user receives:
- 4 graphs: Sleep trend (7 days), workout frequency, compliance scores, domain radar
- AI-generated insights (3-4 paragraphs analyzing the week)
- Constitution compliance score for week
- Pattern flags (if any detected)
- Next week focus areas

**Automated Monthly Reports:**
First Sunday of month at 9 AM IST, user receives:
- Extended graphs (30 days + month-over-month comparison)
- Goal progress tracking (career, physical, wealth)
- Strategic assessment by AI (5-7 paragraphs)
- Trajectory analysis ("on track for June goals?")
- Recommended adjustments

**Interactive Dashboard:**
Web app at `https://dashboard.constitution-agent.run.app` with:
- Overview page (current stats, recent check-ins)
- Analytics page (custom date ranges, all graphs)
- Goals page (progress charts, milestone timeline)
- Reports archive (past weekly/monthly reports)
- Export page (download data as PDF/CSV)

---

## Product Requirements

### Functional Requirements

#### FR-1: Weekly Report Generation

**Priority:** Must Have

**Description:** System automatically generates a comprehensive weekly report every Sunday at 9 AM IST and delivers it via Telegram.

**Acceptance Criteria:**
- Report triggered by Cloud Scheduler at 9:00 AM IST every Sunday
- Report covers last 7 days (Monday-Sunday)
- Includes 4 graphs: sleep trend, workout frequency, compliance scores, domain radar
- AI generates 3-4 paragraphs of insights referencing specific data
- Graphs uploaded to Cloud Storage and embedded in Telegram message
- Report generation completes in <30 seconds
- If no check-ins in week, gracefully handles with "No data this week" message

**User Story:**
> "As a user, I want to receive a weekly summary every Sunday morning so I can review my progress before planning the next week, without having to manually aggregate my check-in data."

**Constitution Reference:**
- Section III.C: "Weekly AI Deep Dive (Sunday, 60min): AI generates report with compliance score, domain analysis, longitudinal trends (graphs), pattern flags"

---

#### FR-2: Monthly Report Generation

**Priority:** Must Have

**Description:** System automatically generates an extended monthly strategic review on the first Sunday of each month at 9 AM IST.

**Acceptance Criteria:**
- Report triggered on first Sunday of month at 9:00 AM IST
- Report covers last 30 days
- Includes 8 graphs: all weekly graphs + month-over-month comparison, goal progress, pattern heatmap, streak calendar
- AI generates 5-7 paragraphs of strategic insights
- Includes goal progress percentages (career, physical, wealth)
- Provides trajectory assessment ("on track" vs "needs adjustment")
- Recommends specific actions for next month
- Report generation completes in <60 seconds

**User Story:**
> "As a user, I want to receive a comprehensive monthly review on the first Sunday so I can assess whether I'm on track for my June 2026 goals and make strategic adjustments."

**Constitution Reference:**
- Section III.C: "Monthly Review (First Sunday, 2hrs): Strategic assessment, goal progress tracking, constitution effectiveness, life trajectory"

---

#### FR-3: Interactive Dashboard

**Priority:** Should Have

**Description:** Web application providing on-demand access to all historical data with interactive visualizations and export capabilities.

**Acceptance Criteria:**
- Accessible at dedicated URL (authenticated via Telegram user_id)
- 5 pages: Overview, Analytics, Goals, Reports, Export
- Custom date range selection (7 days, 30 days, 90 days, all time, custom)
- All graphs render in <2 seconds
- Mobile-responsive (works on phones)
- Export to PDF and CSV functional
- Dashboard loads in <3 seconds (initial page load)
- Data updates reflect within 1 minute of Firestore write

**User Story:**
> "As a user, I want to explore my historical data interactively so I can analyze specific time periods, compare months, and export data for external analysis."

---

#### FR-4: Data Visualizations

**Priority:** Must Have

**Description:** Generate publication-quality graphs using Plotly showing key metrics and trends.

**Graph Types Required:**

1. **Sleep Trend (Line Chart):**
   - X-axis: Dates
   - Y-axis: Sleep hours (0-12)
   - Target line at 7 hours (constitution minimum)
   - Color: Green if ≥7, yellow if 6-7, red if <6
   
2. **Workout Frequency (Bar Chart):**
   - X-axis: Days of week
   - Y-axis: Workout completed (Yes/No/Rest Day)
   - Target indicator (constitution: 6x/week in optimization, 3-4x in maintenance)
   
3. **Compliance Scores (Line Chart):**
   - X-axis: Dates
   - Y-axis: Compliance % (0-100%)
   - Trend line showing direction
   - Target zone shaded (80-100% for maintenance mode)
   
4. **Domain Radar Chart:**
   - 5 axes: Physical, Career, Mental, Wealth, Relationships
   - Score 0-100 for each domain
   - Filled area showing current balance
   
5. **Pattern Frequency Heatmap (Monthly only):**
   - X-axis: Pattern types
   - Y-axis: Weeks in month
   - Color intensity: Frequency of detection
   
6. **Streak Calendar (Monthly only):**
   - Calendar grid showing last 30-90 days
   - Green squares: check-in completed
   - Gray squares: missed day
   - Streak chains highlighted

**Acceptance Criteria:**
- All graphs render correctly on desktop (1920x1080) and mobile (375x667)
- Graphs include axis labels, titles, legends
- Colors accessible (no red/green only for colorblind users - add patterns)
- Graphs export as PNG (1200x800 resolution)
- No missing data points (gracefully handle gaps)

---

#### FR-5: AI-Generated Insights

**Priority:** Must Have

**Description:** AI analyzes report data and generates actionable, specific insights referencing user's constitution and goals.

**Weekly Insights Requirements:**
- 3-4 paragraphs (200-500 words total)
- Reference specific data points ("sleep averaged 6.2 hours, below 7hr target")
- Identify trends ("workout consistency improved - 6/7 days this week")
- Flag concerns ("compliance dropped to 65% on Thursday, what happened?")
- Connect to constitution ("this aligns with your Optimization Mode targets")
- Suggest next week focus ("prioritize sleep - it's trending down")

**Monthly Insights Requirements:**
- 5-7 paragraphs (400-800 words total)
- Strategic assessment ("you're on track for June career goal")
- Pattern analysis ("sleep degradation pattern appeared 2x this month")
- Goal progress ("LeetCode: 52 problems solved, target was 60 - 87% of goal")
- Trajectory ("at current pace, you'll hit ₹2L/month by July, 1 month behind target")
- Recommendations ("increase job applications from 3/week to 5/week")

**Tone:**
- Coach-like: supportive but firm
- Evidence-based: cite specific data
- Not generic: use user's numbers, not placeholders
- Accountability-focused: call out patterns, don't let things slide
- Future-oriented: connect today's actions to June goals

**Acceptance Criteria:**
- Insights generated using Gemini 2.0 Flash
- Cost <$0.02 per weekly report, <$0.05 per monthly report
- Generation time <10 seconds
- Always references at least 3 specific data points
- Includes at least 1 actionable recommendation

---

### Non-Functional Requirements

#### NFR-1: Performance
- Report generation: <30 seconds (weekly), <60 seconds (monthly)
- Dashboard page load: <3 seconds
- Graph rendering: <2 seconds per chart
- Cloud Storage upload: <5 seconds per image

#### NFR-2: Scalability
- Support 50 users generating reports simultaneously
- Handle 10,000 check-ins per user without performance degradation
- Dashboard supports 100 concurrent users

#### NFR-3: Reliability
- Scheduled reports have 99% success rate (allowed: 1 missed report per 100)
- Graceful handling of missing data (partial week, gaps in check-ins)
- Automatic retry on Cloud Scheduler job failure (up to 3 retries)

#### NFR-4: Cost
- Phase 3 components <$1/month
- Total system (Phase 1+2+3) <$2/month
- Cloud Storage <$0.05/month

#### NFR-5: Maintainability
- All graph generation functions unit tested
- Report templates documented in PHASE3_PROMPTS.md
- Dashboard code modular (separate page files)
- Configuration externalized (no hardcoded values)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Scheduler                          │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │ Weekly Report    │         │ Monthly Report      │      │
│  │ (Sun 9 AM IST)   │         │ (1st Sun 9 AM IST)  │      │
│  └─────────┬────────┘         └──────────┬──────────┘      │
└────────────┼───────────────────────────────┼────────────────┘
             │                               │
             ↓                               ↓
    ┌────────────────────────────────────────────────┐
    │          FastAPI App (Cloud Run)               │
    │  /trigger/weekly-report                        │
    │  /trigger/monthly-report                       │
    └────────────┬───────────────────────────────────┘
                 ↓
    ┌────────────────────────────────────────────────┐
    │         Reporting Agent (LangGraph)            │
    │  - Fetch data from Firestore                   │
    │  - Aggregate metrics                           │
    │  - Generate graphs                             │
    │  - Create AI insights                          │
    └────────────┬───────────────────────────────────┘
                 ↓
         ┌───────┴───────┐
         ↓               ↓
┌──────────────────┐  ┌──────────────────────┐
│ Visualization    │  │  LLM Service         │
│ Service          │  │  (Gemini 2.0 Flash)  │
│ (Plotly)         │  └──────────────────────┘
└──────┬───────────┘
       ↓
┌──────────────────────┐
│  Cloud Storage       │
│  (PNG images)        │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│  Telegram Bot        │
│  (Send report)       │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Streamlit Dashboard (Separate Cloud Run)        │
│  ┌──────────┐  ┌───────────┐  ┌───────┐  ┌─────────┐      │
│  │ Overview │  │ Analytics │  │ Goals │  │ Reports │      │
│  └────┬─────┘  └─────┬─────┘  └───┬───┘  └────┬────┘      │
│       └──────────────┴────────────┴───────────┘            │
│                      ↓                                       │
│               Firestore Service                             │
│               Visualization Service                         │
└─────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                        Reporting Agent                         │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Data Collector │→ │ Report Generator │→ │ AI Insights  │ │
│  │ - Query range  │  │ - Weekly/Monthly │  │ - Generate   │ │
│  │ - Aggregate    │  │ - Build report   │  │   summary    │ │
│  └────────────────┘  └──────────────────┘  └──────────────┘ │
└──────────┬─────────────────────┬──────────────────┬──────────┘
           ↓                     ↓                  ↓
   ┌───────────────┐   ┌──────────────────┐   ┌────────────┐
   │ Firestore     │   │ Visualization    │   │ LLM Service│
   │ Service       │   │ Service          │   │            │
   │ - get_range() │   │ - line_chart()   │   │ - prompt() │
   │ - aggregate() │   │ - bar_chart()    │   │ - generate()│
   └───────────────┘   │ - radar_chart()  │   └────────────┘
                       │ - heatmap()      │
                       │ - calendar()     │
                       └─────────┬────────┘
                                 ↓
                       ┌───────────────────┐
                       │ Cloud Storage     │
                       │ Service           │
                       │ - upload_image()  │
                       │ - get_url()       │
                       └───────────────────┘
```

### Data Flow

**Weekly Report Generation Flow:**

1. **Trigger:** Cloud Scheduler sends POST to `/trigger/weekly-report`
2. **Authenticate:** Verify request is from Cloud Scheduler
3. **Fetch Users:** Get all active users from Firestore
4. **For Each User:**
   - Query last 7 days of check-ins
   - Aggregate metrics (avg sleep, workout count, compliance scores)
   - Generate 4 graphs (sleep, workouts, compliance, radar)
   - Upload graphs to Cloud Storage
   - Generate AI insights using Gemini
   - Format Telegram message with graph URLs
   - Send to user via Telegram
   - Log report metadata to Firestore
5. **Complete:** Return summary (users processed, reports sent, errors)

**Dashboard Data Flow:**

1. **User Access:** Navigate to `https://dashboard.constitution-agent.run.app`
2. **Authenticate:** Telegram login → verify user_id in Firestore
3. **Load Overview:** Fetch latest check-in, current streak, recent patterns
4. **Render Page:** Display stats + recent 7-day graphs
5. **User Interaction:** Select custom date range on Analytics page
6. **Re-query:** Fetch data for selected range, regenerate graphs
7. **Display:** Update page with new visualizations

---

## Feature Specifications

### Feature 1: Weekly Report Generation

**Technical Overview:**

The weekly report system uses a Cloud Scheduler job to trigger report generation every Sunday at 9:00 AM IST. The ReportingAgent aggregates 7 days of check-in data, generates visualizations, and uses Gemini to create contextual insights.

**Key Concepts:**

**1. Date Range Calculation:**
```python
from datetime import datetime, timedelta
import pytz

def get_week_range():
    """Get last 7 days (Monday-Sunday)"""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist)
    
    # Find last Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    sunday = today - timedelta(days=days_since_sunday)
    monday = sunday - timedelta(days=6)
    
    return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')
```

**Why:** Constitution reviews are weekly (Monday-Sunday). Reports generated Sunday morning review the completed week.

**2. Data Aggregation:**
```python
async def aggregate_week(user_id: str, start_date: str, end_date: str):
    """Compute weekly metrics from daily check-ins"""
    checkins = await firestore_service.get_checkins_range(
        user_id, start_date, end_date
    )
    
    return {
        'total_checkins': len(checkins),
        'avg_sleep': mean([c.tier1.sleep_hours for c in checkins]),
        'workout_count': sum([1 for c in checkins if c.tier1.training]),
        'avg_compliance': mean([c.compliance_score for c in checkins]),
        'domain_scores': calculate_domain_scores(checkins),
        'patterns_detected': get_patterns_in_range(user_id, start_date, end_date)
    }
```

**Why:** AI needs aggregated metrics to generate insights ("averaged 6.5 hours sleep" vs showing 7 individual numbers).

**3. Graph Generation:**
```python
import plotly.graph_objects as go

def generate_sleep_trend(checkins: List[CheckIn]) -> go.Figure:
    """Create line chart of sleep hours"""
    dates = [c.date for c in checkins]
    hours = [c.tier1.sleep_hours for c in checkins]
    
    fig = go.Figure()
    
    # Main line
    fig.add_trace(go.Scatter(
        x=dates, y=hours,
        mode='lines+markers',
        name='Sleep Hours',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8)
    ))
    
    # Target line (7 hours)
    fig.add_hline(y=7, line_dash="dash", 
                  annotation_text="Target: 7hrs",
                  line_color="green")
    
    fig.update_layout(
        title="Sleep Trend (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Hours",
        height=400,
        template="plotly_white"
    )
    
    return fig
```

**Why:** Plotly creates interactive, publication-quality graphs. Exports as PNG for Telegram, interactive HTML for dashboard.

**4. AI Insights Generation:**
```python
async def generate_weekly_insights(
    user_id: str,
    week_data: dict,
    constitution: dict
) -> str:
    """Use Gemini to analyze week and generate insights"""
    
    prompt = f"""
You are Ayush's constitution AI coach. Analyze this week's data and provide insights.

**Week Data (Monday-Sunday):**
- Check-ins completed: {week_data['total_checkins']}/7
- Average sleep: {week_data['avg_sleep']:.1f} hours (target: 7+)
- Workouts: {week_data['workout_count']}/7 days (target: 6x in Optimization, 4x in Maintenance)
- Average compliance: {week_data['avg_compliance']:.0f}% (target: 80%+)
- Patterns detected: {', '.join(week_data['patterns_detected']) or 'None'}

**Constitution Context:**
- Current mode: {constitution['mode']}
- Current streak: {constitution['streak']} days
- Recent trends: {constitution['recent_trends']}

**Generate 3-4 paragraphs:**

1. **Overall Assessment:** How was the week? Reference specific numbers.
2. **Wins:** What went well? Celebrate specific achievements.
3. **Areas for Improvement:** What needs attention? Be specific and direct.
4. **Next Week Focus:** Top 1-2 priorities based on data.

**Tone:** Coach-like (supportive but firm), evidence-based, specific (use actual numbers), accountability-focused.
"""
    
    response = await llm_service.generate(prompt, max_tokens=500)
    return response.text
```

**Why:** Generic templates don't work - each week is unique. AI analyzes specific patterns and provides tailored guidance.

**5. Telegram Delivery:**
```python
async def send_weekly_report(user_id: str, report_data: dict):
    """Send formatted report via Telegram"""
    
    message = f"""
📊 **Weekly Constitution Report**
Week of {report_data['week_start']} to {report_data['week_end']}

**📈 Key Metrics:**
• Check-ins: {report_data['total_checkins']}/7
• Avg Sleep: {report_data['avg_sleep']:.1f} hrs
• Workouts: {report_data['workout_count']}/7 days
• Compliance: {report_data['avg_compliance']:.0f}%
• Streak: {report_data['current_streak']} days 🔥

**🧠 AI Insights:**

{report_data['ai_insights']}

**📊 Visualizations:**
(Graphs attached below)
"""
    
    # Send message
    await telegram_bot.send_message(user_id, message)
    
    # Send graphs as photos
    for graph_url in report_data['graph_urls']:
        await telegram_bot.send_photo(user_id, graph_url)
```

**Why:** Telegram supports rich formatting (markdown) and inline images. Separating text and graphs keeps message readable.

---

### Feature 2: Monthly Report Generation

**What's Different from Weekly:**

1. **Extended Date Range:** 30 days instead of 7
2. **Additional Graphs:** Month-over-month comparison, goal progress, pattern heatmap, streak calendar
3. **Strategic Analysis:** AI provides 5-7 paragraphs focusing on goal trajectory
4. **Goal Progress Tracking:** Calculates progress toward June 2026 targets

**Goal Progress Calculation:**

```python
def calculate_goal_progress(user_id: str, month_data: dict) -> dict:
    """Track progress toward constitution goals"""
    
    # Career Goal: ₹28-42 LPA by June 2026
    career = {
        'target_salary': 28_00_000,  # ₹28 LPA minimum
        'current_salary': month_data['current_salary'],
        'target_date': '2026-06-30',
        'applications_this_month': month_data['job_apps'],
        'applications_target': 20,  # 5/week * 4 weeks
        'interviews_this_month': month_data['interviews']
    }
    
    career['progress_pct'] = (career['applications_this_month'] / 
                              career['applications_target']) * 100
    
    # Physical Goal: 12% bodyfat, visible abs by June 2026
    physical = {
        'target_bodyfat': 12.0,
        'current_bodyfat': month_data.get('bodyfat', None),
        'workout_consistency': (month_data['workout_count'] / 
                                month_data['target_workouts']) * 100,
        'sleep_avg': month_data['avg_sleep'],
        'sleep_target': 7.0
    }
    
    # Wealth Goal: Rebuild ₹5L emergency fund post-surgery
    wealth = {
        'target_fund': 5_00_000,
        'current_fund': month_data.get('emergency_fund', None),
        'monthly_savings': month_data.get('savings_this_month', None),
        'target_date': '2026-08-31'
    }
    
    if wealth['current_fund']:
        wealth['progress_pct'] = (wealth['current_fund'] / 
                                  wealth['target_fund']) * 100
    
    return {
        'career': career,
        'physical': physical,
        'wealth': wealth
    }
```

**Why:** Constitution has specific measurable goals. Monthly reports must track whether you're on pace or falling behind.

**Pattern Heatmap:**

```python
def generate_pattern_heatmap(patterns: List[Pattern], weeks: int = 4) -> go.Figure:
    """Show frequency of each pattern type over weeks"""
    
    pattern_types = ['sleep_degradation', 'training_abandonment', 
                     'porn_relapse', 'compliance_decline', 'ghosting']
    
    # Build matrix: rows=weeks, cols=pattern types
    matrix = [[0] * len(pattern_types) for _ in range(weeks)]
    
    for pattern in patterns:
        week_index = calculate_week_index(pattern.detected_at, weeks)
        pattern_index = pattern_types.index(pattern.type)
        matrix[week_index][pattern_index] += 1
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=pattern_types,
        y=[f'Week {i+1}' for i in range(weeks)],
        colorscale='Reds',
        text=matrix,
        texttemplate='%{text}',
        textfont={"size": 14}
    ))
    
    fig.update_layout(
        title="Pattern Frequency (Last 4 Weeks)",
        xaxis_title="Pattern Type",
        yaxis_title="Week",
        height=400
    )
    
    return fig
```

**Why:** Visual heatmap makes recurring patterns obvious. If "porn_relapse" is red every week, that's a clear signal for intervention.

---

### Feature 3: Interactive Dashboard

**Tech Stack:**
- **Streamlit:** Python framework for building data apps
- **Deployment:** Cloud Run (separate service from main app)
- **Authentication:** Session-based using Telegram user_id

**Why Streamlit:**
- Fast development (100 lines of code = full dashboard)
- Python-native (reuse existing Firestore/Plotly code)
- Reactive (UI updates automatically when data changes)
- Mobile-responsive out of the box

**Dashboard Structure:**

```
dashboard/
├── app.py                 # Main entry point
├── pages/
│   ├── 1_📊_Overview.py   # Current stats page
│   ├── 2_📈_Analytics.py  # Historical trends
│   ├── 3_🎯_Goals.py      # Goal tracking
│   ├── 4_📄_Reports.py    # Past weekly/monthly reports
│   └── 5_💾_Export.py     # Data download
├── components/
│   ├── auth.py            # Telegram login
│   ├── graphs.py          # Reusable graph components
│   └── metrics.py         # Metric cards
└── requirements.txt
```

**Example Page (Overview):**

```python
# pages/1_📊_Overview.py
import streamlit as st
from components.auth import require_auth
from components.graphs import render_sleep_chart, render_domain_radar
from components.metrics import metric_card

# Authenticate
user = require_auth()

st.title("📊 Constitution Dashboard - Overview")

# Top-level metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Current Streak", f"{user.streak} days 🔥", "+2 from last week")
with col2:
    metric_card("This Week", f"{user.week_compliance}%", "Compliance")
with col3:
    metric_card("Sleep Avg", f"{user.avg_sleep:.1f} hrs", "Last 7 days")
with col4:
    metric_card("Workouts", f"{user.workout_count}/7", "This week")

# Recent trend graphs
st.subheader("📈 Last 7 Days")
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(render_sleep_chart(user.id, days=7), use_container_width=True)

with col2:
    st.plotly_chart(render_domain_radar(user.id), use_container_width=True)

# Recent check-ins
st.subheader("📋 Recent Check-Ins")
recent = get_recent_checkins(user.id, limit=5)
for checkin in recent:
    with st.expander(f"{checkin.date} - {checkin.compliance}% compliance"):
        st.write(f"**Sleep:** {checkin.tier1.sleep_hours} hours")
        st.write(f"**Workout:** {'✅' if checkin.tier1.training else '❌'}")
        st.write(f"**Rating:** {checkin.responses.rating}/10")
        st.write(f"**Challenges:** {checkin.responses.challenges}")
```

**Why This Design:**
- Metric cards give instant status at a glance
- Two-column layout fits desktop and mobile
- Expanders keep page clean (expand only what you want to see)
- Recent check-ins provide quick context

**Authentication Flow:**

```python
# components/auth.py
import streamlit as st
from services.firestore_service import firestore_service

def require_auth():
    """Ensure user is authenticated via Telegram"""
    
    # Check session state
    if 'user_id' not in st.session_state:
        st.warning("⚠️ Please authenticate via Telegram")
        
        # Show Telegram login widget
        user_id = st.text_input("Enter your Telegram User ID:")
        
        if st.button("Login"):
            # Verify user exists in Firestore
            user = firestore_service.get_user(user_id)
            if user:
                st.session_state['user_id'] = user_id
                st.session_state['user'] = user
                st.success("✅ Logged in!")
                st.rerun()
            else:
                st.error("❌ User not found. Please complete a check-in first.")
                st.stop()
        else:
            st.stop()
    
    return st.session_state['user']
```

**Why:** Streamlit's session state persists across page changes. Once authenticated, user stays logged in for session.

---

### Feature 4: Data Export

**Export Formats:**

1. **PDF Report:** Full report with graphs embedded
2. **CSV Data:** Raw check-in data for external analysis
3. **JSON:** Complete data dump including metadata

**CSV Export Example:**

```python
def export_to_csv(user_id: str, start_date: str, end_date: str) -> bytes:
    """Export check-ins as CSV"""
    checkins = firestore_service.get_checkins_range(user_id, start_date, end_date)
    
    rows = []
    for c in checkins:
        rows.append({
            'date': c.date,
            'sleep_hours': c.tier1.sleep_hours,
            'training': c.tier1.training,
            'deep_work': c.tier1.deep_work,
            'zero_porn': c.tier1.zero_porn,
            'boundaries': c.tier1.boundaries,
            'compliance_score': c.compliance_score,
            'rating': c.responses.rating,
            'challenges': c.responses.challenges,
            'tomorrow_priority': c.responses.tomorrow_priority
        })
    
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode('utf-8')
```

**PDF Report Generation:**

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf_report(user_id: str, report_data: dict) -> bytes:
    """Create PDF with text + embedded graphs"""
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Weekly Constitution Report")
    
    # Date range
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, 
                 f"{report_data['week_start']} to {report_data['week_end']}")
    
    # Key metrics
    y = height - 120
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Key Metrics:")
    
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(70, y, f"• Check-ins: {report_data['total_checkins']}/7")
    y -= 20
    c.drawString(70, y, f"• Avg Sleep: {report_data['avg_sleep']:.1f} hrs")
    y -= 20
    c.drawString(70, y, f"• Compliance: {report_data['avg_compliance']:.0f}%")
    
    # Embed graphs
    y -= 50
    for graph_path in report_data['graph_paths']:
        c.drawImage(graph_path, 50, y - 250, width=500, height=200)
        y -= 270
        
        if y < 100:  # New page if running out of space
            c.showPage()
            y = height - 50
    
    # AI insights
    c.showPage()
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "AI Insights:")
    
    y -= 30
    c.setFont("Helvetica", 10)
    # Wrap text
    lines = wrap_text(report_data['ai_insights'], 80)
    for line in lines:
        c.drawString(50, y, line)
        y -= 15
    
    c.save()
    buffer.seek(0)
    return buffer.read()
```

**Why:** PDF preserves formatting for sharing/printing. CSV enables external analysis (Excel, Python pandas). JSON allows backup/restore.

---

## Implementation Plan

### Phase 1: Foundation (Days 1-2)

#### Day 1: Visualization Service Setup

**Tasks:**
1. Create `src/services/visualization_service.py`
2. Implement graph generation functions using Plotly
3. Write unit tests for each graph type
4. Configure Cloud Storage bucket

**Deliverables:**
- ✅ `visualization_service.py` with 6 graph functions
- ✅ Unit tests: `tests/test_visualization.py` (20+ tests)
- ✅ Cloud Storage bucket created: `gs://constitution-agent-reports`
- ✅ Sample graphs generated and uploaded

**Learning Concepts:**
- **Plotly Basics:** `go.Figure()`, traces, layouts
- **Graph Types:** Line, bar, radar, heatmap, calendar
- **Cloud Storage API:** Upload, get public URL, set permissions

---

#### Day 2: Cloud Storage & Reporting Agent Base

**Tasks:**
1. Create `src/services/storage_service.py`
2. Implement upload/download/delete functions
3. Create `src/agents/reporting_agent.py` base class
4. Implement data aggregation logic

**Deliverables:**
- ✅ `storage_service.py` functional
- ✅ `reporting_agent.py` with aggregation methods
- ✅ Unit tests for storage operations
- ✅ Data aggregation tested with sample Firestore data

**Learning Concepts:**
- **Cloud Storage SDK:** `google.cloud.storage`
- **Data Aggregation:** Computing averages, counts, trends
- **Date Range Queries:** Firestore `where()` with date filters

---

### Phase 2: Weekly Reports (Days 3-4)

#### Day 3: Weekly Report Generation

**Tasks:**
1. Implement weekly report generation in `reporting_agent.py`
2. Create AI prompt templates for weekly insights
3. Integrate visualization + LLM services
4. Test report generation locally

**Deliverables:**
- ✅ `generate_weekly_report()` function complete
- ✅ Weekly insights prompt in `PHASE3_PROMPTS.md`
- ✅ End-to-end test with sample data
- ✅ Report generation <30 seconds

**Learning Concepts:**
- **Prompt Engineering:** Structuring data for AI analysis
- **Async Operations:** Parallel graph generation + AI insights
- **Error Handling:** Graceful degradation if API fails

---

#### Day 4: Cloud Scheduler + Telegram Delivery

**Tasks:**
1. Add `/trigger/weekly-report` endpoint to `src/main.py`
2. Implement Telegram delivery formatting
3. Create Cloud Scheduler job
4. Test scheduled execution

**Deliverables:**
- ✅ FastAPI endpoint functional
- ✅ Telegram sends formatted report with graphs
- ✅ Cloud Scheduler job created (Sun 9 AM IST)
- ✅ Full integration tested end-to-end

**Learning Concepts:**
- **Cron Syntax:** `0 9 * * 0` (every Sunday 9 AM)
- **Timezone Handling:** IST (Asia/Kolkata) in Cloud Scheduler
- **Telegram Rich Messages:** Markdown formatting, photo attachments

---

### Phase 3: Monthly Reports (Day 5)

#### Day 5: Monthly Report Implementation

**Tasks:**
1. Extend reporting agent for monthly reports
2. Implement additional graphs (heatmap, calendar, goal progress)
3. Create strategic review prompt template
4. Add `/trigger/monthly-report` endpoint
5. Create Cloud Scheduler job (1st Sunday)

**Deliverables:**
- ✅ `generate_monthly_report()` function complete
- ✅ 3 new graph types implemented
- ✅ Goal progress calculation functional
- ✅ Monthly Scheduler job created
- ✅ Full monthly report tested

**Learning Concepts:**
- **Complex Graphs:** Heatmaps, calendar grids
- **Goal Tracking:** Computing progress percentages
- **Strategic AI Prompts:** Long-form analysis (5-7 paragraphs)

---

### Phase 4: Dashboard Foundation (Days 6-7)

#### Day 6: Streamlit App Structure

**Tasks:**
1. Create `dashboard/` directory structure
2. Implement authentication component
3. Build Overview page
4. Test locally

**Deliverables:**
- ✅ Streamlit app runs locally
- ✅ Authentication functional
- ✅ Overview page displays current stats
- ✅ Graphs render correctly

**Learning Concepts:**
- **Streamlit Basics:** `st.title()`, `st.columns()`, `st.plotly_chart()`
- **Session State:** Persisting authentication
- **Layout:** Responsive columns and containers

---

#### Day 7: Analytics & Goals Pages

**Tasks:**
1. Build Analytics page with custom date ranges
2. Build Goals page with progress tracking
3. Implement graph regeneration on date change
4. Test responsiveness on mobile

**Deliverables:**
- ✅ Analytics page functional
- ✅ Goals page displays progress charts
- ✅ Date range selector works
- ✅ Mobile responsiveness verified

**Learning Concepts:**
- **Streamlit Widgets:** `st.date_input()`, `st.selectbox()`
- **Dynamic Updates:** Regenerating graphs on input change
- **Mobile Testing:** Chrome DevTools device simulation

---

### Phase 5: Dashboard Complete (Days 8-9)

#### Day 8: Reports & Export Pages

**Tasks:**
1. Build Reports archive page
2. Implement Export page with PDF/CSV generation
3. Test all download formats
4. Deploy dashboard to Cloud Run

**Deliverables:**
- ✅ Reports page shows past weekly/monthly reports
- ✅ Export generates PDF and CSV correctly
- ✅ Dashboard deployed to Cloud Run
- ✅ URL accessible: `https://dashboard.constitution-agent.run.app`

**Learning Concepts:**
- **File Downloads:** `st.download_button()`
- **Cloud Run Deployment:** Streamlit in containerized environment
- **PDF Generation:** reportlab library

---

#### Day 9: Integration Testing & Polish

**Tasks:**
1. End-to-end testing (trigger reports, view in dashboard)
2. Performance optimization (caching, lazy loading)
3. UI polish (consistent styling, error messages)
4. Documentation

**Deliverables:**
- ✅ All features tested end-to-end
- ✅ Performance <3 sec page load
- ✅ UI polished and consistent
- ✅ `PHASE3_IMPLEMENTATION.md` created

---

### Phase 6: Deployment & Monitoring (Day 10)

#### Day 10: Production Deployment

**Tasks:**
1. Deploy all services to production
2. Configure monitoring and alerts
3. Test with real user data
4. Create rollback plan
5. Update documentation

**Deliverables:**
- ✅ Main app redeployed with report endpoints
- ✅ Dashboard deployed
- ✅ Cloud Scheduler jobs active
- ✅ Monitoring dashboard configured
- ✅ PHASE3_COMPLETE.md` created

---

## Data Models

### Report Data Schemas

```python
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class GraphMetadata(BaseModel):
    """Metadata for generated graph"""
    type: str  # 'line', 'bar', 'radar', 'heatmap', 'calendar'
    title: str
    storage_url: str  # Cloud Storage public URL
    storage_path: str  # Full GCS path
    alt_text: str  # Accessibility description
    width: int
    height: int
    generated_at: datetime

class WeeklyMetrics(BaseModel):
    """Aggregated metrics for week"""
    total_checkins: int  # 0-7
    avg_sleep_hours: float
    avg_deep_work_hours: float
    workout_count: int  # 0-7
    workout_target: int  # Based on mode (6 for optimization, 4 for maintenance)
    avg_compliance_score: float  # 0-100
    domain_scores: Dict[str, float]  # 5 domains, each 0-100
    patterns_detected: List[str]  # Pattern types found this week
    
class MonthlyMetrics(WeeklyMetrics):
    """Extended metrics for monthly report"""
    total_checkins: int  # 0-30
    week_by_week: List[WeeklyMetrics]  # 4 weeks
    month_over_month_comparison: Dict[str, float]  # % change from last month
    goal_progress: Dict[str, any]  # Career, physical, wealth progress
    pattern_frequency: Dict[str, int]  # Count by pattern type
    longest_streak_this_month: int
    
class WeeklyReportData(BaseModel):
    """Complete weekly report"""
    user_id: str
    week_start: str  # YYYY-MM-DD
    week_end: str
    metrics: WeeklyMetrics
    graphs: List[GraphMetadata]
    ai_insights: str  # 200-500 words
    generated_at: datetime
    report_id: str  # Unique identifier
    
class MonthlyReportData(BaseModel):
    """Complete monthly report"""
    user_id: str
    month_start: str
    month_end: str
    metrics: MonthlyMetrics
    graphs: List[GraphMetadata]  # 8 graphs total
    ai_strategic_review: str  # 400-800 words
    goal_progress_summary: Dict[str, any]
    trajectory_assessment: str  # 'on_track', 'needs_adjustment', 'falling_behind'
    recommendations: List[str]  # 3-5 specific action items
    generated_at: datetime
    report_id: str
```

### Firestore Collections

**New Collections:**

```
reports/
  {user_id}/
    weekly/
      {report_id}/  # e.g., "2026-W06" (year-week number)
        - type: "weekly"
        - week_start: "2026-02-03"
        - week_end: "2026-02-09"
        - metrics: {...}
        - graph_urls: [...]
        - ai_insights: "..."
        - generated_at: timestamp
        - sent_at: timestamp
        - sent_successfully: boolean
        
    monthly/
      {report_id}/  # e.g., "2026-02" (year-month)
        - type: "monthly"
        - month_start: "2026-02-01"
        - month_end: "2026-02-29"
        - metrics: {...}
        - graph_urls: [...]
        - ai_strategic_review: "..."
        - goal_progress: {...}
        - generated_at: timestamp
        - sent_at: timestamp
        - sent_successfully: boolean
```

**Why Store Reports:**
- Audit trail (verify reports were generated)
- Dashboard access (Reports archive page)
- Retry logic (resend if Telegram fails)
- Analytics (track which insights correlate with behavior change)

---

## Cost Analysis

### Detailed Cost Breakdown

#### Component Costs (Per Month)

**1. Plotly:**
- Cost: **$0.00** (open source, no licensing)

**2. Cloud Storage:**
- Storage: ~50 images × 200KB = 10MB
- Cost: $0.026/GB × 0.01GB = **$0.0003/month**
- Egress: Minimal (Telegram fetches images)
- Total: **~$0.001/month**

**3. Cloud Scheduler:**
- Existing jobs: 1 (pattern scan)
- New jobs: 2 (weekly report, monthly report)
- Cost: $0.10/job/month × 2 = **$0.20/month**

**4. Streamlit Dashboard (Cloud Run):**
- Assumptions: 30 visits/month, 2 min/visit
- CPU time: 30 × 2 = 60 min = 1 hour
- Memory: 512Mi
- Cost calculation:
  - vCPU: $0.00002400/vCPU-second × 3600 = $0.0864/hour
  - Memory: $0.00000250/GiB-second × 0.5 × 3600 = $0.0045/hour
  - Total per hour: $0.091
  - Monthly: 1 hour × $0.091 = **$0.091/month**
- Add cold starts: ~$0.05/month
- Total: **~$0.15/month**

**5. AI Report Generation (Gemini):**

**Weekly Reports (4x per month):**
- Input tokens: ~500 (prompt + data)
- Output tokens: ~400 (insights)
- Cost per report:
  - Input: 500 × $0.00025/1K = $0.000125
  - Output: 400 × $0.001/1K = $0.0004
  - Total: $0.000525
- Monthly: 4 × $0.000525 = **$0.0021**

**Monthly Reports (1x per month):**
- Input tokens: ~1000 (extended prompt + data)
- Output tokens: ~800 (strategic review)
- Cost per report:
  - Input: 1000 × $0.00025/1K = $0.00025
  - Output: 800 × $0.001/1K = $0.0008
  - Total: $0.00105
- Monthly: 1 × $0.00105 = **$0.00105**

**Total AI costs:** $0.0021 + $0.00105 = **$0.00315/month**

**6. Main App (Cloud Run) - Incremental:**
- Report endpoints add ~10 sec CPU time per report
- Weekly: 4 reports × 10 sec = 40 sec
- Monthly: 1 report × 20 sec = 20 sec
- Total: 60 sec = 1 min
- Cost: Negligible (<$0.01/month)

---

### Phase 3 Total Cost

| Component | Cost/Month |
|-----------|------------|
| Cloud Storage | $0.001 |
| Cloud Scheduler (2 jobs) | $0.20 |
| Dashboard (Cloud Run) | $0.15 |
| AI Generation (Reports) | $0.003 |
| Main App (Incremental) | $0.01 |
| **Phase 3 Total** | **$0.364** |

### Combined System Cost

| Phase | Cost/Month |
|-------|------------|
| Phase 1 (MVP) | $0.15 |
| Phase 2 (AI + Patterns) | $0.17 |
| Phase 3 (Reports + Dashboard) | $0.36 |
| **Total System** | **$0.68/month** |

**Target:** <$2/month  
**Actual:** $0.68/month  
**Under Budget:** ✅ **66% cheaper than target**

---

### Cost Optimization Strategies

**1. Dashboard Caching:**
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_user_data(user_id: str):
    """Cache Firestore queries to reduce reads"""
    return firestore_service.get_user(user_id)
```
**Savings:** Reduces Firestore reads by 80-90%

**2. Lazy Graph Generation:**
```python
# Don't generate graphs on every dashboard page load
# Only generate when user explicitly requests (e.g., clicks "Analytics" page)
if st.button("Generate Fresh Graphs"):
    graphs = generate_all_graphs(user_id)
else:
    graphs = load_cached_graphs(user_id)  # Use last generated
```
**Savings:** Reduces Cloud Run CPU time

**3. Image Compression:**
```python
# Compress PNGs before uploading to Cloud Storage
from PIL import Image

def compress_graph(image_path: str, quality=85):
    img = Image.open(image_path)
    img.save(image_path, optimize=True, quality=quality)
```
**Savings:** Reduces storage costs by ~50%

**4. Scheduled Job Optimization:**
```python
# Batch process multiple users in single job execution
# Instead of: 1 job per user
# Use: 1 job that processes all users
async def weekly_report_job():
    users = get_all_active_users()
    for user in users:
        await generate_weekly_report(user.id)
```
**Savings:** Reduces Cloud Scheduler job count (no additional cost but cleaner architecture)

---

## Testing Strategy

### Unit Tests

**1. Graph Generation Tests** (`tests/test_visualization.py`)

```python
def test_sleep_trend_chart():
    """Verify sleep trend graph generates correctly"""
    checkins = [
        mock_checkin(date='2026-02-03', sleep_hours=7.5),
        mock_checkin(date='2026-02-04', sleep_hours=6.0),
        mock_checkin(date='2026-02-05', sleep_hours=7.0),
    ]
    
    fig = visualization_service.generate_sleep_trend(checkins)
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Line + target line
    assert fig.data[0].x == ['2026-02-03', '2026-02-04', '2026-02-05']
    assert fig.data[0].y == [7.5, 6.0, 7.0]
    
def test_domain_radar_chart():
    """Verify domain radar generates correctly"""
    domain_scores = {
        'physical': 85.0,
        'career': 70.0,
        'mental': 90.0,
        'wealth': 60.0,
        'relationships': 50.0
    }
    
    fig = visualization_service.generate_domain_radar(domain_scores)
    
    assert isinstance(fig, go.Figure)
    assert fig.data[0].r == [85.0, 70.0, 90.0, 60.0, 50.0]

def test_graph_export_to_png():
    """Verify graphs can be exported as PNG"""
    fig = simple_test_figure()
    
    png_bytes = visualization_service.export_to_png(fig, width=1200, height=800)
    
    assert len(png_bytes) > 1000  # Non-empty PNG
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic number
```

**Coverage Target:** 90%+ for visualization service

---

**2. Data Aggregation Tests** (`tests/test_reporting_agent.py`)

```python
def test_weekly_metrics_calculation():
    """Verify weekly metrics computed correctly"""
    checkins = [
        mock_checkin(date='2026-02-03', sleep=7.5, training=True, compliance=100),
        mock_checkin(date='2026-02-04', sleep=6.0, training=True, compliance=80),
        mock_checkin(date='2026-02-05', sleep=7.0, training=False, compliance=80),
        # Missing 4 check-ins
    ]
    
    metrics = reporting_agent.calculate_weekly_metrics(checkins)
    
    assert metrics.total_checkins == 3
    assert metrics.avg_sleep_hours == pytest.approx(6.83, 0.01)
    assert metrics.workout_count == 2
    assert metrics.avg_compliance_score == pytest.approx(86.67, 0.01)

def test_monthly_metrics_with_missing_data():
    """Verify graceful handling of gaps in data"""
    checkins = create_mock_checkins(count=15)  # Only 15/30 days
    
    metrics = reporting_agent.calculate_monthly_metrics(checkins)
    
    assert metrics.total_checkins == 15
    assert metrics.avg_sleep_hours is not None  # Computed despite gaps
    assert len(metrics.week_by_week) == 4  # 4 weeks even with gaps

def test_goal_progress_calculation():
    """Verify goal tracking math"""
    user_data = {
        'job_applications': 18,  # vs target of 20
        'current_salary': 20_00_000,
        'target_salary': 28_00_000
    }
    
    progress = reporting_agent.calculate_goal_progress(user_data)
    
    assert progress['career']['progress_pct'] == 90.0  # 18/20 * 100
```

**Coverage Target:** 85%+ for reporting agent

---

**3. Cloud Storage Tests** (`tests/test_storage_service.py`)

```python
@pytest.mark.integration
def test_upload_and_retrieve_image():
    """Verify Cloud Storage upload/download"""
    test_image_path = 'tests/fixtures/test_graph.png'
    
    # Upload
    url = storage_service.upload_image(
        test_image_path, 
        destination='test/graph.png'
    )
    
    assert url.startswith('https://storage.googleapis.com/')
    
    # Verify accessible
    response = requests.get(url)
    assert response.status_code == 200
    
    # Cleanup
    storage_service.delete_image('test/graph.png')

def test_image_path_construction():
    """Verify correct GCS paths"""
    path = storage_service.build_path(
        user_id='user123',
        report_type='weekly',
        date='2026-02-09',
        graph_type='sleep_trend'
    )
    
    expected = 'users/user123/weekly/2026-02-09_sleep_trend.png'
    assert path == expected
```

---

### Integration Tests

**1. End-to-End Report Generation** (`tests/test_weekly_report_e2e.py`)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_weekly_report_full_flow():
    """Test complete weekly report generation"""
    user_id = 'test_user_123'
    
    # Setup: Create 7 days of check-ins
    await create_test_checkins(user_id, days=7)
    
    # Trigger report generation
    report = await reporting_agent.generate_weekly_report(user_id)
    
    # Verify report structure
    assert report.user_id == user_id
    assert report.metrics.total_checkins == 7
    assert len(report.graphs) == 4  # 4 graphs generated
    assert len(report.ai_insights) > 200  # AI generated insights
    
    # Verify graphs uploaded
    for graph in report.graphs:
        response = requests.get(graph.storage_url)
        assert response.status_code == 200
    
    # Verify report stored in Firestore
    stored = await firestore_service.get_report(user_id, report.report_id)
    assert stored is not None
    
    # Cleanup
    await cleanup_test_data(user_id)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_telegram_delivery():
    """Test report delivery via Telegram"""
    user_id = 'test_user_123'
    report = await reporting_agent.generate_weekly_report(user_id)
    
    # Send via Telegram
    success = await telegram_service.send_weekly_report(user_id, report)
    
    assert success is True
    
    # Verify message was sent (check Telegram API)
    # Note: This requires test Telegram bot and test user
```

**2. Dashboard Page Rendering** (`tests/test_dashboard.py`)

```python
from streamlit.testing.v1 import AppTest

def test_overview_page_renders():
    """Test Overview page loads without errors"""
    app = AppTest.from_file("dashboard/pages/1_📊_Overview.py")
    app.run()
    
    assert not app.exception
    assert "Constitution Dashboard" in app.title[0].value

def test_analytics_page_with_date_range():
    """Test custom date range selection"""
    app = AppTest.from_file("dashboard/pages/2_📈_Analytics.py")
    app.run()
    
    # Select custom date range
    app.date_input[0].set_value([
        datetime(2026, 1, 1),
        datetime(2026, 1, 31)
    ])
    app.run()
    
    # Verify graphs regenerated
    assert len(app.plotly_chart) > 0
```

---

### Manual Testing Checklist

**Weekly Report:**
- [ ] Report generated on schedule (Sunday 9 AM IST)
- [ ] All 4 graphs render correctly
- [ ] Graphs display properly on Telegram mobile app
- [ ] AI insights reference specific data (not generic)
- [ ] Report delivered within 30 seconds
- [ ] Report stored in Firestore
- [ ] Handles missing data gracefully (partial week)

**Monthly Report:**
- [ ] Report generated on first Sunday
- [ ] All 8 graphs render correctly
- [ ] Goal progress percentages accurate
- [ ] Strategic review is detailed (5-7 paragraphs)
- [ ] Trajectory assessment correct ("on track" vs "needs adjustment")
- [ ] Recommendations actionable

**Dashboard:**
- [ ] Authentication works
- [ ] Overview page loads in <3 seconds
- [ ] Custom date ranges work
- [ ] All graphs interactive (hover shows data)
- [ ] Mobile responsive (test on iPhone, Android)
- [ ] Export to PDF works
- [ ] Export to CSV contains correct data

**Performance:**
- [ ] Report generation <30 sec (weekly), <60 sec (monthly)
- [ ] Dashboard <3 sec initial load
- [ ] Graphs render <2 sec each
- [ ] No memory leaks (test with large datasets)

---

### Performance Testing

**Load Test Script:**

```python
import asyncio
import time

async def load_test_weekly_reports(num_users=50):
    """Simulate 50 concurrent weekly report generations"""
    
    user_ids = [f'test_user_{i}' for i in range(num_users)]
    
    start = time.time()
    
    tasks = [
        reporting_agent.generate_weekly_report(uid)
        for uid in user_ids
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end = time.time()
    
    # Analysis
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = num_users - successful
    avg_time = (end - start) / num_users
    
    print(f"✅ Successful: {successful}/{num_users}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Avg time per report: {avg_time:.2f}s")
    print(f"⏱️  Total time: {end - start:.2f}s")
    
    # Assertions
    assert successful >= 0.95 * num_users  # 95% success rate
    assert avg_time < 30  # Under 30 seconds average

# Run
asyncio.run(load_test_weekly_reports(50))
```

---

## Success Criteria

### Functional Criteria

**Must Have (Launch Blockers):**
- ✅ Weekly reports auto-generate every Sunday at 9 AM IST
- ✅ Monthly reports auto-generate on first Sunday at 9 AM IST
- ✅ All 4 core graphs render correctly (sleep, workouts, compliance, radar)
- ✅ AI insights generated and relevant (not generic)
- ✅ Reports delivered via Telegram successfully
- ✅ Dashboard accessible and loads without errors
- ✅ Authentication functional (Telegram user_id verification)

**Should Have (Post-Launch):**
- ⚪ Export to PDF functional
- ⚪ Export to CSV functional
- ⚪ Custom date ranges work on Analytics page
- ⚪ Mobile responsiveness excellent (not just functional)
- ⚪ Reports archive page shows past reports

**Nice to Have (Future):**
- ⚪ Email delivery option (in addition to Telegram)
- ⚪ Shareable report links
- ⚪ Comparison view (compare any two weeks/months)
- ⚪ Annotations on graphs (user can add notes)

---

### Performance Criteria

| Metric | Target | Acceptable | Current |
|--------|--------|------------|---------|
| Weekly report generation | <20s | <30s | TBD |
| Monthly report generation | <40s | <60s | TBD |
| Dashboard initial load | <2s | <3s | TBD |
| Graph rendering (each) | <1s | <2s | TBD |
| Cloud Storage upload | <3s | <5s | TBD |
| AI insights generation | <8s | <10s | TBD |

**Load Targets:**
- Support 50 concurrent weekly reports
- Dashboard handles 100 simultaneous users
- No degradation with 10,000+ historical check-ins

---

### Quality Criteria

**AI Insights:**
- ✅ References at least 3 specific data points
- ✅ Includes at least 1 actionable recommendation
- ✅ Mentions user's current streak
- ✅ Tone appropriate (coach-like, not generic)
- ✅ Length appropriate (200-500 words weekly, 400-800 monthly)

**Visualizations:**
- ✅ All graphs have clear titles and axis labels
- ✅ Colors accessible (not red/green only)
- ✅ Data points clearly visible
- ✅ No missing data (gaps handled gracefully)
- ✅ Mobile-friendly (readable on small screens)

**User Experience:**
- ✅ Reports formatted consistently
- ✅ Error messages clear and actionable
- ✅ Loading states shown (not blank screens)
- ✅ Dashboard intuitive (no training needed)

---

### Cost Criteria

**Hard Limits (Must Not Exceed):**
- ✅ Phase 3 total: <$1/month
- ✅ Combined system (Phase 1+2+3): <$2/month
- ✅ Cloud Storage: <$0.10/month
- ✅ AI generation per report: <$0.02

**Target (Ideal):**
- Phase 3 total: <$0.50/month
- Combined system: <$1/month

**Current Projection:** $0.68/month total system ✅

---

### Reliability Criteria

**Uptime:**
- Dashboard: 99% availability (allowed: ~7 hours downtime/month)
- Report generation success rate: 95% (allowed: 1-2 missed reports/month)

**Error Handling:**
- Graceful degradation if LLM API fails (use fallback template)
- Graceful handling of missing data (partial weeks, gaps)
- Automatic retry on Cloud Storage upload failures
- User-friendly error messages (never show stack traces)

---

## Risks & Mitigations

### Risk 1: Report Generation Timeout

**Risk:** Report generation takes >60 seconds and Cloud Run times out.

**Likelihood:** Medium (complex graphs + AI generation could be slow)

**Impact:** High (users don't receive reports)

**Mitigation:**
1. **Parallel Processing:** Generate 4 graphs simultaneously (async)
2. **Caching:** Cache aggregated metrics (don't recompute on retry)
3. **Timeout Increase:** Set Cloud Run timeout to 120 seconds (from default 60)
4. **Monitoring:** Alert if generation time >45 seconds
5. **Fallback:** If timeout, queue for retry (background job)

**Detection:**
```python
@app.post("/trigger/weekly-report")
async def weekly_report(request: Request):
    try:
        with timeout(90):  # 90 second timeout
            await reporting_agent.generate_weekly_report(user_id)
    except TimeoutError:
        # Queue for retry
        await queue_report_retry(user_id, 'weekly')
        logger.error(f"Report timeout for {user_id}")
```

---

### Risk 2: Cloud Storage Costs Exceed Budget

**Risk:** Storing 100s of graphs per user exceeds $0.10/month target.

**Likelihood:** Low (storage is cheap)

**Impact:** Medium (budget overrun, but only by small amount)

**Mitigation:**
1. **Lifecycle Policy:** Delete graphs >90 days old automatically
2. **Compression:** Compress PNGs to reduce size by 50%
3. **Lazy Generation:** Only generate graphs when explicitly requested (not every dashboard visit)
4. **Monitoring:** Alert if storage >5GB or cost >$0.05/month

**Implementation:**
```python
# Cloud Storage lifecycle policy
lifecycle_rule = {
    "action": {"type": "Delete"},
    "condition": {"age": 90}  # Delete after 90 days
}

bucket.lifecycle_rules = [lifecycle_rule]
bucket.patch()
```

---

### Risk 3: AI Insights Generic or Low Quality

**Risk:** Gemini generates generic feedback that doesn't reference specific data.

**Likelihood:** Medium (prompt engineering is hard)

**Impact:** High (defeats purpose of personalized reports)

**Mitigation:**
1. **Detailed Prompts:** Include specific data in prompt (not just summaries)
2. **Examples:** Provide few-shot examples of good vs bad insights
3. **Post-Processing:** Validate insights contain specific numbers
4. **Human Review:** Manual review of first 10-20 generated reports
5. **Iteration:** Refine prompts based on quality feedback

**Quality Check:**
```python
def validate_insights(insights: str, data: dict) -> bool:
    """Verify insights reference specific data"""
    
    # Check for specific numbers
    has_numbers = any(char.isdigit() for char in insights)
    
    # Check for data points mentioned
    mentions_sleep = str(data['avg_sleep']) in insights
    mentions_compliance = str(int(data['avg_compliance'])) in insights
    
    # Check length
    word_count = len(insights.split())
    
    return has_numbers and (mentions_sleep or mentions_compliance) and word_count >= 150
```

---

### Risk 4: Dashboard Performance Degrades with Large Datasets

**Risk:** Dashboard becomes slow when user has 1000+ check-ins.

**Likelihood:** Medium (will happen eventually as users accumulate history)

**Impact:** Medium (slow UX, but functional)

**Mitigation:**
1. **Pagination:** Limit queries to last 90 days by default
2. **Caching:** Cache Firestore queries for 1 hour
3. **Lazy Loading:** Load graphs only when page visible (not all at once)
4. **Database Indexes:** Create Firestore indexes on date fields
5. **Optimization:** Profile and optimize slow queries

**Caching Implementation:**
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_checkins(user_id: str, days: int = 90):
    """Cached Firestore query"""
    cutoff = datetime.now() - timedelta(days=days)
    return firestore_service.get_checkins_after(user_id, cutoff)
```

---

### Risk 5: Scheduled Jobs Fail Silently

**Risk:** Cloud Scheduler job fails and no reports are generated, user doesn't know.

**Likelihood:** Low (Cloud Scheduler is reliable)

**Impact:** High (missed reports break constitution review routine)

**Mitigation:**
1. **Monitoring:** Cloud Logging alert on job failures
2. **Retry:** Configure 3 automatic retries with exponential backoff
3. **Fallback:** Send simple text report if graph generation fails
4. **User Notification:** Telegram message if report generation fails
5. **Dashboard Indicator:** Show "Report generation in progress" status

**Monitoring Setup:**
```python
# Cloud Logging alert
alert_policy = {
    "display_name": "Weekly Report Job Failures",
    "conditions": [{
        "display_name": "Job failed",
        "condition_threshold": {
            "filter": 'resource.type="cloud_scheduler_job" AND severity="ERROR"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 0,
            "duration": "60s"
        }
    }],
    "notification_channels": [notification_channel_id]
}
```

---

### Risk 6: Telegram Rate Limits

**Risk:** Sending multiple large images hits Telegram API rate limits.

**Likelihood:** Medium (especially with 50+ users)

**Impact:** Medium (some users don't receive graphs)

**Mitigation:**
1. **Batch Sending:** Add delays between users (1-2 sec)
2. **Retry Logic:** Exponential backoff on 429 errors
3. **Image Optimization:** Keep images under 5MB (Telegram limit is 10MB)
4. **Alternative:** Send single image with all 4 graphs combined
5. **Monitoring:** Track rate limit errors

**Rate Limit Handling:**
```python
async def send_with_retry(user_id: str, photo_url: str, max_retries=3):
    """Send photo with exponential backoff on rate limits"""
    for attempt in range(max_retries):
        try:
            await telegram_bot.send_photo(user_id, photo_url)
            return True
        except telegram.error.RetryAfter as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Rate limit exceeded for {user_id}")
                return False
```

---

## Rollout Plan

### Phase 1: Internal Testing (Days 1-2)

**Goal:** Validate all features work end-to-end in production environment.

**Activities:**
1. Deploy to production (main user only)
2. Generate test weekly report (manually trigger)
3. Generate test monthly report
4. Test dashboard with real data
5. Monitor logs for errors

**Success Criteria:**
- All reports generate successfully
- Graphs render correctly on Telegram
- Dashboard accessible and functional
- No errors in Cloud Logging
- Cost tracking confirms <$1/month

**Rollback Plan:**
- If critical bug: disable Cloud Scheduler jobs
- If dashboard broken: revert to previous Cloud Run revision
- Main app (check-ins) continues working regardless

---

### Phase 2: Soft Launch (Week 1)

**Goal:** Run first weekly report cycle in production.

**Activities:**
1. Enable weekly Cloud Scheduler job
2. Monitor Sunday 9 AM report generation
3. Collect user feedback (if any issues)
4. Review AI insights quality
5. Check cost metrics

**Monitoring:**
- Cloud Logging dashboard (real-time errors)
- Cloud Storage usage (ensure <10MB)
- Cloud Run metrics (CPU, memory, request latency)
- Gemini API costs

**Success Criteria:**
- Weekly report sent successfully
- User receives report on time
- Graphs clear and accurate
- AI insights personalized
- Cost within budget

**User Communication:**
> "Starting this Sunday, you'll receive an automated weekly report at 9 AM with graphs and AI insights analyzing your week. Let me know if you notice any issues!"

---

### Phase 3: Full Launch (Week 2-3)

**Goal:** Enable monthly reports and dashboard.

**Activities Week 2:**
1. Monitor second weekly report
2. Enable monthly Cloud Scheduler job
3. Wait for first Sunday of month
4. Monitor monthly report generation
5. Share dashboard URL

**Activities Week 3:**
1. Collect feedback on monthly report
2. Iterate on AI prompts if needed
3. Monitor dashboard usage
4. Optimize performance if needed

**Success Criteria:**
- Monthly report comprehensive and accurate
- Dashboard used at least once
- All graphs render correctly
- Cost still within budget (<$1/month)

**User Communication:**
> "Monthly strategic review is now live! You'll receive it on the first Sunday of each month. Also, check out your dashboard at [URL] to explore historical data anytime."

---

### Phase 4: Monitoring & Optimization (Ongoing)

**Goal:** Ensure system runs reliably and cost-effectively.

**Daily Monitoring:**
- Check Cloud Logging for errors
- Verify scheduled jobs ran successfully
- Monitor cost (daily budget alert if >$0.10/day)

**Weekly Review:**
- Analyze AI insights quality (sample 3-5 reports)
- Check dashboard usage (how many visits?)
- Review performance metrics (any slowdowns?)

**Monthly Review:**
- Total cost analysis (vs budget)
- User feedback collection
- Feature requests prioritization
- Optimization opportunities

**Optimization Checklist:**
- [ ] Compress older images to reduce storage
- [ ] Add more caching to dashboard
- [ ] Refine AI prompts based on quality review
- [ ] Optimize slow Firestore queries
- [ ] Add more graphs if user requests

---

### Rollback Procedures

**If Weekly Reports Fail:**
1. Check Cloud Logging for error
2. If systematic issue: disable Cloud Scheduler job
3. Fix underlying bug
4. Re-enable scheduler
5. Manually trigger missed reports

**If Dashboard Broken:**
1. Check error logs
2. Revert Cloud Run to previous working revision:
   ```bash
   gcloud run services update-traffic dashboard-app \
     --to-revisions=PREVIOUS_REVISION=100
   ```
3. Fix bug in development
4. Redeploy when fixed

**If Costs Spike:**
1. Check which component caused spike (Cloud Logging → Billing)
2. If Cloud Storage: enable aggressive lifecycle policy (delete >30 days)
3. If AI costs: reduce report generation frequency temporarily
4. If Cloud Run: reduce dashboard concurrency limit

**Communication:**
If rollback needed, notify user:
> "Weekly reports temporarily paused due to a technical issue. Working on fix. Check-ins continue working normally."

---

## Appendices

### Appendix A: Prompt Templates

See `PHASE3_PROMPTS.md` for complete AI prompt templates used in weekly and monthly report generation.

---

### Appendix B: Graph Specifications

**Sleep Trend Line Chart:**
- Type: `plotly.graph_objects.Scatter`
- X-axis: Dates (7 for weekly, 30 for monthly)
- Y-axis: Hours (0-12 range)
- Target line: 7 hours (dashed green)
- Colors: Green (≥7), Yellow (6-7), Red (<6)
- Interactive: Hover shows exact hours

**Workout Frequency Bar Chart:**
- Type: `plotly.graph_objects.Bar`
- X-axis: Days of week or dates
- Y-axis: Binary (0=No, 1=Yes, 0.5=Rest Day)
- Colors: Green (Yes), Red (No), Blue (Rest Day)
- Target indicator: Expected frequency based on mode

**Compliance Scores Line Chart:**
- Type: `plotly.graph_objects.Scatter`
- X-axis: Dates
- Y-axis: Percentage (0-100%)
- Trend line: Linear regression showing direction
- Target zone: Shaded area (80-100%)
- Colors: Green (>80%), Yellow (60-80%), Red (<60%)

**Domain Radar Chart:**
- Type: `plotly.graph_objects.Scatterpolar`
- Axes: 5 domains (Physical, Career, Mental, Wealth, Relationships)
- Range: 0-100 for each axis
- Fill: Semi-transparent to show area
- Comparison: Can overlay previous period (dotted line)

**Pattern Frequency Heatmap:**
- Type: `plotly.graph_objects.Heatmap`
- X-axis: Pattern types (5 types)
- Y-axis: Weeks (4 weeks for monthly)
- Colors: White (0) to Dark Red (5+)
- Annotations: Numbers on each cell

**Streak Calendar:**
- Type: Custom (combination of `plotly.graph_objects.Table` or pure HTML/CSS)
- Layout: Calendar grid (7 columns × 4-5 rows)
- Colors: Green (check-in complete), Gray (missed), White (future)
- Highlights: Streak chains with border
- Interactive: Click date to see details

---

### Appendix C: Dashboard Deployment

**Dockerfile for Streamlit:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard code
COPY dashboard/ .
COPY src/ ./src/

# Expose port
EXPOSE 8080

# Set Streamlit config
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Run Streamlit
CMD ["streamlit", "run", "app.py"]
```

**Deploy Command:**

```bash
gcloud run deploy constitution-dashboard \
  --source ./dashboard \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --service-account accountability-agent@accountability-agent.iam.gserviceaccount.com
```

---

### Appendix D: Cost Calculator Spreadsheet

**Monthly Cost Breakdown (Per User):**

| Component | Unit | Quantity | Unit Cost | Monthly Cost |
|-----------|------|----------|-----------|--------------|
| Cloud Scheduler (Weekly) | Job | 1 | $0.10 | $0.10 |
| Cloud Scheduler (Monthly) | Job | 1 | $0.10 | $0.10 |
| Cloud Storage (Images) | GB | 0.01 | $0.026/GB | $0.0003 |
| Dashboard (Cloud Run) | Hour | 1 | $0.091/hour | $0.091 |
| Weekly Report AI | Report | 4 | $0.000525 | $0.0021 |
| Monthly Report AI | Report | 1 | $0.00105 | $0.00105 |
| Main App (Incremental) | - | - | - | $0.01 |
| **Phase 3 Total** | | | | **$0.364** |

**Scaling Analysis:**

If scaling to 100 users:
- Cloud Scheduler: $0.20 (same, shared jobs)
- Cloud Storage: $0.03 (100 × $0.0003)
- Dashboard: $0.15 (shared service)
- AI Reports: $0.32 (100 × $0.0032)
- **Total: $0.70/month for 100 users** ≈ $0.007 per user

**Cost Efficiency:** Phase 3 becomes more cost-efficient at scale due to shared infrastructure.

---

**END OF SPECIFICATION**

---

**Document Version:** 1.0  
**Last Updated:** February 4, 2026  
**Status:** Ready for Implementation  
**Approved By:** Constitution Agent Team  
**Next Steps:** Begin Phase 1 implementation (Visualization service setup)