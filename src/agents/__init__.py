"""
Agents Package - LangGraph Multi-Agent System

This package contains all the AI agents for Phase 2:
- Supervisor Agent: Intent classification and routing
- CheckIn Agent: Check-in conversation with AI feedback
- Pattern Detection Agent: Analyze check-ins for violations
- Intervention Agent: Generate warning messages

Architecture:
-------------
User Message → Supervisor → Routes to specific agent → Generates response
                ↓
         (Intent: checkin, emotional, query, command)
                ↓
         CheckIn Agent / Emotional Agent / Query Handler
"""
