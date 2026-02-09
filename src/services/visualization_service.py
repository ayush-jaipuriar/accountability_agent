"""
Visualization Service - Graph Generation for Weekly Reports
=============================================================

Phase 3F: Generates 4 types of graphs for weekly visual reports.

<b>Graph Types:</b>
1. Sleep Trend (Line Chart) - Hours per night with target line
2. Training Frequency (Bar Chart) - Workout/Rest/Missed per day
3. Compliance Scores (Line + Trend) - Scores with linear regression
4. Domain Radar (Polar Chart) - 5-axis balance visualization

<b>Technology Choice: Matplotlib</b>
- Open source ($0 cost)
- Agg backend: Renders to memory without display server (Cloud Run compatible)
- Well-documented, widely used
- Produces publication-quality graphs

<b>Design Philosophy:</b>
- Mobile-first: Graphs designed for phone screens (Telegram)
- High DPI: 150 DPI for crisp text on retina displays
- Consistent color scheme: Green/Red/Blue/Yellow across all charts
- Clean: Minimal gridlines, clear labels, readable at small sizes

<b>Why Not Plotly?</b>
- Plotly generates interactive HTML (useless in Telegram)
- Plotly requires Node.js for static export (heavy dependency)
- Matplotlib is lighter and purpose-built for static images
"""

import io
import logging
import numpy as np
from typing import List, Dict, Tuple

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt

from src.models.schemas import DailyCheckIn

logger = logging.getLogger(__name__)

# ===== Color Palette =====
# Consistent colors across all graphs for visual cohesion
COLORS = {
    'primary': '#2980B9',       # Blue - main data
    'success': '#27AE60',       # Green - targets met
    'danger': '#E74C3C',        # Red - targets missed
    'warning': '#F39C12',       # Yellow/Orange - borderline
    'rest': '#3498DB',          # Light blue - rest days
    'background': '#FAFAFA',    # Light grey background
    'grid': '#ECF0F1',          # Subtle grid
    'text': '#2C3E50',          # Dark text
    'muted': '#95A5A6',         # Muted grey text
    'trend': '#8E44AD',         # Purple - trend lines
}

# ===== Graph Configuration =====
FIGURE_SIZE = (10, 6)  # Width x Height in inches
DPI = 150              # Dots per inch (150 = crisp on mobile)
FONT_SIZE = 11         # Base font size


def _setup_figure(title: str, figsize: Tuple = FIGURE_SIZE) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create a consistently styled figure and axes.
    
    <b>Why a helper?</b>
    Every graph needs the same setup: figure size, background color,
    title style, grid, and spine removal. This DRY helper ensures
    visual consistency across all 4 graph types.
    
    Args:
        title: Graph title
        figsize: Figure dimensions (width, height) in inches
        
    Returns:
        Tuple of (Figure, Axes) ready for plotting
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    ax.set_title(title, fontsize=14, fontweight='bold', color=COLORS['text'], pad=15)
    ax.grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    ax.tick_params(colors=COLORS['text'], labelsize=FONT_SIZE - 1)
    return fig, ax


