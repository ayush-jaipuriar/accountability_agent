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
                
                # Run pattern detection
                patterns = pattern_agent.detect_patterns(checkins)
                
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
