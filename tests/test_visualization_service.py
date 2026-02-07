"""
Unit Tests for Visualization Service (Phase 3F)
=================================================

Tests all 4 graph generators and the orchestration function.

**Testing Strategy:**
- Graph generators are PURE functions: (List[DailyCheckIn]) -> BytesIO
- We verify they produce valid PNG images (magic bytes check)
- We verify they handle edge cases (1 check-in, 0 check-ins)
- We don't assert pixel values (fragile); we assert structure
- matplotlib Agg backend is tested implicitly (no display server needed)

**Theory: Testing Visualizations**
You can't easily unit test "does this graph look good?" But you CAN test:
1. Does it produce a valid image file? (magic bytes)
2. Is the image non-trivially sized? (not empty)
3. Does it handle edge cases gracefully? (no crashes)
4. Does the orchestration correctly aggregate results?

Run tests:
    pytest tests/test_visualization_service.py -v
"""

import pytest
import io
from datetime import datetime, timedelta

from src.services.visualization_service import (
    generate_sleep_chart,
    generate_training_chart,
    generate_compliance_chart,
    generate_domain_radar,
    generate_weekly_graphs,
    _setup_figure,
    _figure_to_bytes,
)
from src.models.schemas import (
    DailyCheckIn,
    Tier1NonNegotiables,
    CheckInResponses,
)


# ===== PNG Validation Helper =====

def is_valid_png(buffer: io.BytesIO) -> bool:
    """
    Check if a BytesIO buffer contains valid PNG data.
    
    **Theory: PNG Magic Bytes**
    PNG files always start with an 8-byte signature:
    89 50 4E 47 0D 0A 1A 0A
    The first byte (0x89) has bit 7 set to detect transmission errors.
    "PNG" in ASCII follows, then DOS and Unix line endings to detect
    text-mode transfer corruption.
    """
    buffer.seek(0)
    magic = buffer.read(8)
    return magic == b'\x89PNG\r\n\x1a\n'


# ===== Sleep Chart Tests =====

class TestSleepChart:
    """Tests for sleep trend line chart."""
    
    def test_returns_bytesio(self, sample_week_checkins):
        """Sleep chart should return BytesIO buffer."""
        result = generate_sleep_chart(sample_week_checkins)
        assert isinstance(result, io.BytesIO)
    
    def test_produces_valid_png(self, sample_week_checkins):
        """Sleep chart should produce a valid PNG image."""
        result = generate_sleep_chart(sample_week_checkins)
        assert is_valid_png(result), "Sleep chart output is not valid PNG"
    
    def test_image_has_reasonable_size(self, sample_week_checkins):
        """Sleep chart should be a substantial image (not empty)."""
        result = generate_sleep_chart(sample_week_checkins)
        size = result.getbuffer().nbytes
        assert size > 10_000, f"Sleep chart too small ({size} bytes)"
    
    def test_handles_single_checkin(self, sample_checkin):
        """Sleep chart should work with a single data point."""
        result = generate_sleep_chart([sample_checkin])
        assert is_valid_png(result)
    
    def test_handles_zero_sleep_hours(self, sample_week_checkins):
        """Chart should handle None/0 sleep hours without crashing."""
        # Modify first checkin to have None sleep hours
        sample_week_checkins[0].tier1_non_negotiables.sleep_hours = None
        result = generate_sleep_chart(sample_week_checkins)
        assert is_valid_png(result)


# ===== Training Chart Tests =====

class TestTrainingChart:
    """Tests for training frequency bar chart."""
    
    def test_returns_bytesio(self, sample_week_checkins):
        result = generate_training_chart(sample_week_checkins)
        assert isinstance(result, io.BytesIO)
    
    def test_produces_valid_png(self, sample_week_checkins):
        result = generate_training_chart(sample_week_checkins)
        assert is_valid_png(result)
    
    def test_handles_all_trained(self):
        """Chart should work when all days have training=True."""
        checkins = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Test challenge for the day with enough characters to pass validation",
                    rating=8,
                    rating_reason="Solid day with good progress made in all areas of constitution",
                    tomorrow_priority="Focus on maintaining consistency across all non-negotiable areas",
                    tomorrow_obstacle="Late evening commitments might interfere with early bedtime goal",
                ),
                compliance_score=100.0,
            ))
        
        result = generate_training_chart(checkins)
        assert is_valid_png(result)
    
    def test_handles_all_rest_days(self):
        """Chart should work when all days are rest days."""
        checkins = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=False, is_rest_day=True,
                    deep_work=True, zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Test challenge for the rest day with enough characters here",
                    rating=7,
                    rating_reason="Rest day went well and recovery was prioritized successfully",
                    tomorrow_priority="Return to training with full energy and focus on compounds",
                    tomorrow_obstacle="Might feel sluggish after rest day but will push through it",
                ),
                compliance_score=80.0,
            ))
        
        result = generate_training_chart(checkins)
        assert is_valid_png(result)


# ===== Compliance Chart Tests =====

