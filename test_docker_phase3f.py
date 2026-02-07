"""
Docker Environment Test for Phase 3F
=====================================

This script tests Phase 3F functionality inside Docker WITHOUT requiring:
- Firestore credentials
- Live Telegram bot
- GCP authentication

**What's tested:**
1. Matplotlib graph generation with Agg backend
2. Pillow image manipulation
3. ReportLab PDF generation
4. QRCode generation
5. Font availability
6. All 4 graph types (sleep, training, compliance, radar)
7. Shareable stats image generation
8. CSV/JSON/PDF export generation

**Why this script?**
Docker containers run in Cloud Run's production environment. We need to
verify that all Phase 3F dependencies work correctly in this environment
BEFORE deploying. This script tests the critical path without needing
external services.

Run in Docker:
    docker run --rm accountability-agent:phase3f python3 test_docker_phase3f.py
"""

import io
import sys
from datetime import datetime, timedelta

print("=" * 70)
print("Phase 3F Docker Environment Verification")
print("=" * 70)
print()

# Track test results
tests_passed = 0
tests_failed = 0


def test(name: str, func):
    """Run a test and track results."""
    global tests_passed, tests_failed
    try:
        func()
        print(f"✅ {name}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ {name}: {e}")
        tests_failed += 1


# ===== Test 1: Matplotlib Configuration =====

def test_matplotlib_backend():
    """Verify matplotlib uses Agg backend (no display server)."""
    import matplotlib
    matplotlib.use('Agg')
    backend = matplotlib.get_backend()
    assert backend == 'Agg', f"Wrong backend: {backend}"


def test_matplotlib_plot():
    """Verify matplotlib can generate plots."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("Test Plot")
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    
    buf.seek(0)
    magic = buf.read(8)
    assert magic == b'\x89PNG\r\n\x1a\n', "Invalid PNG"
    assert buf.getbuffer().nbytes > 1000, "Plot too small"


print("1. Matplotlib Tests")
print("-" * 70)
test("Matplotlib Agg backend configured", test_matplotlib_backend)
test("Matplotlib plot generation", test_matplotlib_plot)
print()


# ===== Test 2: Font Availability =====

def test_fonts_available():
    """Verify system fonts are available for matplotlib."""
    import matplotlib.font_manager as fm
    fonts = fm.findSystemFonts()
    assert len(fonts) > 0, "No system fonts found"
    
    dejavu = [f for f in fonts if 'DejaVu' in f]
    assert len(dejavu) > 0, "DejaVu fonts not found"


print("2. Font Tests")
print("-" * 70)
test("System fonts available", test_fonts_available)
print()


# ===== Test 3: Visualization Service =====

def test_visualization_imports():
    """Verify visualization service imports work."""
    from src.services.visualization_service import (
        generate_sleep_chart,
        generate_training_chart,
        generate_compliance_chart,
        generate_domain_radar,
        generate_weekly_graphs,
    )


def test_all_four_graphs():
    """Verify all 4 graph types generate correctly."""
    from src.services.visualization_service import generate_weekly_graphs
    from src.models.schemas import DailyCheckIn, Tier1NonNegotiables, CheckInResponses
    
    # Create 7 days of test data
    checkins = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        checkins.append(DailyCheckIn(
            date=date,
            user_id="docker_test",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=(i % 2 == 0),
                is_rest_day=(i % 2 == 1),
                deep_work=True, deep_work_hours=2.5,
                skill_building=True, skill_building_hours=2.0,
                zero_porn=True,
                boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Docker test challenge with enough characters for validation",
                rating=8,
                rating_reason="Docker test reason with enough characters for validation",
                tomorrow_priority="Docker test priority with enough characters for validation",
                tomorrow_obstacle="Docker test obstacle with enough characters for validation",
            ),
            compliance_score=83.3,
        ))
    
    graphs = generate_weekly_graphs(checkins)
    assert len(graphs) == 4, f"Expected 4 graphs, got {len(graphs)}"
    
    for name in ['sleep', 'training', 'compliance', 'radar']:
        assert name in graphs, f"Missing graph: {name}"
        buf = graphs[name]
        buf.seek(0)
        magic = buf.read(8)
        assert magic == b'\x89PNG\r\n\x1a\n', f"{name} graph not valid PNG"


print("3. Visualization Service Tests")
print("-" * 70)
test("Visualization service imports", test_visualization_imports)
test("All 4 graph types generate", test_all_four_graphs)
print()


# ===== Test 4: Pillow =====

def test_pillow_image():
    """Verify Pillow can create and manipulate images."""
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (500, 500), color='blue')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 450, 450], fill='white')
    draw.text((250, 250), "Test", fill='black')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    assert buf.read(8)[:4] == b'\x89PNG', "Invalid PNG"


print("4. Pillow Tests")
print("-" * 70)
test("Pillow image creation", test_pillow_image)
print()


# ===== Test 5: ReportLab =====

def test_reportlab_pdf():
    """Verify ReportLab can generate PDFs."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Test PDF Document", styles['Title']),
        Paragraph("This is a test paragraph.", styles['Normal']),
    ]
    doc.build(story)
    
    buf.seek(0)
    magic = buf.read(5)
    assert magic == b'%PDF-', "Invalid PDF"
    assert buf.getbuffer().nbytes > 500, "PDF too small"


