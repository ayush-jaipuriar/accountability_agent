"""
FastAPI Application - Main Entry Point
======================================

This is the web server that receives Telegram webhook calls.

Flow:
1. User sends message to bot
2. Telegram servers POST to /webhook/telegram
3. FastAPI receives update → passes to bot handler
4. Bot processes message → sends response to user

Key Concepts:
- Webhook: Event-driven (Telegram pushes to us, vs polling where we fetch)
- Async: Non-blocking I/O (handles multiple users simultaneously)
- Health Check: Cloud Run pings /health to verify app is running
- Startup Event: Initialize bot, set webhook URL
"""

from fastapi import FastAPI, Request, HTTPException
from telegram import Update
import logging
import sys
from datetime import datetime

from src.config import settings
from src.bot.telegram_bot import bot_manager
from src.bot.conversation import create_checkin_conversation_handler
from src.services.firestore_service import firestore_service

# ===== Logging Configuration =====

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)


# ===== FastAPI Application =====

app = FastAPI(
    title="Constitution Accountability Agent",
    description="AI-powered accountability system for personal constitution adherence",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.environment == "development" else None
)


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """
    Run once when application starts.
    
    Tasks:
    1. Initialize Telegram application
    2. Register conversation handler
    3. Test Firestore connection
    4. Set webhook URL (production only)
    5. Log startup info
    """
    logger.info("🚀 Starting Constitution Accountability Agent...")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   GCP Project: {settings.gcp_project_id}")
    logger.info(f"   Region: {settings.gcp_region}")
    
    # Initialize Telegram application (CRITICAL for webhook mode)
    await bot_manager.application.initialize()
    logger.info("✅ Telegram application initialized")
    
    # Register check-in conversation handler
    conversation_handler = create_checkin_conversation_handler()
    bot_manager.register_conversation_handler(conversation_handler)
    logger.info("✅ Conversation handler registered")
    
    # Test Firestore connection
    try:
        if firestore_service.test_connection():
            logger.info("✅ Firestore connection verified")
    except Exception as e:
        logger.error(f"❌ Firestore connection failed: {e}")
        raise
    
    # Set webhook URL (production only)
    if settings.environment == "production" and settings.webhook_url:
        webhook_url = f"{settings.webhook_url}/webhook/telegram"
        
        try:
            success = await bot_manager.set_webhook(webhook_url)
            if success:
                logger.info(f"✅ Webhook set to: {webhook_url}")
            else:
                logger.error(f"❌ Failed to set webhook")
        except Exception as e:
            logger.error(f"❌ Error setting webhook: {e}")
            raise
    else:
        logger.info("⚠️ Development mode - webhook not set")
        logger.info("   For local testing, use polling mode or ngrok")
    
    logger.info("✅ Constitution Agent started successfully!")
    logger.info("=" * 60)


# ===== Shutdown Event =====

@app.on_event("shutdown")
async def shutdown_event():
    """
    Run when application shuts down.
    
    Cleanup tasks: shutdown Telegram application gracefully.
    """
    logger.info("🛑 Shutting down Constitution Agent...")
    
    # Shutdown Telegram application
    await bot_manager.application.shutdown()
    logger.info("✅ Telegram application shutdown")
    
    logger.info("✅ Shutdown complete")


