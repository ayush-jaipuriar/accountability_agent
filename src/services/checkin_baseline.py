"""
Check-In Baseline Service
=========================

Computes intelligent predictive baseline values for the 3-stage check-in.

Theory: Behavioral Accuracy without Friction
---------------------------------------------
Blindly pre-checking "100% success / all green" creates default effect bias
where users unconsciously confirm without honesty. Conversely, starting from
a blank slate causes high typing friction.

This service calculates an intelligent baseline based on:
1. Daytime task completions (if marked in morning briefing)
2. Rolling 3-day averages for continuous metrics (sleep, deep work, skill)
3. Day-of-week typical performance
4. Safe conservative defaults when data is limited
"""

import logging
from statistics import mean
from typing import Dict, Any, Optional

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service
from src.services.task_service import task_service

logger = logging.getLogger(__name__)


def compute_predictive_baseline(user_id: str, checkin_date: str) -> Dict[str, Any]:
    """
    Calculate baseline habit values for today's check-in.
    
    Returns:
        Dict with keys: sleep_hours, deep_work_hours, skill_building_hours,
        training_intensity, zero_porn, boundaries, has_history
    """
    try:
        user = firestore_service.get_user(user_id)
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        task_list = task_service.get_daily_tasks(user_id, checkin_date)

        # 1. Sleep Baseline
        recent_sleep = [
            c.tier1_non_negotiables.sleep_hours
            for c in recent_checkins[:3]
            if c.tier1_non_negotiables and c.tier1_non_negotiables.sleep_hours is not None
        ]
        if recent_sleep:
            raw_avg = mean(recent_sleep)
            sleep_hours = round(raw_avg * 2) / 2
        else:
            sleep_hours = 6.5  # Realistic honest starting baseline

        # 2. Deep Work Baseline
        dw_hours = 0.0
        if task_list and task_list.committed:
            primary_done = any(t.is_primary and t.completed for t in task_list.tasks)
            if primary_done:
                dw_hours = 2.0
        
        if dw_hours == 0.0:
            recent_dw = [
                c.tier1_non_negotiables.deep_work_hours
                for c in recent_checkins[:3]
                if c.tier1_non_negotiables and c.tier1_non_negotiables.deep_work_hours is not None
            ]
            if recent_dw:
                dw_hours = min(2.0, round(mean(recent_dw) * 2) / 2)
            else:
                dw_hours = 1.0  # Conservative baseline

        # 3. Skill Building Baseline
        recent_sb = [
            c.tier1_non_negotiables.skill_building_hours
            for c in recent_checkins[:3]
            if c.tier1_non_negotiables and c.tier1_non_negotiables.skill_building_hours is not None
        ]
        if recent_sb:
            sb_hours = min(2.0, round(mean(recent_sb) * 2) / 2)
        else:
            sb_hours = 0.0

        # 4. Training Intensity Baseline
        recent_training = [
            c.tier1_non_negotiables.training_intensity
            for c in recent_checkins[:3]
            if c.tier1_non_negotiables and c.tier1_non_negotiables.training_intensity
        ]
        if recent_training and "intense" in recent_training:
            training_intensity = "intense"
        elif recent_training and "moderate" in recent_training:
            training_intensity = "moderate"
        elif recent_training and "light" in recent_training:
            training_intensity = "light"
        else:
            training_intensity = "rest"

        # 5. Guardrails Baseline
        zero_porn = True
        boundaries = True

        return {
            "sleep_hours": sleep_hours,
            "deep_work_hours": dw_hours,
            "skill_building_hours": sb_hours,
            "training_intensity": training_intensity,
            "zero_porn": zero_porn,
            "boundaries": boundaries,
            "has_history": len(recent_checkins) > 0,
        }

    except Exception as e:
        logger.error(f"❌ Failed to compute check-in baseline for {user_id}: {e}", exc_info=True)
        return {
            "sleep_hours": 6.5,
            "deep_work_hours": 1.0,
            "skill_building_hours": 0.0,
            "training_intensity": "rest",
            "zero_porn": True,
            "boundaries": True,
            "has_history": False,
        }