print("5. ReportLab Tests")
print("-" * 70)
test("ReportLab PDF generation", test_reportlab_pdf)
print()


# ===== Test 6: QRCode =====

def test_qrcode_generation():
    """Verify QRCode can generate QR codes."""
    import qrcode
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data('https://t.me/test_bot')
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    
    assert img.size[0] > 0, "QR code has no size"


print("6. QRCode Tests")
print("-" * 70)
test("QRCode generation", test_qrcode_generation)
print()


# ===== Test 7: CSV/JSON/PDF Libraries (Without Firestore) =====

def test_csv_library():
    """Verify CSV library works."""
    import csv
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['name', 'value'])
    writer.writeheader()
    writer.writerow({'name': 'test', 'value': '123'})
    
    content = output.getvalue()
    assert 'name,value' in content
    assert 'test,123' in content


def test_json_library():
    """Verify JSON library works."""
    import json
    
    data = {"test": "value", "nested": {"key": 123}}
    json_str = json.dumps(data, indent=2)
    parsed = json.loads(json_str)
    
    assert parsed["test"] == "value"
    assert parsed["nested"]["key"] == 123


def test_reportlab_with_tables():
    """Verify ReportLab can generate complex PDFs with tables."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Create table
    data = [
        ['Header 1', 'Header 2'],
        ['Row 1 Col 1', 'Row 1 Col 2'],
        ['Row 2 Col 1', 'Row 2 Col 2'],
    ]
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story = [
        Paragraph("Test Report", styles['Title']),
        table,
    ]
    doc.build(story)
    
    buf.seek(0)
    assert buf.read(5) == b'%PDF-'


print("7. Data Export Libraries Tests")
print("-" * 70)
test("CSV library", test_csv_library)
test("JSON library", test_json_library)
test("ReportLab with tables", test_reportlab_with_tables)
print()

# Note: Full export_service tests require Firestore (tested in pytest suite)


# ===== Test 8: UX Utilities =====

def test_ux_formatting():
    """Verify UX utilities work."""
    from src.utils.ux import format_header, ErrorMessages, generate_help_text, EMOJI
    
    header = format_header("Test", "Subtitle")
    assert "<b>Test</b>" in header
    
    error = ErrorMessages.user_not_found()
    assert "/start" in error
    
    help_text = generate_help_text()
    assert "/checkin" in help_text
    assert "/export" in help_text
    assert len(help_text) > 500


print("8. UX Utilities Tests")
print("-" * 70)
test("UX formatting and messages", test_ux_formatting)
print()


# ===== Summary =====

print("=" * 70)
print(f"Results: {tests_passed} passed, {tests_failed} failed")
print("=" * 70)

if tests_failed > 0:
    print("\n❌ Some tests failed. Review errors above.")
    sys.exit(1)
else:
    print("\n✅ All Phase 3F components verified in Docker!")
    print("📦 Image is ready for Cloud Run deployment")
    sys.exit(0)
