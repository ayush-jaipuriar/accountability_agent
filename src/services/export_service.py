"""
Export Service - CSV, JSON, PDF Data Export
============================================

Phase 3F: Allows users to export all their check-in data in multiple formats.

**Architecture Pattern: Strategy Pattern**
- Single entry point (export_data) delegates to format-specific functions
- Each format (CSV, JSON, PDF) is an isolated function
- Easy to add new formats (e.g., Excel) without modifying existing code

**Supported Formats:**
1. CSV  - Machine-readable, Excel/Google Sheets compatible
2. JSON - Complete data with nested structures, developer-friendly
3. PDF  - Human-readable formatted report with summary statistics

**File Delivery:**
- Files are generated in memory (BytesIO) to avoid disk I/O on Cloud Run
- Sent via Telegram's document upload API
- Files are ephemeral (not stored in Cloud Storage)

**Why No pandas?**
- CSV module from stdlib is sufficient for flat tabular data
- Avoids a heavy dependency (~30MB) for a simple export
- Keeps Docker image small and deploy times fast

**Cost: $0.00** (all open-source libraries, no API calls)
"""

import csv
import json
import io
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.models.schemas import DailyCheckIn, User
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


# ===== CSV Export =====

def generate_csv_export(checkins: List[DailyCheckIn], user: User) -> io.BytesIO:
    """
    Generate CSV export of all check-in data.
    
    **CSV Structure:**
    One row per check-in with columns for all Tier 1 items,
    compliance score, responses, and metadata.
    
    **Why BytesIO?**
    Cloud Run is stateless - no persistent filesystem. BytesIO keeps
    the file in memory, which is passed directly to Telegram's API.
    
    Args:
        checkins: List of DailyCheckIn objects (sorted by date)
        user: User profile for metadata
        
    Returns:
        BytesIO buffer containing CSV data (UTF-8 encoded with BOM for Excel)
    """
    # Create in-memory buffer
    output = io.StringIO()
    
    # Define CSV columns - these map directly to the DailyCheckIn and 
    # Tier1NonNegotiables model fields
    fieldnames = [
        "date",
        "sleep_hours",
        "sleep_met",
        "training",
        "is_rest_day",
        "training_type",
        "deep_work",
        "deep_work_hours",
        "skill_building",
        "skill_building_hours",
        "skill_building_activity",
        "zero_porn",
        "boundaries",
        "compliance_score",
        "rating",
        "challenges",
        "tomorrow_priority",
        "mode",
        "is_quick_checkin",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for checkin in checkins:
        t1 = checkin.tier1_non_negotiables
        # For quick check-ins, responses may use defaults
        responses = checkin.responses
        
        writer.writerow({
            "date": checkin.date,
            "sleep_hours": t1.sleep_hours or "",
            "sleep_met": "Yes" if t1.sleep else "No",
            "training": "Yes" if t1.training else ("Rest" if t1.is_rest_day else "No"),
            "is_rest_day": "Yes" if t1.is_rest_day else "No",
            "training_type": t1.training_type or "",
            "deep_work": "Yes" if t1.deep_work else "No",
            "deep_work_hours": t1.deep_work_hours or "",
            "skill_building": "Yes" if t1.skill_building else "No",
            "skill_building_hours": t1.skill_building_hours or "",
            "skill_building_activity": t1.skill_building_activity or "",
            "zero_porn": "Yes" if t1.zero_porn else "No",
            "boundaries": "Yes" if t1.boundaries else "No",
            "compliance_score": f"{checkin.compliance_score:.1f}",
            "rating": responses.rating,
            "challenges": responses.challenges,
            "tomorrow_priority": responses.tomorrow_priority,
            "mode": checkin.mode,
            "is_quick_checkin": "Yes" if checkin.is_quick_checkin else "No",
        })
    
    # Convert to bytes with UTF-8 BOM for Excel compatibility
    # BOM (Byte Order Mark) tells Excel to interpret the file as UTF-8
    csv_content = output.getvalue()
    byte_buffer = io.BytesIO()
    byte_buffer.write(b'\xef\xbb\xbf')  # UTF-8 BOM
    byte_buffer.write(csv_content.encode('utf-8'))
    byte_buffer.seek(0)
    
    logger.info(f"📊 CSV export generated: {len(checkins)} rows, {byte_buffer.getbuffer().nbytes} bytes")
    return byte_buffer


# ===== JSON Export =====

def generate_json_export(checkins: List[DailyCheckIn], user: User) -> io.BytesIO:
    """
    Generate JSON export with complete nested data structures.
    
    **JSON Structure:**
    {
        "export_metadata": { ... },
        "user_profile": { ... },
        "check_ins": [ { date, tier1: {...}, responses: {...}, ... } ]
    }
    
    **Why include metadata?**
    JSON exports are often consumed by scripts or APIs. Including
    metadata (export date, total count, date range) makes the file
    self-documenting and easier to process programmatically.
    
    Args:
        checkins: List of DailyCheckIn objects
        user: User profile
        
    Returns:
        BytesIO buffer containing formatted JSON
    """
    # Build export data structure
    export_data = {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "user_id": user.user_id,
            "user_name": user.name,
            "total_checkins": len(checkins),
            "date_range": {
                "start": checkins[-1].date if checkins else None,
                "end": checkins[0].date if checkins else None,
            },
            "format_version": "1.0",
        },
        "user_profile": {
            "name": user.name,
            "timezone": user.timezone,
            "constitution_mode": user.constitution_mode,
            "career_mode": user.career_mode,
            "streaks": {
                "current": user.streaks.current_streak,
                "longest": user.streaks.longest_streak,
                "total_checkins": user.streaks.total_checkins,
            },
            "achievements": user.achievements,
            "level": user.level,
            "xp": user.xp,
        },
        "check_ins": [],
    }
    
    for checkin in checkins:
        t1 = checkin.tier1_non_negotiables
        responses = checkin.responses
        
        checkin_data = {
            "date": checkin.date,
            "mode": checkin.mode,
            "compliance_score": checkin.compliance_score,
            "is_quick_checkin": checkin.is_quick_checkin,
            "completed_at": checkin.completed_at.isoformat() if checkin.completed_at else None,
            "duration_seconds": checkin.duration_seconds,
            "tier1": {
                "sleep": {
                    "met": t1.sleep,
                    "hours": t1.sleep_hours,
                },
                "training": {
                    "completed": t1.training,
                    "is_rest_day": t1.is_rest_day,
                    "type": t1.training_type,
                },
                "deep_work": {
                    "completed": t1.deep_work,
                    "hours": t1.deep_work_hours,
                },
                "skill_building": {
                    "completed": t1.skill_building,
                    "hours": t1.skill_building_hours,
                    "activity": t1.skill_building_activity,
                },
                "zero_porn": t1.zero_porn,
                "boundaries": t1.boundaries,
            },
            "responses": {
                "challenges": responses.challenges,
                "rating": responses.rating,
                "rating_reason": responses.rating_reason,
                "tomorrow_priority": responses.tomorrow_priority,
                "tomorrow_obstacle": responses.tomorrow_obstacle,
            },
        }
        export_data["check_ins"].append(checkin_data)
    
    # Serialize to formatted JSON
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
    
    byte_buffer = io.BytesIO()
    byte_buffer.write(json_str.encode('utf-8'))
    byte_buffer.seek(0)
    
    logger.info(f"📊 JSON export generated: {len(checkins)} check-ins, {byte_buffer.getbuffer().nbytes} bytes")
    return byte_buffer


