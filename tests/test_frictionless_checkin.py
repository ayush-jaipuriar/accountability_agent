import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.models.schemas import Tier1NonNegotiables
from src.utils.compliance import calculate_compliance_score, is_all_tier1_complete, get_missed_items
from src.agents.checkin_agent import CheckInAgent

@pytest.mark.asyncio
class TestRestDayCompliance:
    async def test_rest_day_compliance_met(self):
        """Rest day counts as compliant, giving 100% compliance if other goals are met."""
        # Rest day where training = False, is_rest_day = True
        tier1 = Tier1NonNegotiables(
            sleep=True,
            sleep_hours=8.0,
            training=False,
            is_rest_day=True,
            training_intensity='rest',
            deep_work=True,
            deep_work_hours=2.5,
            skill_building=True,
            skill_building_hours=2.0,
            zero_porn=True,
            boundaries=True
        )
        # All items are complete because training=False but is_rest_day=True
        assert is_all_tier1_complete(tier1) is True
        
        # Missed items should NOT contain training
        missed = get_missed_items(tier1)
        assert "training" not in missed
        
        # Compliance score should be 100%
        score = calculate_compliance_score(tier1)
        assert score == 100.0

    async def test_rest_day_compliance_partial(self):
        """Rest day with other targets missed doesn't give 100% compliance."""
        tier1 = Tier1NonNegotiables(
            sleep=False,  # Missed sleep
            sleep_hours=5.0,
            training=False,
            is_rest_day=True,
            training_intensity='rest',
            deep_work=True,
            deep_work_hours=2.5,
            skill_building=True,
            skill_building_hours=2.0,
            zero_porn=True,
            boundaries=True
        )
        assert is_all_tier1_complete(tier1) is False
        missed = get_missed_items(tier1)
        assert "sleep" in missed
        assert "training" not in missed


@pytest.mark.asyncio
class TestMicroHabitStreakPreservation:
    async def test_micro_habits_compliance_score(self):
        """If user meets micro-habit targets (e.g. sleep=6h, dw=0.5h, sb=0.5h), legacy booleans are True and compliance is 100%."""
        tier1 = Tier1NonNegotiables(
            sleep_hours=6.0,          # Micro-habit (full is 7.0)
            deep_work_hours=0.5,      # Micro-habit (full is 2.0)
            skill_building_hours=0.5,  # Micro-habit (full is 2.0)
            training_intensity='moderate',
            training=True,
            zero_porn=True,
            boundaries=True,
            sleep=True,
            deep_work=True,
            skill_building=True
        )
        
        # Let's verify properties on schemas:
        assert tier1.sleep_met is True
        assert tier1.sleep_met_full is False
        
        assert tier1.deep_work_met is True
        assert tier1.deep_work_met_full is False
        
        assert tier1.skill_building_met is True
        assert tier1.skill_building_met_full is False

    async def test_micro_habits_compliance_score_calculation(self):
        """Verify that a user logging micro-habit hours but missing full targets gets a compliance score reflecting full targets (i.e. not 100%)."""
        tier1 = Tier1NonNegotiables(
            sleep_hours=6.0,
            deep_work_hours=0.5,
            skill_building_hours=0.5,
            training_intensity='moderate',
            sleep=6.0 >= 7.0,
            training=True,
            deep_work=0.5 >= 2.0,
            skill_building=0.5 >= 2.0,
            zero_porn=True,
            boundaries=True,
            is_rest_day=False
        )
        
        # Streak preservation properties should still be True
        assert tier1.sleep_met is True
        assert tier1.deep_work_met is True
        assert tier1.skill_building_met is True
        
        # But legacy booleans (full targets) must be False
        assert tier1.sleep is False
        assert tier1.deep_work is False
        assert tier1.skill_building is False
        
        # Compliance score now reflects proportional credit for continuous habits (v3 scoring)
        # Sleep (6h/7h = 85.7%), Deep Work (0.5h/2h = 25%), Skill Building (0.5h/2h = 25%), Training (100%), Zero Porn (100%), Boundaries (100%)
        # Total: (0.857 + 0.25 + 0.25 + 1.0 + 1.0 + 1.0) / 6 = 72.6%
        score = calculate_compliance_score(tier1)
        assert pytest.approx(72.62, abs=0.1) == score



@pytest.mark.asyncio
class TestReflectionParser:
    async def test_parse_reflection_note_success(self):
        """Verify parse_reflection_note correctly structures Gemini response."""
        mock_llm = MagicMock()
        mock_llm.generate_text = AsyncMock(return_value="""
        {
          "alignment_rating": 8,
          "challenges": "Felt tired in the afternoon",
          "rating_reason": "Good alignment but sleep was a bit off",
          "tomorrow_priority": "Get to bed by 10 PM",
          "tomorrow_obstacle": "Distractions from social media"
        }
        """)
        
        agent = CheckInAgent("fake-project")
        agent.llm = mock_llm
        
        result = await agent.parse_reflection_note(
            note_text="I felt pretty tired today, but managed to do everything. Tomorrow I need to sleep early.",
            compliance_score=80.0,
            tier1_completed="sleep, deep work, boundaries"
        )
        
        assert result["alignment_rating"] == 8
        assert result["challenges"] == "Felt tired in the afternoon"
        assert result["tomorrow_priority"] == "Get to bed by 10 PM"
        assert result["tomorrow_obstacle"] == "Distractions from social media"
        assert result["rating_reason"] == "Good alignment but sleep was a bit off"

    async def test_parse_reflection_note_fallback(self):
        """Verify parse_reflection_note handles malformed LLM responses gracefully."""
        mock_llm = MagicMock()
        mock_llm.generate_text = AsyncMock(return_value="not a json string")
        
        agent = CheckInAgent("fake-project")
        agent.llm = mock_llm
        
        result = await agent.parse_reflection_note(
            note_text="My short reflection",
            compliance_score=80.0,
            tier1_completed="sleep"
        )
        
        # Should gracefully fall back to defaults or raw text
        assert result["alignment_rating"] == 8
        assert result["tomorrow_priority"] == "Maintain consistency."
        assert "My short reflection" in result["rating_reason"]
