"""
Integration Tests for Phase 3F
================================

Tests that test full end-to-end flows across multiple services.

**What Makes These Integration Tests?**
Unit tests isolate a single function. Integration tests verify that
multiple components work together correctly. These tests:
1. Cross service boundaries (export → visualization → reporting)
2. Test the full pipeline (data in → processing → output)
3. Use realistic data shapes
4. Mock only external infrastructure (Firestore, Telegram, LLM)

**Theory: The Testing Pyramid**
            /  E2E  \\       ← Few, expensive, slow (real Telegram)
           /  Integ  \\      ← Some, moderate cost (mocked infra)
          /   Unit    \\     ← Many, cheap, fast (pure functions)

We're at the "Integration" level here: testing component interactions
with mocked infrastructure.

Run tests:
    pytest tests/test_phase3f_integration.py -v -m integration
"""

import pytest
import io
import json
import csv
from unittest.mock import patch, AsyncMock

from src.services.export_service import (
    generate_csv_export,
    generate_json_export,
    generate_pdf_export,
    export_user_data,
)
from src.services.visualization_service import generate_weekly_graphs
from src.agents.reporting_agent import (
    _build_report_message,
    _generate_fallback_insights,
    generate_and_send_weekly_report,
    send_weekly_reports_to_all,
)
from src.models.schemas import User


# ===== Integration: Full Export Pipeline =====

@pytest.mark.integration
class TestExportPipeline:
    """
    Integration test: Data → Export Service → Valid output file.
    
    Tests the complete export flow with realistic data.
    """
    
    def test_csv_export_data_integrity(self, sample_user_3f, sample_month_checkins):
        """
        CSV export should preserve all data accurately.
        
        This integration test verifies that data flows correctly from
        DailyCheckIn objects through the CSV serialization pipeline
        and back into readable tabular data with no data loss.
        """
        buffer = generate_csv_export(sample_month_checkins, sample_user_3f)
        content = buffer.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        # Verify row count
        assert len(rows) == 30
        
        # Verify data integrity for first row
        first_checkin = sample_month_checkins[0]
        first_row = rows[0]
        assert first_row["date"] == first_checkin.date
        assert first_row["mode"] == first_checkin.mode
    
    def test_json_export_data_integrity(self, sample_user_3f, sample_month_checkins):
        """JSON export should contain all check-in data with correct nesting."""
        buffer = generate_json_export(sample_month_checkins, sample_user_3f)
        data = json.loads(buffer.read().decode('utf-8'))
        
        # Verify structure completeness
        assert len(data["check_ins"]) == 30
        assert data["export_metadata"]["total_checkins"] == 30
        
        # Verify nested data for first check-in
        first = data["check_ins"][0]
        assert "tier1" in first
        assert "responses" in first
        assert "sleep" in first["tier1"]
        assert "met" in first["tier1"]["sleep"]
        assert "hours" in first["tier1"]["sleep"]
    
    def test_pdf_export_with_large_dataset(self, sample_user_3f, sample_month_checkins):
        """PDF should handle 30 days of data and produce a multi-page document."""
        buffer = generate_pdf_export(sample_month_checkins, sample_user_3f)
        
        # Should be a valid PDF
        buffer.seek(0)
        assert buffer.read(5) == b'%PDF-'
        
        # Should be substantial (ReportLab uses efficient compression)
        size = buffer.getbuffer().nbytes
        assert size > 3000, f"30-day PDF should be substantial ({size} bytes)"
    
    def test_all_export_formats_succeed(self, sample_user_3f, sample_week_checkins):
        """All 3 export formats should succeed with the same data."""
        csv_buf = generate_csv_export(sample_week_checkins, sample_user_3f)
        json_buf = generate_json_export(sample_week_checkins, sample_user_3f)
        pdf_buf = generate_pdf_export(sample_week_checkins, sample_user_3f)
        
        assert csv_buf.getbuffer().nbytes > 0
        assert json_buf.getbuffer().nbytes > 0
        assert pdf_buf.getbuffer().nbytes > 0


# ===== Integration: Export Service with Mocked Firestore =====

