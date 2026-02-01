"""
Constitution Service
===================

Loads and provides access to user's constitution document.

Purpose:
- Loads constitution.md at startup
- Provides full text for AI prompts (Phase 2)
- Extracts Tier 1 rules for validation
- Makes constitution accessible throughout app

Why a Service?
- Load once, use everywhere (efficient)
- Centralized access point
- Easy to mock in tests
- Can add caching/updating logic later
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ConstitutionService:
    """
    Service for loading and accessing user's constitution.
    
    The constitution contains:
    - Core principles
    - Operating modes (optimization/maintenance/survival)
    - Tier 1 non-negotiables
    - Historical patterns
    - Crisis protocols
    
    Usage:
        from src.services.constitution_service import constitution_service
        
        text = constitution_service.get_constitution_text()
        rules = constitution_service.get_tier1_rules()
    """
    
    def __init__(self, constitution_path: str = "constitution.md"):
        """
        Initialize constitution service.
        
        Args:
            constitution_path: Path to constitution.md file
        """
        self.constitution_path = Path(constitution_path)
        self._constitution_text: Optional[str] = None
        self._load_constitution()
    
    def _load_constitution(self) -> None:
        """
        Load constitution text from file.
        
        Called once at initialization.
        """
        try:
            if not self.constitution_path.exists():
                raise FileNotFoundError(
                    f"Constitution file not found at: {self.constitution_path.absolute()}"
                )
            
            with open(self.constitution_path, 'r', encoding='utf-8') as f:
                self._constitution_text = f.read()
            
            logger.info(
                f"✅ Constitution loaded: {len(self._constitution_text)} characters "
                f"from {self.constitution_path}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to load constitution: {e}")
            raise
    
    def get_constitution_text(self) -> str:
        """
        Get full constitution text.
        
        Used for AI prompts in Phase 2.
        
        Returns:
            str: Complete constitution markdown text
            
        Example:
            >>> text = constitution_service.get_constitution_text()
            >>> print(len(text))
            145000  # ~145KB of constitution text
        """
        if self._constitution_text is None:
            raise RuntimeError("Constitution not loaded")
        
        return self._constitution_text
    
    def get_constitution_summary(self, max_chars: int = 2000) -> str:
        """
        Get abbreviated constitution summary for token efficiency.
        
        Used when full constitution would exceed token limits.
        
        Args:
            max_chars: Maximum characters to return
            
        Returns:
            str: Truncated constitution with "..." suffix
        """
        full_text = self.get_constitution_text()
        
        if len(full_text) <= max_chars:
            return full_text
        
        return full_text[:max_chars] + "\n\n... (truncated for token efficiency)"
    
    def get_tier1_rules(self) -> Dict[str, Dict]:
        """
        Extract Tier 1 non-negotiable rules from constitution.
        
        Used for:
        - Validation during check-in
        - Displaying targets to user
        - Pattern detection thresholds
        
        Returns:
            dict: Rules for each Tier 1 item
            
        Example:
            >>> rules = constitution_service.get_tier1_rules()
            >>> rules['sleep']['target_hours']
            7.0
            >>> rules['training']['frequency_optimization']
            6
        """
        return {
            "sleep": {
                "target_hours": 7.0,
                "critical_threshold": 6.0,  # Below this = pattern trigger
                "description": "7+ hours per night",
                "bedtime_target": "11:00 PM",
                "wake_target": "6:30 AM"
            },
            "training": {
                "frequency_optimization": 6,  # times per week
                "frequency_maintenance": 4,   # times per week (current mode)
                "frequency_survival": 3,      # times per week
                "description": "Workout OR scheduled rest day",
                "rest_days_per_week": 1
            },
            "deep_work": {
                "target_hours": 2.0,
                "critical_threshold": 1.0,
                "description": "2+ hours of focused work/study",
                "focus_areas": ["LeetCode", "System Design", "Job Applications"]
            },
            "zero_porn": {
                "rule": "absolute",
                "description": "No consumption, period",
                "relapse_threshold": 3,  # 3 instances in 7 days = pattern
                "high_risk_window": "10 PM - 12 AM"
            },
            "boundaries": {
                "rule": "no_toxic_sacrifices",
                "description": "No toxic interactions, no self-sacrifice that compromises constitution",
                "examples": [
                    "Declining social events that conflict with sleep",
                    "Saying no to last-minute requests during deep work",
                    "Avoiding relationship discussions after 10 PM"
                ]
            }
        }
    
    def get_operating_modes(self) -> Dict[str, Dict]:
        """
        Get constitution operating mode definitions.
        
        Returns:
            dict: Mode definitions with graduation criteria
        """
        return {
            "optimization": {
                "description": "All systems firing - aggressive growth",
                "training_frequency": 6,
                "deep_work_hours": 3,
                "target_compliance": 90,
                "graduation_criteria": "30 days at 90%+ compliance"
            },
            "maintenance": {
                "description": "Sustaining progress, recovery phase",
                "training_frequency": 4,
                "deep_work_hours": 2,
                "target_compliance": 80,
                "current_status": "Post-surgery recovery (until April 2026)",
                "graduation_criteria": "14 days at 85%+ compliance"
            },
            "survival": {
                "description": "Crisis mode - protect bare minimums",
                "training_frequency": 3,
                "deep_work_hours": 1,
                "target_compliance": 60,
                "purpose": "Prevent full spiral during acute crisis",
                "graduation_criteria": "7 days at 70%+ compliance → move to maintenance"
            }
        }
    
    def get_historical_patterns(self) -> Dict[str, Dict]:
        """
        Get user's historical patterns to watch for.
        
        Used by pattern detection agent (Phase 2).
        
        Returns:
            dict: Historical patterns with triggers and responses
        """
        return {
            "relationship_stress_spiral": {
                "trigger": "Relationship stress or breakup",
                "cascade": [
                    "1. Emotional stress leads to reduced sleep",
                    "2. Sleep loss → missed workouts",
                    "3. Reduced productivity → depression",
                    "4. Full 6-month regression"
                ],
                "last_occurrence": "Feb 2025 (post-breakup)",
                "ai_response": "Flag within 24 hours, immediate intervention",
                "early_warning_signs": [
                    "2+ nights of <6 hours sleep",
                    "Increased late-night phone usage",
                    "Skipped workouts 2+ days"
                ]
            },
            "surgery_anxiety_procrastination": {
                "trigger": "Medical procedure anxiety",
                "pattern": "Avoidance behavior, task procrastination",
                "last_occurrence": "Jan-Feb 2026 (pre-surgery)",
                "ai_response": "Push through resistance, task completion tracking"
            },
            "post_breakup_vulnerability": {
                "trigger": "Loneliness + boredom",
                "high_risk_window": "10 PM - 12 AM",
                "pattern": "Porn relapse risk",
                "duration": "First 2 weeks post-breakup",
                "ai_response": "Interrupt pattern, suggest public space or friend contact"
            }
        }
    
    def get_crisis_protocols(self) -> Dict[str, Dict]:
        """
        Get crisis intervention protocols.
        
        Returns:
            dict: Protocols with escalation rules
        """
        return {
            "ghosting": {
                "trigger": "3+ missed check-ins",
                "escalation": [
                    "Day 2: Gentle reminder",
                    "Day 3: Urgent check-in",
                    "Day 4: Reference historical ghosting patterns",
                    "Day 5: Emergency escalation (future: contact accountability partner)"
                ]
            },
            "sleep_crisis": {
                "trigger": "<6 hours sleep for 3+ consecutive nights",
                "response": [
                    "Warning intervention",
                    "Reference Feb 2025 spiral",
                    "Demand immediate action (adjust schedule, remove phone from bedroom)"
                ]
            },
            "porn_relapse_pattern": {
                "trigger": "3+ relapses in one week",
                "response": [
                    "Critical intervention",
                    "Immediate action required: text friend, delete apps, schedule call"
                ]
            },
            "compliance_freefall": {
                "trigger": "<60% compliance for 5+ consecutive days",
                "response": [
                    "Emergency mode activation",
                    "Switch to survival mode protocols",
                    "Daily mandatory check-ins with accountability partner"
                ]
            }
        }
    
    def reload_constitution(self) -> None:
        """
        Reload constitution from disk.
        
        Used if constitution.md is updated while app is running.
        """
        self._constitution_text = None
        self._load_constitution()
        logger.info("♻️ Constitution reloaded from disk")


# ===== Singleton Instance =====
# Import this throughout the app: `from src.services.constitution_service import constitution_service`

constitution_service = ConstitutionService()
