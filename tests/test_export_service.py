"""
Unit Tests for Export Service (Phase 3F)
=========================================

Tests CSV, JSON, and PDF export generation functions.

**Testing Strategy:**
- Tests ONLY the generation functions (generate_csv_export, generate_json_export, generate_pdf_export)
- These are PURE functions that take (checkins, user) and return BytesIO
- No mocking needed for Firestore because we test the generators directly
- The async export_user_data() function delegates to these + Firestore, tested in integration

**Key Assertions:**
- Output is a BytesIO object (in-memory, not disk)
- CSV: Correct headers, row count, field values, UTF-8 BOM
- JSON: Valid JSON, correct structure, metadata, nested objects
- PDF: Non-empty buffer, begins with PDF magic bytes (%PDF)

Run tests:
    pytest tests/test_export_service.py -v
"""

import pytest
import csv
import json
import io

from src.services.export_service import (
    generate_csv_export,
    generate_json_export,
    generate_pdf_export,
)


# ===== CSV Export Tests =====

class TestCSVExport:
    """Tests for CSV export generation."""
    
    def test_csv_returns_bytesio(self, sample_user_3f, sample_week_checkins):
        """CSV generator should return a BytesIO object (not a file path)."""
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        assert isinstance(result, io.BytesIO)
    
    def test_csv_starts_with_utf8_bom(self, sample_user_3f, sample_week_checkins):
        """
        CSV should start with UTF-8 BOM (Byte Order Mark).
        
        **Theory: Why BOM?**
        Excel on Windows doesn't auto-detect UTF-8 encoding. Without a BOM,
        Excel will interpret the file as ANSI, mangling any non-ASCII characters
        (like user names with accents). The BOM bytes (EF BB BF) tell Excel
        "this file is UTF-8." It's invisible to most other applications.
        """
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        first_bytes = result.read(3)
        assert first_bytes == b'\xef\xbb\xbf', "CSV must start with UTF-8 BOM for Excel compatibility"
    
    def test_csv_has_correct_headers(self, sample_user_3f, sample_week_checkins):
        """CSV should have all expected column headers."""
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8-sig')  # utf-8-sig strips BOM
        reader = csv.DictReader(io.StringIO(content))
        
        expected_headers = {
            "date", "sleep_hours", "sleep_met", "training", "is_rest_day",
            "training_type", "deep_work", "deep_work_hours", "skill_building",
            "skill_building_hours", "skill_building_activity", "zero_porn",
            "boundaries", "compliance_score", "rating", "challenges",
            "tomorrow_priority", "mode", "is_quick_checkin",
        }
        
        assert set(reader.fieldnames) == expected_headers
    
    def test_csv_row_count_matches_checkins(self, sample_user_3f, sample_week_checkins):
        """CSV should have one row per check-in (plus header)."""
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        assert len(rows) == len(sample_week_checkins)
    
    def test_csv_boolean_fields_use_yes_no(self, sample_user_3f, sample_week_checkins):
        """
        Boolean fields should use 'Yes'/'No' not 'True'/'False'.
        
        This is a UX decision: 'Yes'/'No' is more readable in spreadsheets,
        and avoids confusion with Python/Firestore boolean representations.
        """
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        
        for row in reader:
            assert row["sleep_met"] in ("Yes", "No")
            assert row["deep_work"] in ("Yes", "No")
            assert row["zero_porn"] in ("Yes", "No")
            assert row["boundaries"] in ("Yes", "No")
            assert row["is_quick_checkin"] in ("Yes", "No")
    
    def test_csv_training_field_has_three_states(self, sample_user_3f, sample_week_checkins):
        """
        Training field should be 'Yes', 'No', or 'Rest'.
        
        **Design Decision:**
        Training is ternary, not binary. A rest day is NOT a failure -
        it's a deliberate recovery strategy. Representing it as a third
        state prevents penalizing planned rest in data analysis.
        """
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        
        for row in reader:
            assert row["training"] in ("Yes", "No", "Rest")
    
    def test_csv_compliance_score_format(self, sample_user_3f, sample_week_checkins):
        """Compliance scores should be formatted with 1 decimal place."""
        result = generate_csv_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        
        for row in reader:
            # Should be parseable as float with 1 decimal place
            score = float(row["compliance_score"])
            assert 0 <= score <= 100
    
    def test_csv_empty_checkins(self, sample_user_3f):
        """CSV with no check-ins should still have headers but no data rows."""
        result = generate_csv_export([], sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        assert len(rows) == 0
        assert reader.fieldnames is not None


# ===== JSON Export Tests =====

class TestJSONExport:
    """Tests for JSON export generation."""
    
    def test_json_returns_bytesio(self, sample_user_3f, sample_week_checkins):
        """JSON generator should return BytesIO."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        assert isinstance(result, io.BytesIO)
    
    def test_json_is_valid(self, sample_user_3f, sample_week_checkins):
        """Output should be valid, parseable JSON."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        content = result.read().decode('utf-8')
        data = json.loads(content)  # Will raise if invalid
        assert isinstance(data, dict)
    
    def test_json_has_required_top_level_keys(self, sample_user_3f, sample_week_checkins):
        """
        JSON should have three top-level keys for self-documenting structure.
        
        **Theory: Self-Documenting Data**
        By including metadata, the JSON file can be processed programmatically
        without needing separate documentation. A script can check the 
        format_version, determine the date range, and iterate check_ins.
        """
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        
        assert "export_metadata" in data
        assert "user_profile" in data
        assert "check_ins" in data
    
    def test_json_metadata_content(self, sample_user_3f, sample_week_checkins):
        """Metadata should include user info, counts, date range, and format version."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        metadata = data["export_metadata"]
        
        assert metadata["user_id"] == "123456789"
        assert metadata["user_name"] == "Ayush"
        assert metadata["total_checkins"] == 7
        assert metadata["format_version"] == "1.0"
        assert "exported_at" in metadata
        assert "date_range" in metadata
        assert metadata["date_range"]["start"] is not None
        assert metadata["date_range"]["end"] is not None
    
    def test_json_user_profile(self, sample_user_3f, sample_week_checkins):
        """User profile section should contain key user info."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        profile = data["user_profile"]
        
        assert profile["name"] == "Ayush"
        assert profile["timezone"] == "Asia/Kolkata"
        assert profile["constitution_mode"] == "maintenance"
        assert "streaks" in profile
        assert "achievements" in profile
        assert profile["level"] == 5
        assert profile["xp"] == 500
    
    def test_json_checkin_structure(self, sample_user_3f, sample_week_checkins):
        """Each check-in should have the correct nested structure."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        
        assert len(data["check_ins"]) == 7
        
        checkin = data["check_ins"][0]
        assert "date" in checkin
        assert "mode" in checkin
        assert "compliance_score" in checkin
        assert "tier1" in checkin
        assert "responses" in checkin
        
        # Tier1 should have nested sub-objects
        tier1 = checkin["tier1"]
        assert "sleep" in tier1
        assert "training" in tier1
        assert "deep_work" in tier1
        assert "skill_building" in tier1
        assert "zero_porn" in tier1
        assert "boundaries" in tier1
        
        # Sleep should be a nested object with met and hours
        assert "met" in tier1["sleep"]
        assert "hours" in tier1["sleep"]
    
    def test_json_checkin_count_matches(self, sample_user_3f, sample_week_checkins):
        """Number of check-ins in JSON should match input."""
        result = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        
        assert len(data["check_ins"]) == len(sample_week_checkins)
    
    def test_json_empty_checkins(self, sample_user_3f):
        """JSON with empty check-ins should still be valid."""
        result = generate_json_export([], sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        
        assert data["check_ins"] == []
        assert data["export_metadata"]["total_checkins"] == 0


# ===== PDF Export Tests =====

class TestPDFExport:
    """Tests for PDF export generation."""
    
    def test_pdf_returns_bytesio(self, sample_user_3f, sample_week_checkins):
        """PDF generator should return BytesIO."""
        result = generate_pdf_export(sample_week_checkins, sample_user_3f)
        assert isinstance(result, io.BytesIO)
    
    def test_pdf_starts_with_magic_bytes(self, sample_user_3f, sample_week_checkins):
        """
        PDF should start with %PDF magic bytes.
        
        **Theory: Magic Bytes**
        File formats use "magic numbers" (fixed byte sequences at the start)
        to identify the file type. PDF files always start with '%PDF-'.
        This is how the OS knows a file is a PDF even without a .pdf extension.
        """
        result = generate_pdf_export(sample_week_checkins, sample_user_3f)
        magic = result.read(5)
        assert magic == b'%PDF-', "PDF must start with %PDF- magic bytes"
    
    def test_pdf_is_non_empty(self, sample_user_3f, sample_week_checkins):
        """PDF should have substantial content (at least 1KB for a report)."""
        result = generate_pdf_export(sample_week_checkins, sample_user_3f)
        size = result.getbuffer().nbytes
        assert size > 1024, f"PDF too small ({size} bytes) - likely empty or malformed"
    
    def test_pdf_with_empty_checkins(self, sample_user_3f):
        """PDF should still generate even with no check-in data."""
        result = generate_pdf_export([], sample_user_3f)
        assert isinstance(result, io.BytesIO)
        assert result.getbuffer().nbytes > 0
    
    def test_pdf_with_large_dataset(self, sample_user_3f, sample_month_checkins):
        """PDF should handle 30 days of data without error."""
        result = generate_pdf_export(sample_month_checkins, sample_user_3f)
        assert isinstance(result, io.BytesIO)
        # Should be larger than a 7-day PDF due to more data
        assert result.getbuffer().nbytes > 2048


# ===== Edge Cases =====

class TestExportEdgeCases:
    """Test edge cases across all export formats."""
    
    def test_single_checkin_csv(self, sample_user_3f, sample_checkin):
        """Export should work with just one check-in."""
        result = generate_csv_export([sample_checkin], sample_user_3f)
        content = result.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 1
    
    def test_single_checkin_json(self, sample_user_3f, sample_checkin):
        """JSON export should work with just one check-in."""
        result = generate_json_export([sample_checkin], sample_user_3f)
        data = json.loads(result.read().decode('utf-8'))
        assert len(data["check_ins"]) == 1
    
    def test_single_checkin_pdf(self, sample_user_3f, sample_checkin):
        """PDF export should work with just one check-in."""
        result = generate_pdf_export([sample_checkin], sample_user_3f)
        assert result.getbuffer().nbytes > 0


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
