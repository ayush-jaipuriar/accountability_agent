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
import json
import sys
import time
from datetime import datetime

from src.config import settings
from src.bot.telegram_bot import bot_manager
from src.bot.conversation import create_checkin_conversation_handler
from src.services.firestore_service import firestore_service
from src.utils.metrics import metrics
from src.utils.rate_limiter import rate_limiter

# ===== Logging Configuration =====
# 
# Two modes:
# 1. JSON logging (production): Structured JSON that Cloud Logging automatically
#    parses into searchable, filterable log entries. Each log line is a JSON object
#    with severity, message, module, and custom fields (user_id, latency, etc.).
#    Cloud Monitoring can create log-based metrics from these structured fields.
#
# 2. Plain text logging (development): Human-readable format for local debugging.
#    Easier to scan visually but not machine-parseable.

class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for Google Cloud Logging compatibility.
    
    Cloud Logging expects a 'severity' field (not 'level') and parses
    any valid JSON line into structured log entry fields. This means
    custom fields like 'user_id' and 'latency_ms' become searchable
    in the Logs Explorer without any configuration.
    """
    def format(self, record):
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "timestamp": self.formatTime(record, self.datefmt),
        }
        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include custom fields attached to log records
        for field in ("user_id", "command", "latency_ms", "error_category"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        return json.dumps(log_entry)

# Apply formatter based on config
log_handler = logging.StreamHandler(sys.stdout)
if settings.json_logging:
    log_handler.setFormatter(JSONFormatter())
else:
    log_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    handlers=[log_handler],
)

logger = logging.getLogger(__name__)

# ===== Initialize Rate Limiter with Admin IDs =====
# Parse comma-separated admin IDs from config
if settings.admin_telegram_ids:
    _admin_ids = [aid.strip() for aid in settings.admin_telegram_ids.split(",") if aid.strip()]
    rate_limiter.set_admin_ids(_admin_ids)


# ===== FastAPI Application =====

app = FastAPI(
    title="Constitution Accountability Agent",
    description="AI-powered accountability system for personal constitution adherence",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.environment == "development" else None
)


# ===== Cron Endpoint Authentication =====

def verify_cron_request(request: Request) -> None:
    """
    Verify that a cron/trigger request comes from Cloud Scheduler.
    
    WHY THIS MATTERS:
    -----------------
    Without authentication, anyone who discovers the cron endpoint URLs can:
    - Trigger mass reminders to all users (spam)
    - Force pattern scans (waste API credits)
    - Generate reports for all users (abuse resources)
    
    HOW IT WORKS:
    -------------
    Cloud Scheduler is configured to send a secret header (X-Cron-Secret) with
    each request. This function compares it to the expected secret from config.
    If they don't match (or the header is missing), the request is rejected.
    
    When cron_secret is empty (development), authentication is skipped.
    
    Args:
        request: FastAPI Request object
        
    Raises:
        HTTPException(403): If authentication fails
    """
    expected_secret = settings.cron_secret
    
    # Skip auth if no secret configured (development mode)
    if not expected_secret:
        logger.debug("⚠️ Cron auth skipped (no CRON_SECRET configured)")
        return
    
    provided_secret = request.headers.get("X-Cron-Secret", "")
    
    if provided_secret != expected_secret:
        logger.warning(
            f"🚨 Unauthorized cron request blocked. "
            f"Source: {request.client.host if request.client else 'unknown'}, "
            f"Path: {request.url.path}"
        )
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid cron secret")


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
    
    # Gather lightweight metrics for health response
    uptime = metrics.get_uptime()
    
    if healthy:
        return {
            "status": "healthy",
            "service": "constitution-agent",
            "version": "1.0.0",
            "environment": settings.environment,
            "uptime": uptime["uptime_human"],
            "checks": {
                "firestore": "ok"
            },
            "metrics_summary": {
                "checkins_total": metrics.get_counter("checkins_total"),
                "commands_total": metrics.get_counter("commands_total"),
                "errors_total": metrics.get_error_count(),
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


@app.get("/admin/metrics")
async def admin_metrics(request: Request):
    """
    Full metrics endpoint for monitoring and debugging.
    
    Returns detailed counters, latency percentiles, error breakdown,
    and recent error log. Intended for admin use and monitoring systems.
    
    Authentication: Requires admin_telegram_id as query parameter.
    In production, this should be behind a VPN or IAP.
    
    Returns:
        dict: Full metrics summary
    """
    # Simple auth: check query param against admin IDs
    admin_id = request.query_params.get("admin_id", "")
    admin_ids = [aid.strip() for aid in settings.admin_telegram_ids.split(",") if aid.strip()]
    
    if not admin_ids or admin_id not in admin_ids:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return metrics.get_summary()


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
    start_time = time.monotonic()
    
    try:
        # Get update data from request body
        update_data = await request.json()
        
        logger.debug(f"Received update: {update_data.get('update_id', 'unknown')}")
        
        # Convert to Telegram Update object
        update = Update.de_json(update_data, bot_manager.bot)
        
        # Process update with bot
        await bot_manager.application.process_update(update)
        
        # Record webhook latency
        elapsed_ms = (time.monotonic() - start_time) * 1000
        metrics.record_latency("webhook_latency", elapsed_ms)
        metrics.increment("webhooks_total")
        
        return {"ok": True}
        
    except Exception as e:
        # Record error in metrics
        elapsed_ms = (time.monotonic() - start_time) * 1000
        metrics.record_latency("webhook_latency", elapsed_ms)
        metrics.record_error("webhook", str(e))
        
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
    
    # Authenticate cron request (blocks unauthorized access)
    verify_cron_request(request)
    
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    logger.info(f"📡 Pattern scan triggered by: {scheduler_header or 'manual/unknown'}")
    
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
                                            
                                            # Phase C: Enhanced ghosting alert with partner context
                                            partner_streak = partner.streaks.current_streak
                                            partner_msg = (
                                                f"🚨 <b>Accountability Partner Alert</b>\n\n"
                                                f"Your partner <b>{user.name}</b> hasn't checked in for <b>{days_missing} days</b>.\n\n"
                                                f"📊 Their streak before ghosting: {user.streaks.current_streak} days\n"
                                                f"📅 Last check-in: {last_checkin}\n\n"
                                                f"This is serious. Consider reaching out to check on them:\n"
                                                f"• Text them directly\n"
                                                f"• Call if you have their number\n"
                                                f"• Make sure they're okay\n\n"
                                                f"Sometimes people need a friend more than a bot.\n\n"
                                                f"🔥 Your own streak: {partner_streak} days — keep showing up!\n"
                                                f"Use /partner_status to see full partner dashboard."
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
    verify_cron_request(request)
    
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
                    f"🔔 <b>Daily Check-In Time!</b>\n\n"
                    f"Hey {user.name}! It's 9 PM - time for your daily check-in.\n\n"
                    f"🔥 Current streak: {user.streaks.current_streak} days\n"
                    f"🎯 Mode: {user.constitution_mode.title()}\n\n"
                    f"Ready to keep the momentum going?\n\n"
                    f"Use /checkin to start! 💪"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode='HTML'
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
    verify_cron_request(request)
    
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
                    f"👋 <b>Still There?</b>\n\n"
                    f"Hey {user.name}, your daily check-in is waiting!\n\n"
                    f"🔥 Don't break your {user.streaks.current_streak}-day streak\n"
                    f"⏰ Check-in closes at midnight\n\n"
                    f"Just takes 2 minutes: /checkin"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode='HTML'
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
    verify_cron_request(request)
    
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
                    f"⚠️ <b>URGENT: Check-In Closing Soon!</b>\n\n"
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
                    f"<b>Don't let one missed day undo {user.streaks.current_streak} days of work.</b>\n\n"
                    f"Check in NOW: /checkin"
                )
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode='HTML'
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


# ===== Phase B: Timezone-Aware Unified Reminder =====

@app.post("/cron/reminder_tz_aware")
async def reminder_tz_aware(request: Request):
    """
    Timezone-aware unified reminder endpoint (Phase B).
    
    <b>Architecture:</b>
    Instead of 3 fixed IST endpoints, this single endpoint is called
    by Cloud Scheduler every 15 minutes. Each invocation:
    
    1. Checks which of our catalog timezones are currently at 9:00 PM,
       9:30 PM, or 10:00 PM (within 15-minute tolerance)
    2. Fetches users in those timezones who haven't checked in today
    3. Sends the appropriate reminder (first/second/third) based on
       which target time matched
    
    <b>Why 15-minute intervals?</b>
    - Timezone offsets come in 15/30/45/60 minute increments
    - 15 minutes captures all offsets without duplication
    - Cloud Scheduler fires 96 times/day (cheap & reliable)
    
    <b>Why keep the old endpoints?</b>
    - Backward compatibility during migration
    - Fallback if the new system has issues
    - Can be deprecated once bucket system is proven
    
    <b>Reminder tiers (in user's local time):</b>
    - 21:00 → First reminder (friendly)
    - 21:30 → Second reminder (nudge)
    - 22:00 → Third reminder (urgent)
    
    Returns:
        dict: Summary of timezones matched, users found, reminders sent
    """
    verify_cron_request(request)
    
    from src.utils.timezone_utils import (
        get_timezones_at_local_time,
        get_current_date,
        get_timezone_display_name
    )
    
    utc_now = datetime.utcnow().replace(tzinfo=None)
    # Make it timezone-aware for the helper
    import pytz
    utc_now_aware = pytz.UTC.localize(utc_now)
    
    logger.info(f"🌍 Timezone-aware reminder scan at UTC {utc_now.strftime('%H:%M')}")
    
    # Define reminder tiers: (target_hour, target_minute, tier_name, message_generator)
    reminder_tiers = [
        (21, 0, "first"),
        (21, 30, "second"),
        (22, 0, "third"),
    ]
    
    total_sent = 0
    total_errors = 0
    matched_info = []
    
    try:
        for target_hour, target_minute, tier_name in reminder_tiers:
            # Find timezones where local time matches this tier
            matching_tzs = get_timezones_at_local_time(
                utc_now_aware, target_hour, target_minute, tolerance_minutes=7
            )
            
            if not matching_tzs:
                continue
            
            logger.info(
                f"⏰ {tier_name} reminder: {len(matching_tzs)} timezones at "
                f"{target_hour}:{target_minute:02d} → {matching_tzs}"
            )
            
            # Get users in these timezones
            users = firestore_service.get_users_by_timezones(matching_tzs)
            
            for user in users:
                try:
                    user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
                    user_today = get_current_date(user_tz)
                    
                    # Skip if already checked in today
                    if firestore_service.checkin_exists(user.user_id, user_today):
                        continue
                    
                    # Skip if this tier's reminder already sent today
                    reminder_status = firestore_service.get_reminder_status(user.user_id, user_today)
                    if reminder_status and reminder_status.get(f"{tier_name}_sent"):
                        continue
                    
                    # Build message based on tier
                    if tier_name == "first":
                        message = (
                            f"🔔 <b>Daily Check-In Time!</b>\n\n"
                            f"Hey {user.name}! It's 9 PM — time for your daily check-in.\n\n"
                            f"🔥 Current streak: {user.streaks.current_streak} days\n"
                            f"🎯 Mode: {user.constitution_mode.title()}\n\n"
                            f"Ready to keep the momentum going?\n\n"
                            f"Use /checkin to start!"
                        )
                    elif tier_name == "second":
                        message = (
                            f"👋 <b>Still There?</b>\n\n"
                            f"Hey {user.name}, your daily check-in is waiting!\n\n"
                            f"🔥 Don't break your {user.streaks.current_streak}-day streak\n"
                            f"⏰ Check-in closes at midnight\n\n"
                            f"Just takes 2 minutes: /checkin"
                        )
                    else:  # third
                        message = (
                            f"⚠️ <b>URGENT: Check-In Closing Soon!</b>\n\n"
                            f"⏰ Only 2 hours left until midnight!\n"
                            f"🔥 Your {user.streaks.current_streak}-day streak is at risk\n\n"
                        )
                        if user.streak_shields.available > 0:
                            message += (
                                f"🛡️ You have {user.streak_shields.available} streak shield(s) available\n"
                                f"   (Use if you absolutely can't check in tonight)\n\n"
                            )
                        else:
                            message += f"🛡️ No streak shields remaining — this is critical!\n\n"
                        message += (
                            f"<b>Don't let one missed day undo {user.streaks.current_streak} days of work.</b>\n\n"
                            f"Check in NOW: /checkin"
                        )
                    
                    await bot_manager.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode='HTML'
                    )
                    
                    firestore_service.set_reminder_sent(user.user_id, user_today, tier_name)
                    total_sent += 1
                    
                    logger.info(f"✅ Sent {tier_name} reminder to {user.user_id} ({user.name}, tz={user_tz})")
                    
                except Exception as e:
                    logger.error(f"❌ Failed {tier_name} reminder for {user.user_id}: {e}")
                    total_errors += 1
            
            matched_info.append({
                "tier": tier_name,
                "target_time": f"{target_hour}:{target_minute:02d}",
                "matched_timezones": matching_tzs,
                "users_found": len(users)
            })
        
        result = {
            "status": "tz_aware_reminders_complete",
            "utc_time": utc_now.strftime("%H:%M"),
            "timestamp": datetime.utcnow().isoformat(),
            "tiers_matched": matched_info,
            "total_reminders_sent": total_sent,
            "total_errors": total_errors
        }
        
        logger.info(f"🌍 TZ-aware reminder complete: {total_sent} sent, {total_errors} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ TZ-aware reminder failed: {e}", exc_info=True)
        raise HTTPException(500, f"TZ-aware reminder failed: {str(e)}")


# ===== Phase 3E: Quick Check-In Reset =====

@app.post("/cron/reset_quick_checkins")
async def reset_quick_checkins(request: Request):
    """
    Reset quick check-in counters every Monday 12:00 AM IST (Phase 3E).
    
    <b>Purpose:</b>
    - Quick check-ins limited to 2 per week
    - Counter resets every Monday to give users a fresh start
    - Tracks history of which dates were used
    
    <b>Triggered by:</b> Cloud Scheduler (weekly, Monday 00:00 IST)
    
    <b>Process:</b>
    1. Get all users
    2. Reset quick_checkin_count to 0
    3. Clear quick_checkin_used_dates (optional: keep for history)
    4. Update quick_checkin_reset_date to next Monday
    
    Returns:
        dict: Reset results (users processed)
    """
    verify_cron_request(request)
    
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
    
    <b>Process:</b>
    1. Iterate over all active users
    2. For each user: generate 4 graphs + AI insights
    3. Send report via Telegram (text + 4 images)
    4. Return aggregate results
    
    <b>Performance Considerations:</b>
    - Reports are generated sequentially (Telegram rate limits: 30 msg/s)
    - Each report takes ~5-15 seconds (graph generation + LLM call)
    - For 10 users: ~2.5 minutes total
    - Cloud Run timeout: 300s (5 minutes) - sufficient for 20+ users
    
    <b>Cost:</b>
    - Graph generation: $0.00 (matplotlib)
    - AI insights: ~$0.003/month (300 tokens × 40 reports)
    - Cloud Scheduler: $0.10/month per job
    
    Returns:
        dict: Aggregate report results
    """
    verify_cron_request(request)
    
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
    
    Logs error, records in metrics, and returns 500 response.
    """
    metrics.record_error("unhandled", str(exc))
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