@pytest.mark.integration
class TestExportUserData:
    """
    Integration test: export_user_data() with mocked Firestore.
    
    Tests the async entry point that orchestrates Firestore + generation.
    """
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_csv_success(self, mock_fs, sample_user_3f, sample_week_checkins):
        """Full CSV export flow should work end-to-end."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_all_checkins.return_value = sample_week_checkins
        
        result = await export_user_data("123456789", "csv")
        
        assert result is not None
        assert result["filename"].endswith(".csv")
        assert result["mime_type"] == "text/csv"
        assert result["checkin_count"] == 7
        assert isinstance(result["buffer"], io.BytesIO)
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_json_success(self, mock_fs, sample_user_3f, sample_week_checkins):
        """Full JSON export flow should work end-to-end."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_all_checkins.return_value = sample_week_checkins
        
        result = await export_user_data("123456789", "json")
        
        assert result is not None
        assert result["filename"].endswith(".json")
        assert result["mime_type"] == "application/json"
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_pdf_success(self, mock_fs, sample_user_3f, sample_week_checkins):
        """Full PDF export flow should work end-to-end."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_all_checkins.return_value = sample_week_checkins
        
        result = await export_user_data("123456789", "pdf")
        
        assert result is not None
        assert result["filename"].endswith(".pdf")
        assert result["mime_type"] == "application/pdf"
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_user_not_found(self, mock_fs):
        """Export should return None when user doesn't exist."""
        mock_fs.get_user.return_value = None
        
        result = await export_user_data("nonexistent", "csv")
        assert result is None
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_no_checkins(self, mock_fs, sample_user_3f):
        """Export should return None when user has no check-ins."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_all_checkins.return_value = []
        
        result = await export_user_data("123456789", "csv")
        assert result is None
    
    @pytest.mark.asyncio
    @patch('src.services.export_service.firestore_service')
    async def test_export_invalid_format(self, mock_fs, sample_user_3f, sample_week_checkins):
        """Export should return None for unsupported format."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_all_checkins.return_value = sample_week_checkins
        
        result = await export_user_data("123456789", "xlsx")  # Not supported
        assert result is None


# ===== Integration: Visualization + Report Message =====

@pytest.mark.integration
class TestReportPipeline:
    """
    Integration test: Check-ins → Graphs + Insights → Report Message.
    
    Tests that the reporting pipeline produces coherent output when
    all components work together.
    """
    
    def test_graphs_plus_report_message(self, sample_user_3f, sample_week_checkins):
        """Graphs and report message should be generated from same data."""
        # Generate graphs
        graphs = generate_weekly_graphs(sample_week_checkins)
        assert len(graphs) == 4
        
        # Generate report message with fallback insights
        avg_compliance = sum(c.compliance_score for c in sample_week_checkins) / len(sample_week_checkins)
        avg_sleep = sum(
            c.tier1_non_negotiables.sleep_hours
            for c in sample_week_checkins
            if c.tier1_non_negotiables.sleep_hours
        ) / len(sample_week_checkins)
        
        insights = _generate_fallback_insights(sample_week_checkins, avg_compliance, avg_sleep)
        message = _build_report_message(sample_week_checkins, sample_user_3f, insights)
        
        # Message should be coherent
        assert "Weekly Report" in message
        assert "%" in message
        assert len(message) > 100


# ===== Integration: Weekly Report with Mocked Telegram =====