def _figure_to_bytes(fig: plt.Figure) -> io.BytesIO:
    """
    Convert matplotlib figure to PNG bytes in memory.
    
    <b>Why BytesIO?</b>
    Cloud Run has no persistent filesystem. We render the graph
    to an in-memory buffer that can be sent directly to Telegram's
    photo upload API without touching disk.
    
    Args:
        fig: Matplotlib figure to convert
        
    Returns:
        BytesIO buffer containing PNG image data
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)  # Free memory immediately
    buf.seek(0)
    return buf


# ===== Graph 1: Sleep Trend =====

def generate_sleep_chart(checkins: List[DailyCheckIn]) -> io.BytesIO:
    """
    Generate sleep trend line chart for the week.
    
    <b>Visual Design:</b>
    - Line chart with data points (circle markers)
    - Green horizontal line at 7-hour target
    - Color-coded zones: Green (>=7h), Yellow (6-7h), Red (<6h)
    - Data labels on each point showing exact hours
    - Average line as dashed indicator
    
    <b>Theory: Why Color Zones?</b>
    Color zones provide instant visual feedback. The user doesn't need
    to read numbers - they can instantly see "mostly green = good week"
    or "lots of red = sleep needs attention." This leverages the
    pre-attentive processing of color in visual perception.
    
    Args:
        checkins: List of check-ins (should be 7 days, sorted by date ascending)
        
    Returns:
        BytesIO buffer with PNG image
    """
    fig, ax = _setup_figure("Sleep Trend (Last 7 Days)")
    
    # Extract sleep data
    dates = []
    hours = []
    for c in sorted(checkins, key=lambda x: x.date):
        dates.append(c.date[-5:])  # "MM-DD" format for compact labels
        h = c.tier1_non_negotiables.sleep_hours
        hours.append(h if h is not None else 0)
    
    x = range(len(dates))
    
    # Color-coded zones (background fill)
    ax.axhspan(7, 12, alpha=0.08, color=COLORS['success'], label='Good (≥7h)')
    ax.axhspan(6, 7, alpha=0.08, color=COLORS['warning'], label='Warning (6-7h)')
    ax.axhspan(0, 6, alpha=0.08, color=COLORS['danger'], label='Danger (<6h)')
    
    # Target line
    ax.axhline(y=7, linestyle='--', color=COLORS['success'], alpha=0.7, linewidth=1.5, label='Target: 7h')
    
    # Data line with color-coded markers
    point_colors = []
    for h in hours:
        if h >= 7:
            point_colors.append(COLORS['success'])
        elif h >= 6:
            point_colors.append(COLORS['warning'])
        else:
            point_colors.append(COLORS['danger'])
    
    ax.plot(x, hours, color=COLORS['primary'], linewidth=2.5, zorder=3)
    for xi, hi, color in zip(x, hours, point_colors):
        ax.scatter(xi, hi, color=color, s=80, zorder=4, edgecolors='white', linewidth=1.5)
        ax.annotate(f'{hi:.1f}h', (xi, hi), textcoords="offset points",
                    xytext=(0, 12), ha='center', fontsize=9, fontweight='bold',
                    color=color)
    
    # Average line
    avg_hours = sum(hours) / len(hours) if hours else 0
    ax.axhline(y=avg_hours, linestyle=':', color=COLORS['muted'], alpha=0.8, linewidth=1)
    ax.text(len(x) - 0.5, avg_hours + 0.2, f'Avg: {avg_hours:.1f}h',
            fontsize=9, color=COLORS['muted'], ha='right')
    
    # Labels
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=0)
    ax.set_ylabel('Hours', fontsize=FONT_SIZE, color=COLORS['text'])
    ax.set_ylim(max(0, min(hours) - 1), max(hours) + 1.5)
    ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
    
    plt.tight_layout()
    return _figure_to_bytes(fig)


# ===== Graph 2: Training Frequency =====

def generate_training_chart(checkins: List[DailyCheckIn]) -> io.BytesIO:
    """
    Generate training frequency bar chart.
    
    <b>Visual Design:</b>
    - Bar chart with 3 states: Completed (green), Rest Day (blue), Missed (red)
    - Each bar is full height (binary) with color indicating status
    - Legend explains color coding
    - Training mode indicator shown in subtitle
    
    <b>Theory: Binary vs. Continuous</b>
    Training is inherently binary (did/didn't train), unlike sleep which
    is continuous (hours). Bar charts are the ideal visualization for
    categorical/binary data because each bar represents a discrete
    category (day) with a discrete outcome (trained/rested/skipped).
    
    Args:
        checkins: List of check-ins sorted by date
        
    Returns:
        BytesIO buffer with PNG image
    """
    fig, ax = _setup_figure("Training Frequency (Last 7 Days)")
    
    dates = []
    bar_colors = []
    bar_labels = []
    
    for c in sorted(checkins, key=lambda x: x.date):
        dates.append(c.date[-5:])
        t1 = c.tier1_non_negotiables
        if t1.training:
            bar_colors.append(COLORS['success'])
            bar_labels.append('Completed')
        elif t1.is_rest_day:
            bar_colors.append(COLORS['rest'])
            bar_labels.append('Rest Day')
        else:
            bar_colors.append(COLORS['danger'])
            bar_labels.append('Missed')
    
    x = range(len(dates))
    ax.bar(x, [1] * len(dates), color=bar_colors, width=0.6, edgecolor='white', linewidth=1)
    
    # Add status labels on bars
    for xi, label, _ in zip(x, bar_labels, bar_colors):
        icon = "✓" if label == 'Completed' else ("R" if label == 'Rest Day' else "✗")
        ax.text(xi, 0.5, icon, ha='center', va='center',
                fontsize=16, fontweight='bold', color='white')
    
    # Stats summary
    completed = bar_labels.count('Completed')
    rest = bar_labels.count('Rest Day')
    missed = bar_labels.count('Missed')
    
    stats_text = f"Completed: {completed} | Rest: {rest} | Missed: {missed}"
    ax.text(0.5, 1.08, stats_text, transform=ax.transAxes, ha='center',
            fontsize=10, color=COLORS['text'])
    
    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS['success'], label=f'Completed ({completed})'),
        Patch(facecolor=COLORS['rest'], label=f'Rest Day ({rest})'),
        Patch(facecolor=COLORS['danger'], label=f'Missed ({missed})'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=0)
    ax.set_yticks([])
    ax.set_ylim(0, 1.2)
    
    plt.tight_layout()
    return _figure_to_bytes(fig)


# ===== Graph 3: Compliance Scores =====

def generate_compliance_chart(checkins: List[DailyCheckIn]) -> io.BytesIO:
    """
    Generate compliance score line chart with trend line.
    
    <b>Visual Design:</b>
    - Line chart with data points showing actual scores
    - Linear regression trend line (dashed purple)
    - Average line (dotted grey)
    - Data labels on each point
    - Y-axis 0-100% scale
    
    <b>Theory: Linear Regression Trend</b>
    We use numpy's polyfit(degree=1) to fit a linear regression line
    through the compliance scores. This shows whether compliance is
    trending up (improving) or down (degrading). The slope tells
    the story: positive = good trajectory, negative = needs attention.
    
    The trend line is more useful than raw scores because daily
    fluctuations are noisy. The trend line smooths out noise and
    reveals the underlying direction.
    
    Args:
        checkins: List of check-ins sorted by date
        
    Returns:
        BytesIO buffer with PNG image
    """
    fig, ax = _setup_figure("Compliance Scores (Last 7 Days)")
    
    sorted_checkins = sorted(checkins, key=lambda x: x.date)
    dates = [c.date[-5:] for c in sorted_checkins]
    scores = [c.compliance_score for c in sorted_checkins]
    
    x = np.arange(len(dates))
    
    # Main data line
    ax.plot(x, scores, color=COLORS['primary'], linewidth=2.5, marker='o',
            markersize=8, markeredgecolor='white', markeredgewidth=1.5, zorder=3)
    
    # Data labels
    for xi, score in zip(x, scores):
        color = COLORS['success'] if score >= 80 else (COLORS['warning'] if score >= 60 else COLORS['danger'])
        ax.annotate(f'{score:.0f}%', (xi, score), textcoords="offset points",
                    xytext=(0, 12), ha='center', fontsize=9, fontweight='bold', color=color)
    
    # Linear regression trend line
    if len(scores) >= 3:
        z = np.polyfit(x, scores, 1)  # Degree 1 = linear fit
        p = np.poly1d(z)
        trend_values = p(x)
        ax.plot(x, trend_values, linestyle='--', color=COLORS['trend'],
                alpha=0.7, linewidth=1.5, label=f'Trend ({z[0]:+.1f}%/day)')
    
    # Average line
    avg_score = sum(scores) / len(scores)
    ax.axhline(y=avg_score, linestyle=':', color=COLORS['muted'], alpha=0.7, linewidth=1)
    ax.text(len(x) - 0.5, avg_score + 2, f'Avg: {avg_score:.0f}%',
            fontsize=9, color=COLORS['muted'], ha='right')
    
    # Labels
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=0)
    ax.set_ylabel('Compliance %', fontsize=FONT_SIZE, color=COLORS['text'])
    ax.set_ylim(max(0, min(scores) - 15), min(100, max(scores) + 15))
    ax.legend(loc='upper left', fontsize=9)
    
    plt.tight_layout()
    return _figure_to_bytes(fig)


# ===== Graph 4: Domain Radar Chart =====

def generate_domain_radar(checkins: List[DailyCheckIn]) -> io.BytesIO:
    """
    Generate domain radar chart showing 5-axis life balance.
    
    <b>5 Domains (from Constitution):</b>
    1. Physical: Sleep + Training completion rate
    2. Career: Deep Work + Skill Building completion rate
    3. Mental: Zero Porn + Boundaries (self-control metrics)
    4. Discipline: Overall compliance average
    5. Consistency: Check-in rate (days checked in / total days)
    
    <b>Visual Design:</b>
    - Polar projection with 5 axes (pentagon shape)
    - Filled polygon with transparency showing current balance
    - Scale 0-100 per axis
    - Each axis labeled with domain name and score
    
    <b>Theory: Radar Charts for Multi-Dimensional Assessment</b>
    Radar charts (also called spider/web charts) are ideal for showing
    how a single entity (the user) performs across multiple dimensions.
    The shape of the polygon instantly communicates balance:
    - Pentagon (even) = well-rounded
    - Pointy (uneven) = some areas need attention
    This leverages the Gestalt principle of closure - our brain
    naturally perceives the filled shape as a "profile."
    
    Args:
        checkins: List of check-ins for the period
        
    Returns:
        BytesIO buffer with PNG image
    """
    # Calculate domain scores (0-100 scale)
    total = len(checkins) if checkins else 1
    
    # Physical = (sleep_rate + training_rate) / 2
    sleep_rate = sum(1 for c in checkins if c.tier1_non_negotiables.sleep) / total * 100
    train_rate = sum(1 for c in checkins if c.tier1_non_negotiables.training) / total * 100
    physical = (sleep_rate + train_rate) / 2
    
    # Career = (deep_work_rate + skill_building_rate) / 2
    dw_rate = sum(1 for c in checkins if c.tier1_non_negotiables.deep_work) / total * 100
    sb_rate = sum(1 for c in checkins if c.tier1_non_negotiables.skill_building) / total * 100
    career = (dw_rate + sb_rate) / 2
    
    # Mental = (zero_porn_rate + boundaries_rate) / 2
    zp_rate = sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn) / total * 100
    bd_rate = sum(1 for c in checkins if c.tier1_non_negotiables.boundaries) / total * 100
    mental = (zp_rate + bd_rate) / 2
    
    # Discipline = average compliance score
    discipline = sum(c.compliance_score for c in checkins) / total if checkins else 0
    
    # Consistency = check-in rate (assume 7-day period)
    consistency = min(100, (total / 7) * 100)
    
    # Domain labels and values
    domains = ['Physical', 'Career', 'Mental', 'Discipline', 'Consistency']
    values = [physical, career, mental, discipline, consistency]
    
    # Number of variables
    N = len(domains)
    
    # Compute angle for each axis
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    
    # Close the polygon by repeating the first value
    values_closed = values + [values[0]]
    angles_closed = angles + [angles[0]]
    
    # Create polar plot
    fig, ax = plt.subplots(figsize=(8, 8), dpi=DPI, subplot_kw=dict(projection='polar'))
    fig.patch.set_facecolor(COLORS['background'])
    
    # Draw the polygon
    ax.fill(angles_closed, values_closed, color=COLORS['primary'], alpha=0.2)
    ax.plot(angles_closed, values_closed, color=COLORS['primary'], linewidth=2.5, marker='o',
            markersize=8, markeredgecolor='white', markeredgewidth=1.5)
    
    # Draw reference circles at 25, 50, 75, 100
    for level in [25, 50, 75, 100]:
        ax.plot(angles_closed, [level] * (N + 1), color=COLORS['grid'],
                linewidth=0.5, linestyle='--', alpha=0.5)
    
    # Axis labels with values
    ax.set_xticks(angles)
    labels = [f'{d}\n{v:.0f}%' for d, v in zip(domains, values)]
    ax.set_xticklabels(labels, fontsize=11, fontweight='bold', color=COLORS['text'])
    
    # Scale
    ax.set_ylim(0, 110)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], fontsize=8, color=COLORS['muted'])
    
    # Title
    avg_score = sum(values) / len(values)
    ax.set_title(f"Life Balance Radar\nOverall: {avg_score:.0f}%",
                 fontsize=14, fontweight='bold', color=COLORS['text'], pad=25)
    
    plt.tight_layout()
    return _figure_to_bytes(fig)


# ===== Generate All Graphs =====

def generate_weekly_graphs(checkins: List[DailyCheckIn]) -> Dict[str, io.BytesIO]:
    """
    Generate all 4 weekly report graphs.
    
    <b>Orchestration Function:</b>
    Calls each graph generator and returns a dictionary of buffers.
    If any individual graph fails, we log the error and skip it
    rather than failing the entire report (graceful degradation).
    
    Args:
        checkins: Last 7 days of check-ins
        
    Returns:
        Dictionary mapping graph name to BytesIO buffer:
        {
            'sleep': BytesIO,
            'training': BytesIO,
            'compliance': BytesIO,
            'radar': BytesIO,
        }
    """
    graphs = {}
    
    graph_generators = {
        'sleep': ('Sleep Trend', generate_sleep_chart),
        'training': ('Training Frequency', generate_training_chart),
        'compliance': ('Compliance Scores', generate_compliance_chart),
        'radar': ('Domain Radar', generate_domain_radar),
    }
    
    for name, (display_name, generator) in graph_generators.items():
        try:
            graphs[name] = generator(checkins)
            logger.info(f"📊 Generated {display_name} graph ({graphs[name].getbuffer().nbytes} bytes)")
        except Exception as e:
            logger.error(f"❌ Failed to generate {display_name} graph: {e}", exc_info=True)
    
    logger.info(f"📊 Generated {len(graphs)}/4 weekly graphs")
    return graphs