# ===== Health Check Endpoint =====

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Cloud Run.
    
    Cloud Run pings this to verify app is running.
    Must return 200 OK if healthy.
    
    Returns:
        dict: Health status
    """
    # Check Firestore connection
    firestore_ok = False
    try:
        firestore_ok = firestore_service.test_connection()
    except Exception as e:
        logger.error(f"Health check: Firestore error: {e}")
    
    # Overall health
    healthy = firestore_ok
    
    if healthy:
        return {
            "status": "healthy",
            "service": "constitution-agent",
            "version": "1.0.0",
            "environment": settings.environment,
            "checks": {
                "firestore": "ok"
            }
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "checks": {
                    "firestore": "error" if not firestore_ok else "ok"
                }
            }
        )


# ===== Telegram Webhook Endpoint =====

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Receive updates from Telegram.
    
    Telegram sends POST requests here whenever:
    - User sends message to bot
    - User presses inline button
    - User sends command
    
    Flow:
    1. Telegram servers → POST to this endpoint
    2. We parse the update
    3. Pass to bot application for processing
    4. Bot sends response back to user via Telegram API
    
    Args:
        request: Incoming HTTP request from Telegram
        
    Returns:
        dict: {"ok": True} to acknowledge receipt
    """
    try:
        # Get update data from request body
        update_data = await request.json()
        
        logger.debug(f"Received update: {update_data.get('update_id', 'unknown')}")
        
        # Convert to Telegram Update object
        update = Update.de_json(update_data, bot_manager.bot)
        
        # Process update with bot
        await bot_manager.application.process_update(update)
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        
        # Still return 200 OK to Telegram (don't retry failed updates)
        # Log the error for investigation
        return {"ok": False, "error": str(e)}


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """
    Root endpoint (just for info).
    
    Returns basic info about the service.
    """
    return {
        "service": "Constitution Accountability Agent",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook/telegram",
            "docs": "/docs" if settings.environment == "development" else "disabled"
        }
    }


# ===== Pattern Scanning Endpoint (Phase 2) =====