# ===== PDF Export =====

def generate_pdf_export(checkins: List[DailyCheckIn], user: User) -> io.BytesIO:
    """
    Generate formatted PDF report with summary statistics.
    
    **PDF Layout:**
    1. Header: Title + user info + export date
    2. Summary Statistics: Total check-ins, avg compliance, streak info
    3. Tier 1 Performance: Completion rates for each non-negotiable
    4. Month-by-Month Breakdown: Table with monthly averages
    5. Recent Check-Ins: Last 14 days detail table
    
    **Why ReportLab?**
    - Open source ($0 cost)
    - Pure Python (no system dependencies like wkhtmltopdf)
    - Fine-grained control over layout
    - Works on Cloud Run without extra system packages
    
    Args:
        checkins: List of DailyCheckIn objects
        user: User profile
        
    Returns:
        BytesIO buffer containing PDF data
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    
    byte_buffer = io.BytesIO()
    
    # Create PDF document with A4 page size
    doc = SimpleDocTemplate(
        byte_buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#2C3E50'),
    )
    body_style = styles['Normal']
    
    # Build document elements
    elements = []
    
    # --- Header ---
    elements.append(Paragraph("Constitution Accountability Report", title_style))
    elements.append(Paragraph(
        f"<b>User:</b> {user.name} &nbsp;&nbsp; "
        f"<b>Mode:</b> {user.constitution_mode.title()} &nbsp;&nbsp; "
        f"<b>Exported:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        body_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#BDC3C7')))
    elements.append(Spacer(1, 12))
    
    # --- Summary Statistics ---
    elements.append(Paragraph("Summary Statistics", heading_style))
    
    if checkins:
        from statistics import mean
        compliance_scores = [c.compliance_score for c in checkins]
        avg_compliance = mean(compliance_scores)
        date_range = f"{checkins[-1].date} to {checkins[0].date}"
    else:
        avg_compliance = 0
        date_range = "No data"
    
    summary_data = [
        ["Metric", "Value"],
        ["Total Check-Ins", str(len(checkins))],
        ["Date Range", date_range],
        ["Average Compliance", f"{avg_compliance:.1f}%"],
        ["Current Streak", f"{user.streaks.current_streak} days"],
        ["Longest Streak", f"{user.streaks.longest_streak} days"],
        ["Constitution Mode", user.constitution_mode.title()],
        ["Career Mode", user.career_mode.replace('_', ' ').title()],
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 300])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    
    # --- Tier 1 Performance ---
    if checkins:
        elements.append(Paragraph("Tier 1 Non-Negotiable Performance", heading_style))
        
        total = len(checkins)
        sleep_pct = sum(1 for c in checkins if c.tier1_non_negotiables.sleep) / total * 100
        train_pct = sum(1 for c in checkins if c.tier1_non_negotiables.training) / total * 100
        dw_pct = sum(1 for c in checkins if c.tier1_non_negotiables.deep_work) / total * 100
        sb_pct = sum(1 for c in checkins if c.tier1_non_negotiables.skill_building) / total * 100
        zp_pct = sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn) / total * 100
        bd_pct = sum(1 for c in checkins if c.tier1_non_negotiables.boundaries) / total * 100
        
        # Calculate average sleep hours
        sleep_hours_list = [
            c.tier1_non_negotiables.sleep_hours for c in checkins
            if c.tier1_non_negotiables.sleep_hours is not None
        ]
        avg_sleep = mean(sleep_hours_list) if sleep_hours_list else 0
        
        tier1_data = [
            ["Non-Negotiable", "Completion Rate", "Details"],
            ["Sleep (7+ hrs)", f"{sleep_pct:.0f}%", f"Avg: {avg_sleep:.1f} hrs"],
            ["Training", f"{train_pct:.0f}%", f"{sum(1 for c in checkins if c.tier1_non_negotiables.training)}/{total} days"],
            ["Deep Work (2+ hrs)", f"{dw_pct:.0f}%", f"{sum(1 for c in checkins if c.tier1_non_negotiables.deep_work)}/{total} days"],
            ["Skill Building", f"{sb_pct:.0f}%", f"{sum(1 for c in checkins if c.tier1_non_negotiables.skill_building)}/{total} days"],
            ["Zero Porn", f"{zp_pct:.0f}%", f"{sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn)}/{total} days"],
            ["Boundaries", f"{bd_pct:.0f}%", f"{sum(1 for c in checkins if c.tier1_non_negotiables.boundaries)}/{total} days"],
        ]
        
        tier1_table = Table(tier1_data, colWidths=[150, 120, 180])
        tier1_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(tier1_table)
        elements.append(Spacer(1, 12))
    
    # --- Month-by-Month Breakdown ---
    if checkins:
        elements.append(Paragraph("Monthly Breakdown", heading_style))
        
        # Group check-ins by month
        monthly_data: Dict[str, List[DailyCheckIn]] = {}
        for checkin in checkins:
            month_key = checkin.date[:7]  # "YYYY-MM"
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(checkin)
        
        month_table_data = [["Month", "Check-Ins", "Avg Compliance", "Best Day"]]
        for month_key in sorted(monthly_data.keys()):
            month_checkins = monthly_data[month_key]
            avg = mean([c.compliance_score for c in month_checkins])
            best = max(month_checkins, key=lambda c: c.compliance_score)
            month_table_data.append([
                month_key,
                str(len(month_checkins)),
                f"{avg:.1f}%",
                f"{best.date} ({best.compliance_score:.0f}%)",
            ])
        
        month_table = Table(month_table_data, colWidths=[80, 80, 120, 170])
        month_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8E44AD')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(month_table)
        elements.append(Spacer(1, 12))
    
    # --- Recent Check-Ins (last 14) ---
    if checkins:
        recent = checkins[:14]  # Already sorted newest first
        elements.append(Paragraph(f"Recent Check-Ins (Last {len(recent)} Days)", heading_style))
        
        recent_data = [["Date", "Compliance", "Sleep", "Train", "Deep Work", "Porn-Free", "Rating"]]
        for c in recent:
            t1 = c.tier1_non_negotiables
            recent_data.append([
                c.date,
                f"{c.compliance_score:.0f}%",
                f"{t1.sleep_hours or '-'}h",
                "Y" if t1.training else ("R" if t1.is_rest_day else "N"),
                "Y" if t1.deep_work else "N",
                "Y" if t1.zero_porn else "N",
                str(c.responses.rating),
            ])
        
        recent_table = Table(recent_data, colWidths=[70, 70, 50, 45, 65, 65, 45])
        recent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980B9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(recent_table)
    
    # --- Footer ---
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#BDC3C7')))
    elements.append(Paragraph(
        f"Generated by Constitution Accountability Agent | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=colors.grey)
    ))
    
    # Build PDF
    doc.build(elements)
    byte_buffer.seek(0)
    
    logger.info(f"📊 PDF export generated: {byte_buffer.getbuffer().nbytes} bytes")
    return byte_buffer


# ===== Main Export Function =====

async def export_user_data(
    user_id: str,
    format_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Main entry point for data export.
    
    **Strategy Pattern:**
    This function acts as a dispatcher - it receives the desired format
    and delegates to the appropriate generator function. This makes it
    easy to add new formats without modifying existing code.
    
    Args:
        user_id: User's Telegram ID
        format_type: One of 'csv', 'json', 'pdf'
        
    Returns:
        Dictionary with:
        - buffer: BytesIO with file data
        - filename: Suggested filename
        - mime_type: MIME type for Telegram
        
        None if user not found or no data
    """
    # Fetch user and all check-ins
    user = firestore_service.get_user(user_id)
    if not user:
        logger.warning(f"Export failed: user {user_id} not found")
        return None
    
    checkins = firestore_service.get_all_checkins(user_id)
    if not checkins:
        logger.warning(f"Export failed: no check-ins for user {user_id}")
        return None
    
    # Sort by date ascending for export (oldest first)
    checkins_sorted = sorted(checkins, key=lambda c: c.date)
    
    # Date string for filename
    date_str = datetime.utcnow().strftime("%Y%m%d")
    
    # Dispatch to format-specific generator
    format_map = {
        "csv": {
            "generator": generate_csv_export,
            "filename": f"checkins_{user.name}_{date_str}.csv",
            "mime_type": "text/csv",
        },
        "json": {
            "generator": generate_json_export,
            "filename": f"checkins_{user.name}_{date_str}.json",
            "mime_type": "application/json",
        },
        "pdf": {
            "generator": generate_pdf_export,
            "filename": f"report_{user.name}_{date_str}.pdf",
            "mime_type": "application/pdf",
        },
    }
    
    if format_type not in format_map:
        logger.error(f"Unknown export format: {format_type}")
        return None
    
    fmt = format_map[format_type]
    
    try:
        buffer = fmt["generator"](checkins_sorted, user)
        
        return {
            "buffer": buffer,
            "filename": fmt["filename"],
            "mime_type": fmt["mime_type"],
            "checkin_count": len(checkins_sorted),
        }
    except Exception as e:
        logger.error(f"Export generation failed ({format_type}): {e}", exc_info=True)
        return None