@pytest.mark.integration
class TestWeeklyReportDelivery:
    """
    Integration test: Full weekly report delivery pipeline.
    
    Mocks Firestore (data layer) and Telegram Bot (delivery layer)
    but exercises all intermediate logic (graphs, insights, message).
    """
    
    @pytest.mark.asyncio
    @patch('src.agents.reporting_agent.firestore_service')
    async def test_single_user_report(self, mock_fs, sample_user_3f, sample_week_checkins):
        """
        Full report generation for a single user.
        
        **What's tested:**
        1. Firestore data fetch (mocked)
        2. Graph generation (real matplotlib)
        3. Fallback insights (template-based, since LLM is mocked)
        4. Message building (real)
        5. Telegram delivery (mocked)
        """
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_recent_checkins.return_value = sample_week_checkins
        
        # Mock Telegram bot
        mock_bot = AsyncMock()
        
        # Patch LLM service to return fallback
        with patch('src.agents.reporting_agent.generate_ai_insights') as mock_ai:
            mock_ai.return_value = "Great week! Compliance was strong at 85%."
            
            result = await generate_and_send_weekly_report(
                user_id="123456789",
                project_id="test-project",
                bot=mock_bot,
            )
        
        assert result["status"] == "sent"
        assert result["graphs_sent"] == 4
        
        # Verify Telegram was called
        mock_bot.send_message.assert_called_once()
        assert mock_bot.send_photo.call_count == 4
    
    @pytest.mark.asyncio
    @patch('src.agents.reporting_agent.firestore_service')
    async def test_user_not_found_skips(self, mock_fs):
        """Report should be skipped when user doesn't exist."""
        mock_fs.get_user.return_value = None
        mock_bot = AsyncMock()
        
        result = await generate_and_send_weekly_report(
            user_id="nonexistent",
            project_id="test-project",
            bot=mock_bot,
        )
        
        assert result["status"] == "skipped"
        mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('src.agents.reporting_agent.firestore_service')
    async def test_no_checkins_sends_empty(self, mock_fs, sample_user_3f):
        """Report with no check-ins should send a 'no data' message."""
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_recent_checkins.return_value = []
        
        mock_bot = AsyncMock()
        
        result = await generate_and_send_weekly_report(
            user_id="123456789",
            project_id="test-project",
            bot=mock_bot,
        )
        
        assert result["status"] == "sent_empty"
        mock_bot.send_message.assert_called_once()
        # Should not send any graphs
        mock_bot.send_photo.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('src.agents.reporting_agent.firestore_service')
    async def test_batch_reports(self, mock_fs, sample_user_3f, sample_week_checkins):
        """
        Batch report to all users should process each user.
        
        **Theory: Sequential Processing**
        We process users sequentially (not in parallel) because:
        1. Telegram has rate limits (30 msg/sec)
        2. Graph generation is CPU-intensive
        3. Sequential is more predictable and debuggable
        """
        # Create 3 mock users
        users = []
        for i in range(3):
            users.append(User(
                user_id=str(i),
                telegram_id=i,
                name=f"User{i}",
                timezone="Asia/Kolkata",
            ))
        
        mock_fs.get_all_users.return_value = users
        mock_fs.get_user.return_value = sample_user_3f
        mock_fs.get_recent_checkins.return_value = sample_week_checkins
        
        mock_bot = AsyncMock()
        
        with patch('src.agents.reporting_agent.generate_ai_insights') as mock_ai:
            mock_ai.return_value = "Good week overall."
            
            results = await send_weekly_reports_to_all(
                project_id="test-project",
                bot=mock_bot,
            )
        
        assert results["total_users"] == 3
        assert results["reports_sent"] == 3


# ===== Integration: Export → JSON → Verify Completeness =====

@pytest.mark.integration
class TestExportCompleteness:
    """
    Integration test verifying that exported data is complete.
    
    This tests the end-to-end data integrity: from check-in model
    through the export pipeline to the final output format.
    """
    
    def test_json_export_preserves_all_tier1_fields(self, sample_user_3f, sample_week_checkins):
        """Every Tier 1 field should appear in the JSON export."""
        buffer = generate_json_export(sample_week_checkins, sample_user_3f)
        data = json.loads(buffer.read().decode('utf-8'))
        
        for checkin_data in data["check_ins"]:
            tier1 = checkin_data["tier1"]
            
            # All Tier 1 categories present
            assert "sleep" in tier1
            assert "training" in tier1
            assert "deep_work" in tier1
            assert "skill_building" in tier1
            assert "zero_porn" in tier1
            assert "boundaries" in tier1
            
            # Nested fields correct type
            assert isinstance(tier1["sleep"]["met"], bool)
            assert isinstance(tier1["zero_porn"], bool)
    
    def test_csv_and_json_same_checkin_count(self, sample_user_3f, sample_month_checkins):
        """CSV and JSON exports from same data should have same count."""
        csv_buf = generate_csv_export(sample_month_checkins, sample_user_3f)
        json_buf = generate_json_export(sample_month_checkins, sample_user_3f)
        
        # Count CSV rows
        csv_content = csv_buf.read().decode('utf-8-sig')
        csv_rows = list(csv.DictReader(io.StringIO(csv_content)))
        
        # Count JSON entries
        json_data = json.loads(json_buf.read().decode('utf-8'))
        
        assert len(csv_rows) == len(json_data["check_ins"])
        assert len(csv_rows) == 30


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