@app.post("/trigger/pattern-scan")
async def pattern_scan_trigger(request: Request):
    """
    Trigger pattern detection scan across all active users (Phase 2).
    
    Called by Cloud Scheduler every 6 hours to proactively detect constitution violations.
    
    Flow:
    -----
    1. Verify request is from Cloud Scheduler (security)
    2. Get all active users (checked in within last 7 days)
    3. For each user:
       a. Get recent check-ins (last 7-14 days)
       b. Run pattern detection
       c. If patterns detected → generate intervention
       d. Send intervention via Telegram
       e. Log intervention in Firestore
    4. Return scan summary
    
    Security: Verify request is from Cloud Scheduler (check header).
    
    Returns:
        dict: Scan results (users scanned, patterns detected, interventions sent)
    """
    from src.agents.pattern_detection import get_pattern_detection_agent
    from src.agents.intervention import get_intervention_agent
    
    # Verify request is from Cloud Scheduler (optional but recommended)
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"📡 Pattern scan triggered by: {scheduler_header or 'manual/unknown'}")
    
    # Security: In production, enforce Cloud Scheduler authentication
    # if settings.environment == "production" and scheduler_header != "pattern-scan-job":
    #     raise HTTPException(403, "Unauthorized: Not from Cloud Scheduler")
    
    try:
        # Get pattern detection and intervention agents
        pattern_agent = get_pattern_detection_agent()
        intervention_agent = get_intervention_agent(settings.gcp_project_id)
        
        # Get all active users (checked in within last 7 days)
        # For now, we'll scan all users (Phase 1 doesn't have "active users" method)
        # In production, add get_active_users(days=7) to firestore_service
        all_users = firestore_service.get_all_users()
        
        logger.info(f"🔍 Scanning {len(all_users)} users for patterns...")
        
        users_scanned = 0
        patterns_detected = 0
        interventions_sent = 0
        errors = 0
        
        for user in all_users:
            try:
                users_scanned += 1
                
                # Get recent check-ins (last 14 days for comprehensive detection)
                checkins = firestore_service.get_recent_checkins(user.user_id, days=14)
                
                if not checkins:
                    logger.debug(f"User {user.user_id}: No recent check-ins, skipping")
                    continue
                
                # Run pattern detection (check-in based patterns)
                patterns = pattern_agent.detect_patterns(checkins)
                
                # Phase 3B: Check for ghosting (user-based pattern)
                # Ghosting detection doesn't need check-ins - it looks at last_checkin_date
                ghosting_pattern = pattern_agent.detect_ghosting(user.user_id)
                if ghosting_pattern:
                    patterns.append(ghosting_pattern)
                    logger.warning(f"👻 User {user.user_id}: GHOSTING detected - {ghosting_pattern.data['days_missing']} days missing")
                
                if patterns:
                    logger.warning(f"⚠️  User {user.user_id}: {len(patterns)} pattern(s) detected")
                    patterns_detected += len(patterns)
                    
                    # Generate and send intervention for each pattern
                    for pattern in patterns:
                        try:
                            # Generate intervention message
                            intervention_msg = await intervention_agent.generate_intervention(
                                user_id=user.user_id,
                                pattern=pattern
                            )
                            
                            # Send intervention via Telegram
                            await bot_manager.send_message(
                                chat_id=user.user_id,
                                text=intervention_msg
                            )
                            
                            interventions_sent += 1
                            
                            # Log intervention in Firestore
                            firestore_service.log_intervention(
                                user_id=user.user_id,
                                pattern_type=pattern.type,
                                severity=pattern.severity,
                                data=pattern.data,
                                message=intervention_msg
                            )
                            
                            logger.info(f"✅ Sent {pattern.severity} intervention to {user.user_id}: {pattern.type}")
                            
                            # Phase 3B: Day 5 ghosting → Notify accountability partner
                            if pattern.type == "ghosting" and pattern.data.get("days_missing", 0) >= 5:
                                if user.accountability_partner_id:
                                    try:
                                        partner = firestore_service.get_user(user.accountability_partner_id)
                                        if partner:
                                            days_missing = pattern.data["days_missing"]
                                            last_checkin = pattern.data.get("last_checkin_date", "unknown")
                                            
                                            partner_msg = (
                                                f"🚨 **Accountability Partner Alert**\n\n"
                                                f"Your partner **{user.name}** hasn't checked in for **{days_missing} days**.\n\n"
                                                f"Last check-in: {last_checkin}\n\n"
                                                f"This is serious. Consider reaching out to check on them:\n"
                                                f"• Text them directly\n"
                                                f"• Call if you have their number\n"
                                                f"• Make sure they're okay\n\n"
                                                f"Sometimes people need a friend more than a bot."
                                            )
                                            
                                            await bot_manager.send_message(
                                                chat_id=partner.telegram_id,
                                                text=partner_msg
                                            )
                                            
                                            logger.info(
                                                f"✅ Partner notification sent: {user.user_id} ghosted ({days_missing} days), "
                                                f"notified partner {partner.user_id}"
                                            )
                                    except Exception as e:
                                        logger.error(f"❌ Failed to notify partner for {user.user_id}: {e}")
                                else:
                                    logger.info(f"ℹ️ User {user.user_id} has no partner to notify (Day 5 ghosting)")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to send intervention to {user.user_id}: {e}")
                            errors += 1
                else:
                    logger.debug(f"User {user.user_id}: No patterns detected (compliant)")
            
            except Exception as e:
                logger.error(f"❌ Error scanning user {user.user_id}: {e}")
                errors += 1
                continue
        
        # Return scan summary
        result = {
            "status": "scan_complete",
            "timestamp": datetime.utcnow().isoformat(),
            "users_scanned": users_scanned,
            "patterns_detected": patterns_detected,
            "interventions_sent": interventions_sent,
            "errors": errors
        }
        
        logger.info(
            f"✅ Pattern scan complete: {users_scanned} users scanned, "
            f"{patterns_detected} patterns detected, {interventions_sent} interventions sent"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Pattern scan failed: {e}", exc_info=True)
        raise HTTPException(500, f"Pattern scan failed: {str(e)}")


# ===== Phase 3A: Triple Reminder System =====

@app.post("/cron/reminder_first")
async def reminder_first(request: Request):
    """
    First daily reminder at 9:00 PM IST (Phase 3A Killer Feature).
    
    Tone: Friendly and inviting
    
    Triggered by Cloud Scheduler daily at 9:00 PM IST.
    Finds all users who haven't checked in today and sends friendly reminder.
    
    Returns:
        dict: Reminder results (users reminded)
    """
    from src.utils.timezone_utils import get_current_date_ist
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"🔔 First reminder triggered by: {scheduler_header or 'manual'}")
    
    try:
        today = get_current_date_ist()
        users_without_checkin = firestore_service.get_users_without_checkin_today(today)
        
        logger.info(f"📤 Sending first reminder to {len(users_without_checkin)} users")
        
        reminders_sent = 0
        errors = 0
        
        for user in users_without_checkin:
            try:
                # Check if reminder already sent today
                reminder_status = firestore_service.get_reminder_status(user.user_id, today)
                if reminder_status and reminder_status.get("first_sent"):
                    logger.debug(f"User {user.user_id}: First reminder already sent today, skipping")
                    continue
                
                # Send friendly first reminder
                message = (
                    f"🔔 **Daily Check-In Time!**\n\n"
                    f"Hey {user.name}! It's 9 PM - time for your daily check-in.\n\n"
                    f"🔥 Current streak: {user.streaks.current_streak} days\n"
                    f"🎯 Mode: {user.constitution_mode.title()}\n\n"
                    f"Ready to keep the momentum going?\n\n"
                    f"Use /checkin to start! 💪"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message
                )
                
                # Mark reminder as sent
                firestore_service.set_reminder_sent(user.user_id, today, "first")
                reminders_sent += 1
                
                logger.info(f"✅ Sent first reminder to {user.user_id} ({user.name})")
                
            except Exception as e:
                logger.error(f"❌ Failed to send first reminder to {user.user_id}: {e}")
                errors += 1
        
        result = {
            "status": "reminders_sent",
            "reminder_type": "first",
            "time": "21:00 IST",
            "timestamp": datetime.utcnow().isoformat(),
            "users_without_checkin": len(users_without_checkin),
            "reminders_sent": reminders_sent,
            "errors": errors
        }
        
        logger.info(f"✅ First reminder complete: {reminders_sent} sent, {errors} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ First reminder failed: {e}", exc_info=True)
        raise HTTPException(500, f"First reminder failed: {str(e)}")


