"""
Instagram DM Auto-Reply Service — AI-powered replies to direct messages.
Uses Meta's Messenger Platform API with Webhooks + Sarvam AI for response generation.
Now includes database-backed conversation history for context-aware replies!
"""

import requests
import logging
import re
from core.config import settings
from core.database import SessionLocal
from models.models import DMChatHistory

logger = logging.getLogger(__name__)


def get_instagram_username(sender_id: str) -> str:
    """Fetches the sender's Instagram username using the Graph API."""
    url = f"https://graph.facebook.com/v19.0/{sender_id}?fields=name,username&access_token={settings.INSTAGRAM_ACCESS_TOKEN}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('username') or data.get('name') or "a user"
    except Exception as e:
        logger.warning(f"Could not fetch username for {sender_id}: {e}")
    return "a user"


def _chat_with_free_ai(messages_list: list) -> str | None:
    """Sends native chat history array to a powerful free AI model (Pollinations)."""
    try:
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "model": "openai", # Maps to the smartest conversational model available
            "messages": messages_list,
            "jsonMode": False
        }

        # text.pollinations.ai returns the raw string body, not a nested JSON object like OpenAI!
        response = requests.post("https://text.pollinations.ai/", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.text.strip()
        logger.error(f"Free AI chat failed: {response.text}")
    except Exception as e:
        logger.error(f"Free API exception: {e}")
    return None


def generate_dm_reply(sender_id: str, new_message: str) -> str:
    """
    Generate an AI reply using true conversational arrays and robust models.
    """
    system_prompt = """You are "Nature Vibes" — an enthusiastic nature and landscape photography Instagram page.
Rules:
- You are chatting in Instagram DMs. Be brief (1-3 sentences max).
- Use warm, casual language with emojis.
- Give a very direct, friendly reply to what the user said.
- NEVER introduce yourself. NEVER say "I'm [anything]" or "My name is [anything]".
- NEVER use placeholder text like "[Your Name]" or "[anything in brackets]".
- Do NOT start conversations with greetings or introductions — just respond naturally to their message.
- If someone says "hi" or "hello", just say hi back casually — don't give a speech about who you are."""

    # 1. Fetch conversation history from Database
    db = SessionLocal()
    sender_username = get_instagram_username(sender_id)
    
    # Initialize the messages list with system instructions
    ai_messages = [
        {"role": "system", "content": system_prompt + f"\nInfo: The person you are talking to is named '{sender_username}'."}
    ]
    
    try:
        # Fetch RECENT 5 messages for memory
        past_msgs = db.query(DMChatHistory).filter(
            DMChatHistory.sender_id == sender_id
        ).order_by(DMChatHistory.timestamp.desc()).limit(5).all()
        past_msgs.reverse()
        
        for msg in past_msgs:
            actual_role = "user" if msg.role == "user" else "assistant"
            ai_messages.append({"role": actual_role, "content": msg.message_text})
            
    finally:
        db.close()

    # Add the current new message 
    ai_messages.append({"role": "user", "content": new_message})

    logger.info(f"Generating native chat reply for user: {sender_username} (Total msgs in context: {len(ai_messages)})")

    # 2. Call AI natively 
    ai_reply = _chat_with_free_ai(ai_messages)
    
    logger.info(f"== RAW AI OUTPUT ==\n{ai_reply}\n===================")

    if ai_reply:
        # Clean up
        reply = ai_reply.strip().strip('"').strip("'")
        
        logger.info(f"== CLEANED AI OUTPUT ==\n{reply}\n=======================")
        
        if reply:
            return reply[:980] # Instagram STRICTLY limits DMs to 1000 characters

    logger.warning("AI reply was completely empty after cleaning. Triggering fallback.")

    # Absolute Fallback 
    return "Hey! Thanks for reaching out 🌿 I appreciate you connecting with me! 😊"


def send_dm_reply(recipient_id: str, message_text: str) -> dict:
    url = f"https://graph.facebook.com/v19.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            logger.info(f"DM sent to {recipient_id}: {message_text[:50]}...")
            return response.json()
        else:
            logger.error(f"Failed to send DM: {response.status_code} {response.text}")
            return {"error": response.text}
    except Exception as e:
        logger.error(f"DM send error: {e}")
        return {"error": str(e)}


def handle_incoming_dm(sender_id: str, message_text: str) -> str:
    """
    Full pipeline: receive a DM → save to DB → generate contextual AI reply → save reply to DB → send back.
    """
    logger.info(f"Incoming DM from {sender_id}: {message_text[:100]}")
    
    db = SessionLocal()
    try:
        # 1. Save user's incoming message to DB
        user_msg = DMChatHistory(sender_id=sender_id, role="user", message_text=message_text)
        db.add(user_msg)
        db.commit()
    
        # 2. Generate AI reply (Passing the sender ID to fetch context)
        reply = generate_dm_reply(sender_id, message_text)
        logger.info(f"AI Contextual Reply: {reply[:100]}")
        
        # 3. Save AI's outgoing reply to DB
        ai_msg = DMChatHistory(sender_id=sender_id, role="ai", message_text=reply)
        db.add(ai_msg)
        db.commit()
        
    finally:
        db.close()
    
    # 4. Actually send it via Meta API
    send_dm_reply(sender_id, reply)
    
    return reply
