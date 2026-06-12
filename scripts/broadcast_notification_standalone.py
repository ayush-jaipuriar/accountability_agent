#!/usr/bin/env python3
"""
Standalone Broadcast Notification Script
========================================

Sends update notification to all users without importing project modules.
Uses Firestore REST API + Telegram Bot API directly.

Usage:
    python3 scripts/broadcast_notification_standalone.py
"""

import subprocess
import json
import time
import asyncio
import httpx

PROJECT_ID = "accountability-agent"
BOT_TOKEN = "8197561499:AAEhBUhrnAbnbSSMCBq08-xWWyIDlwZoRdk"
FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
TELEGRAM_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

MESSAGE = (
    "✨ <b>Accountability Agent v2.1 is live — frictionless mobile check-ins and compounded consistency!</b>\n\n"
    "Here is what's new in this update:\n\n"
    "📱 <b>Frictionless Mobile Check-ins</b>\n"
    "We have eliminated tedious text entry. Check-ins now use instant button taps (1–10) to rate your <b>Constitution Alignment</b>, <b>Energy</b>, and <b>Mood</b>. The final reflection note is entirely optional—write a quick sentence or tap <b>'Finish Check-In'</b> to skip and finish instantly!\n\n"
    "🧠 <b>AI-Powered Reflections</b>\n"
    "If you do decide to write a quick reflection note, our Gemini engine automatically parses it behind the scenes to extract tomorrow's priorities and obstacles, keeping your logs detailed without the typing friction.\n\n"
    "😴 <b>Streak Preservation via Micro-Habits</b>\n"
    "On extremely busy or difficult days, the bot now lets you log a 'micro-habit' target to preserve your streak:\n"
    "• <b>Sleep:</b> 6+ hours\n"
    "• <b>Deep Work / Skill Building:</b> 30+ minutes\n"
    "Hitting these lower bounds keeps your momentum alive and prevents complete habit abandonment.\n\n"
    "💪 <b>Scheduled Rest Days</b>\n"
    "Scheduled rest days no longer penalize your compliance score or break streaks. Recovery is an active part of growth!\n\n"
    "Questions or feedback? Just reply directly to this message.\n"
    "Let's maintain the momentum together!"
)


def get_gcloud_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


async def get_all_users(client: httpx.AsyncClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FIRESTORE_BASE}/users?pageSize=1000"
    
    users = []
    while url:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        for doc in data.get("documents", []):
            fields = doc.get("fields", {})
            telegram_id = fields.get("telegram_id", {}).get("integerValue") or fields.get("telegram_id", {}).get("stringValue")
            user_id = fields.get("user_id", {}).get("stringValue")
            name = fields.get("name", {}).get("stringValue", "User")
            
            if telegram_id:
                users.append({
                    "telegram_id": int(telegram_id) if telegram_id.isdigit() else telegram_id,
                    "user_id": user_id,
                    "name": name
                })
        
        url = data.get("nextPageToken")
        if url:
            url = f"{FIRESTORE_BASE}/users?pageSize=1000&pageToken={url}"
    
    return users


async def send_message(client: httpx.AsyncClient, chat_id, text: str):
    url = f"{TELEGRAM_BASE}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()


async def main():
    print("🚀 Starting broadcast notification...")
    
    token = get_gcloud_token()
    print("✅ GCP token obtained")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        users = await get_all_users(client, token)
        print(f"📋 Found {len(users)} users to notify")
        
        sent = 0
        failed = 0
        start_time = time.time()
        
        for user in users:
            try:
                await send_message(client, user["telegram_id"], MESSAGE)
                sent += 1
                print(f"✅ Sent to {user['user_id']} ({user['name']})")
            except Exception as e:
                failed += 1
                print(f"❌ Failed to send to {user['user_id']}: {e}")
            
            # Rate limiting: ~25 msg/sec max
            await asyncio.sleep(0.04)
        
        duration = time.time() - start_time
        print("=" * 60)
        print(f"📊 Broadcast Complete")
        print(f"   Total users: {len(users)}")
        print(f"   Sent: {sent}")
        print(f"   Failed: {failed}")
        print(f"   Duration: {duration:.1f}s")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