@app.post("/cron/reminder_second")
async def reminder_second(request: Request):
    """
    Second daily reminder at 9:30 PM IST (Phase 3A).
    
    Tone: Nudge - slightly more urgent
    
    Triggered by Cloud Scheduler daily at 9:30 PM IST.
    Finds users who still haven't checked in after first reminder.
    
    Returns:
        dict: Reminder results (users reminded)
    """
    from src.utils.timezone_utils import get_current_date_ist
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"🔔 Second reminder triggered by: {scheduler_header or 'manual'}")
    
    try:
        today = get_current_date_ist()
        users_without_checkin = firestore_service.get_users_without_checkin_today(today)
        
        logger.info(f"📤 Sending second reminder to {len(users_without_checkin)} users")
        
        reminders_sent = 0
        errors = 0
        
        for user in users_without_checkin:
            try:
                # Check if second reminder already sent
                reminder_status = firestore_service.get_reminder_status(user.user_id, today)
                if reminder_status and reminder_status.get("second_sent"):
                    logger.debug(f"User {user.user_id}: Second reminder already sent today, skipping")
                    continue
                
                # Send nudge reminder
                message = (
                    f"👋 **Still There?**\n\n"
                    f"Hey {user.name}, your daily check-in is waiting!\n\n"
                    f"🔥 Don't break your {user.streaks.current_streak}-day streak\n"
                    f"⏰ Check-in closes at midnight\n\n"
                    f"Just takes 2 minutes: /checkin"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message
                )
                
                # Mark reminder as sent
                firestore_service.set_reminder_sent(user.user_id, today, "second")
                reminders_sent += 1
                
                logger.info(f"✅ Sent second reminder to {user.user_id} ({user.name})")
                
            except Exception as e:
                logger.error(f"❌ Failed to send second reminder to {user.user_id}: {e}")
                errors += 1
        
        result = {
            "status": "reminders_sent",
            "reminder_type": "second",
            "time": "21:30 IST",
            "timestamp": datetime.utcnow().isoformat(),
            "users_without_checkin": len(users_without_checkin),
            "reminders_sent": reminders_sent,
            "errors": errors
        }
        
        logger.info(f"✅ Second reminder complete: {reminders_sent} sent, {errors} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ Second reminder failed: {e}", exc_info=True)
        raise HTTPException(500, f"Second reminder failed: {str(e)}")