class TestComplianceChart:
    """Tests for compliance score line chart with trend line."""
    
    def test_returns_bytesio(self, sample_week_checkins):
        result = generate_compliance_chart(sample_week_checkins)
        assert isinstance(result, io.BytesIO)
    
    def test_produces_valid_png(self, sample_week_checkins):
        result = generate_compliance_chart(sample_week_checkins)
        assert is_valid_png(result)
    
    def test_handles_uniform_scores(self):
        """
        Chart should handle all identical scores (trend line slope = 0).
        
        **Theory: Edge Case for Linear Regression**
        When all Y values are identical, the slope is 0 and the trend
        line is horizontal. numpy's polyfit handles this gracefully,
        but it's worth testing since some implementations might divide
        by zero on constant data.
        """
        checkins = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="All scores identical testing edge case for regression analysis",
                    rating=8,
                    rating_reason="Consistent day with same compliance score every single day",
                    tomorrow_priority="Continue with same level of consistency and effort each day",
                    tomorrow_obstacle="Complacency might set in when everything feels too routine",
                ),
                compliance_score=80.0,  # All same
            ))
        
        result = generate_compliance_chart(checkins)
        assert is_valid_png(result)
    
    def test_handles_two_checkins_no_trend(self):
        """
        With <3 check-ins, trend line should be skipped (not enough data).
        
        **Theory: Statistical Significance**
        A linear regression on 2 points always gives a perfect fit
        (R²=1) which is meaningless. We require at least 3 data points
        for the trend line to provide any informational value.
        """
        checkins = []
        for i in range(2):
            date = (datetime.now() - timedelta(days=1-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Only two check-ins to test trend line minimum requirement",
                    rating=7,
                    rating_reason="Testing with minimal data points for trend line calculation",
                    tomorrow_priority="Add more check-ins to reach the minimum for trend analysis",
                    tomorrow_obstacle="Need at least three data points for meaningful trend line",
                ),
                compliance_score=80.0,
            ))
        
        result = generate_compliance_chart(checkins)
        assert is_valid_png(result)


# ===== Domain Radar Chart Tests =====

class TestDomainRadar:
    """Tests for 5-axis domain radar chart."""
    
    def test_returns_bytesio(self, sample_week_checkins):
        result = generate_domain_radar(sample_week_checkins)
        assert isinstance(result, io.BytesIO)
    
    def test_produces_valid_png(self, sample_week_checkins):
        result = generate_domain_radar(sample_week_checkins)
        assert is_valid_png(result)
    
    def test_handles_perfect_scores(self):
        """Radar should render correctly when all domains are 100%."""
        checkins = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, sleep_hours=8.0,
                    training=True, deep_work=True,
                    skill_building=True, zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Perfect day with all constitution elements fully completed today",
                    rating=10,
                    rating_reason="Every single non-negotiable was met with full compliance score",
                    tomorrow_priority="Maintain this level of excellence across all five domains",
                    tomorrow_obstacle="Overconfidence might lead to complacency in discipline score",
                ),
                compliance_score=100.0,
            ))
        
        result = generate_domain_radar(checkins)
        assert is_valid_png(result)
    
    def test_handles_zero_scores(self):
        """Radar should render correctly when all domains are 0%."""
        checkins = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=False, sleep_hours=4.0,
                    training=False, deep_work=False,
                    skill_building=False, zero_porn=False, boundaries=False,
                ),
                responses=CheckInResponses(
                    challenges="Difficult day where no constitution elements were completed fully",
                    rating=1,
                    rating_reason="Missed every non-negotiable today which is deeply concerning now",
                    tomorrow_priority="Reset and focus on completing at least sleep and training first",
                    tomorrow_obstacle="Lack of motivation and energy after a completely failed day today",
                ),
                compliance_score=0.0,
            ))
        
        result = generate_domain_radar(checkins)
        assert is_valid_png(result)
    
    def test_single_checkin(self, sample_checkin):
        """Radar should work with just 1 data point."""
        result = generate_domain_radar([sample_checkin])
        assert is_valid_png(result)


# ===== Orchestration Function Tests =====

class TestGenerateWeeklyGraphs:
    """
    Tests for the orchestration function that generates all 4 graphs.
    
    **Theory: Graceful Degradation**
    If one graph fails, the others should still be generated.
    This is critical for reliability - a user shouldn't miss their
    entire weekly report because one graph type had an issue.
    """
    
    def test_returns_dict(self, sample_week_checkins):
        """Should return a dictionary of graph name -> BytesIO."""
        result = generate_weekly_graphs(sample_week_checkins)
        assert isinstance(result, dict)
    
    def test_generates_all_four_graphs(self, sample_week_checkins):
        """Should generate all 4 graph types."""
        result = generate_weekly_graphs(sample_week_checkins)
        assert len(result) == 4
        assert set(result.keys()) == {'sleep', 'training', 'compliance', 'radar'}
    
    def test_all_graphs_are_valid_png(self, sample_week_checkins):
        """Each graph in the dict should be a valid PNG."""
        result = generate_weekly_graphs(sample_week_checkins)
        for name, buffer in result.items():
            assert is_valid_png(buffer), f"{name} graph is not valid PNG"
    
    def test_all_graphs_have_reasonable_size(self, sample_week_checkins):
        """Each graph should have a reasonable file size."""
        result = generate_weekly_graphs(sample_week_checkins)
        for name, buffer in result.items():
            size = buffer.getbuffer().nbytes
            assert size > 5_000, f"{name} graph too small ({size} bytes)"
            assert size < 5_000_000, f"{name} graph too large ({size} bytes)"


# ===== Helper Function Tests =====

class TestHelperFunctions:
    """Tests for internal helper functions."""
    
    def test_setup_figure_returns_fig_and_axes(self):
        """_setup_figure should return (Figure, Axes) tuple."""
        fig, ax = _setup_figure("Test Title")
        assert fig is not None
        assert ax is not None
        # Clean up to avoid resource leak
        import matplotlib
        matplotlib.pyplot.close(fig)
    
    def test_figure_to_bytes_returns_bytesio(self):
        """_figure_to_bytes should convert figure to PNG bytes."""
        fig, ax = _setup_figure("Test")
        ax.plot([1, 2, 3], [1, 2, 3])
        
        result = _figure_to_bytes(fig)
        assert isinstance(result, io.BytesIO)
        assert is_valid_png(result)


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