@app.post("/cron/reminder_third")
async def reminder_third(request: Request):
    """
    Third daily reminder at 10:00 PM IST (Phase 3A).
    
    Tone: Urgent - last chance to maintain streak
    
    Triggered by Cloud Scheduler daily at 10:00 PM IST.
    Final reminder before midnight cutoff. Emphasizes streak protection.
    
    Returns:
        dict: Reminder results (users reminded)
    """
    from src.utils.timezone_utils import get_current_date_ist
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"🔔 Third reminder triggered by: {scheduler_header or 'manual'}")
    
    try:
        today = get_current_date_ist()
        users_without_checkin = firestore_service.get_users_without_checkin_today(today)
        
        logger.info(f"📤 Sending third (urgent) reminder to {len(users_without_checkin)} users")
        
        reminders_sent = 0
        errors = 0
        
        for user in users_without_checkin:
            try:
                # Check if third reminder already sent
                reminder_status = firestore_service.get_reminder_status(user.user_id, today)
                if reminder_status and reminder_status.get("third_sent"):
                    logger.debug(f"User {user.user_id}: Third reminder already sent today, skipping")
                    continue
                
                # Send urgent reminder with streak shield info
                message = (
                    f"⚠️ **URGENT: Check-In Closing Soon!**\n\n"
                    f"⏰ Only 2 hours left until midnight!\n"
                    f"🔥 Your {user.streaks.current_streak}-day streak is at risk\n\n"
                )
                
                # Add streak shield information
                if user.streak_shields.available > 0:
                    message += (
                        f"🛡️ You have {user.streak_shields.available} streak shield(s) available\n"
                        f"   (Use if you absolutely can't check in tonight)\n\n"
                    )
                else:
                    message += (
                        f"🛡️ No streak shields remaining - this is critical!\n\n"
                    )
                
                message += (
                    f"**Don't let one missed day undo {user.streaks.current_streak} days of work.**\n\n"
                    f"Check in NOW: /checkin"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message
                )
                
                # Mark reminder as sent
                firestore_service.set_reminder_sent(user.user_id, today, "third")
                reminders_sent += 1
                
                logger.info(f"✅ Sent third (urgent) reminder to {user.user_id} ({user.name})")
                
            except Exception as e:
                logger.error(f"❌ Failed to send third reminder to {user.user_id}: {e}")
                errors += 1
        
        result = {
            "status": "reminders_sent",
            "reminder_type": "third",
            "time": "22:00 IST",
            "timestamp": datetime.utcnow().isoformat(),
            "users_without_checkin": len(users_without_checkin),
            "reminders_sent": reminders_sent,
            "errors": errors
        }
        
        logger.info(f"✅ Third reminder complete: {reminders_sent} sent, {errors} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ Third reminder failed: {e}", exc_info=True)
        raise HTTPException(500, f"Third reminder failed: {str(e)}")


# ===== Phase 3E: Quick Check-In Reset =====

@app.post("/cron/reset_quick_checkins")
async def reset_quick_checkins(request: Request):
    """
    Reset quick check-in counters every Monday 12:00 AM IST (Phase 3E).
    
    **Purpose:**
    - Quick check-ins limited to 2 per week
    - Counter resets every Monday to give users a fresh start
    - Tracks history of which dates were used
    
    **Triggered by:** Cloud Scheduler (weekly, Monday 00:00 IST)
    
    **Process:**
    1. Get all users
    2. Reset quick_checkin_count to 0
    3. Clear quick_checkin_used_dates (optional: keep for history)
    4. Update quick_checkin_reset_date to next Monday
    
    Returns:
        dict: Reset results (users processed)
    """
    from src.utils.timezone_utils import get_next_monday
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"🔄 Quick check-in reset triggered by: {scheduler_header or 'manual'}")
    
    try:
        # Get all users
        all_users = firestore_service.get_all_users()
        logger.info(f"🔄 Resetting quick check-in counters for {len(all_users)} users")
        
        reset_count = 0
        errors = 0
        next_monday = get_next_monday(format_string="%Y-%m-%d")
        
        for user in all_users:
            try:
                # Get current count (for logging)
                previous_count = user.quick_checkin_count
                
                # Reset counter and update reset date
                firestore_service.update_user(user.user_id, {
                    "quick_checkin_count": 0,
                    # Clear history (or keep last 4 weeks for analytics)
                    "quick_checkin_used_dates": [],
                    "quick_checkin_reset_date": next_monday
                })
                
                reset_count += 1
                
                if previous_count > 0:
                    logger.info(
                        f"✅ Reset quick check-ins for {user.user_id} ({user.name}): "
                        f"{previous_count}/2 → 0/2"
                    )
                
            except Exception as e:
                logger.error(f"❌ Failed to reset quick check-ins for {user.user_id}: {e}")
                errors += 1
        
        result = {
            "status": "reset_complete",
            "timestamp": datetime.utcnow().isoformat(),
            "total_users": len(all_users),
            "reset_count": reset_count,
            "errors": errors,
            "next_reset_date": next_monday
        }
        
        logger.info(
            f"✅ Quick check-in reset complete: {reset_count} users reset, "
            f"{errors} errors. Next reset: {next_monday}"
        )
        return result
        
    except Exception as e:
        logger.error(f"❌ Quick check-in reset failed: {e}", exc_info=True)
        raise HTTPException(500, f"Quick check-in reset failed: {str(e)}")


# ===== Phase 3F: Weekly Report Trigger =====

@app.post("/trigger/weekly-report")
async def weekly_report_trigger(request: Request):
    """
    Trigger weekly report generation for all users (Phase 3F).
    
    Called by Cloud Scheduler every Sunday 9:00 AM IST.
    
    **Process:**
    1. Iterate over all active users
    2. For each user: generate 4 graphs + AI insights
    3. Send report via Telegram (text + 4 images)
    4. Return aggregate results
    
    **Performance Considerations:**
    - Reports are generated sequentially (Telegram rate limits: 30 msg/s)
    - Each report takes ~5-15 seconds (graph generation + LLM call)
    - For 10 users: ~2.5 minutes total
    - Cloud Run timeout: 300s (5 minutes) - sufficient for 20+ users
    
    **Cost:**
    - Graph generation: $0.00 (matplotlib)
    - AI insights: ~$0.003/month (300 tokens × 40 reports)
    - Cloud Scheduler: $0.10/month per job
    
    Returns:
        dict: Aggregate report results
    """
    from src.agents.reporting_agent import send_weekly_reports_to_all
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"📊 Weekly report triggered by: {scheduler_header or 'manual'}")
    
    try:
        results = await send_weekly_reports_to_all(
            project_id=settings.gcp_project_id,
            bot=bot_manager.bot,
        )
        
        logger.info(
            f"✅ Weekly reports complete: {results['reports_sent']} sent, "
            f"{results['reports_failed']} failed"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Weekly report trigger failed: {e}", exc_info=True)
        raise HTTPException(500, f"Weekly report failed: {str(e)}")


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    
    Logs error and returns 500 response.
    """
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    
    return {
        "error": "Internal server error",
        "message": str(exc) if settings.environment == "development" else "Something went wrong"
    }


# ===== Development Mode: Polling Support =====

async def start_polling():
    """
    Start polling mode for local development.
    
    Use this instead of webhooks when testing locally.
    
    Usage:
        python -m src.polling
    """
    logger.info("🔄 Starting polling mode (development only)...")
    
    # Register conversation handler
    conversation_handler = create_checkin_conversation_handler()
    bot_manager.register_conversation_handler(conversation_handler)
    
    # Remove webhook
    await bot_manager.delete_webhook()
    
    # Start polling
    application = bot_manager.get_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("✅ Polling started - bot is now active")
    logger.info("   Press Ctrl+C to stop")


# ===== Entry Point =====

if __name__ == "__main__":
    """
    Direct execution (for local development with uvicorn).
    
    Usage:
        uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    """
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level=settings.log_level.lower()
    )
