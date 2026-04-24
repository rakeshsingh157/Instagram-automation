"""
Instagram Webhook API — Receives DM notifications from Meta and triggers AI auto-reply.

Setup required in Meta Developer Console:
1. Go to your App Dashboard → Products → Messenger → Settings
2. Set Callback URL to: https://your-server.com/api/v1/webhook
3. Set Verify Token to the same value as WEBHOOK_VERIFY_TOKEN below
4. Subscribe to: 'messages' field under Instagram
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
import logging
import time
from collections import OrderedDict
from core.config import settings
from services.dm_replier import handle_incoming_dm

logger = logging.getLogger(__name__)
router = APIRouter()

# This token is used by Meta to verify your webhook endpoint.
# Set it to anything you want, but keep it consistent with Meta Dashboard.
WEBHOOK_VERIFY_TOKEN = "instagram_nature_bot_2026"

# =============================================================================
# ANTI-LOOP PROTECTION
# =============================================================================
# 1. Deduplication cache: tracks recently processed message IDs (max 500 entries)
_processed_message_ids: OrderedDict = OrderedDict()
_MAX_CACHE_SIZE = 500

# 2. Per-sender cooldown: prevents replying to the same user more than once every N seconds
_sender_last_reply_time: dict = {}
_COOLDOWN_SECONDS = 5  # Minimum gap between replies to the same user


def _is_message_already_processed(message_id: str) -> bool:
    """Check if we've already processed this message ID (prevents duplicate webhooks)."""
    if message_id in _processed_message_ids:
        return True
    # Add to cache with current timestamp
    _processed_message_ids[message_id] = time.time()
    # Evict oldest entries if cache is too large
    while len(_processed_message_ids) > _MAX_CACHE_SIZE:
        _processed_message_ids.popitem(last=False)
    return False


def _is_sender_on_cooldown(sender_id: str) -> bool:
    """Check if we've replied to this sender too recently (prevents rapid-fire loops)."""
    now = time.time()
    last_time = _sender_last_reply_time.get(sender_id, 0)
    if now - last_time < _COOLDOWN_SECONDS:
        return True
    _sender_last_reply_time[sender_id] = now
    return False


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta's webhook verification (GET request).
    When you set up the webhook in Meta Dashboard, it sends a GET request
    with a challenge. You must return the challenge to verify.
    """
    if hub_mode == "subscribe" and hub_verify_token == WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    
    logger.warning(f"Webhook verification failed. Token: {hub_verify_token}")
    return PlainTextResponse(content="Verification failed", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receives incoming DM events from Instagram via Meta's webhook.
    Automatically generates and sends an AI reply.
    
    Multiple layers of protection against infinite reply loops:
    1. Skip echo messages (messages sent BY the page/bot itself)
    2. Skip messages where sender_id matches our own INSTAGRAM_PAGE_ID
    3. Skip messages we've already processed (deduplication by message ID)
    4. Per-sender cooldown to throttle rapid webhook bursts
    """
    try:
        body = await request.json()
        logger.info(f"Webhook received: {body}")
        
        # Meta sends events in this structure
        obj = body.get("object", "")
        
        if obj == "instagram":
            entries = body.get("entry", [])
            for entry in entries:
                messaging_events = entry.get("messaging", [])
                for event in messaging_events:
                    sender_id = event.get("sender", {}).get("id")
                    recipient_id = event.get("recipient", {}).get("id")
                    message = event.get("message", {})
                    message_text = message.get("text", "")
                    message_id = message.get("mid", "")
                    
                    # --- GUARD 1: Skip echo messages (messages sent BY the page itself) ---
                    if message.get("is_echo"):
                        logger.info(f"Skipping echo message from {sender_id} (is_echo=True)")
                        continue
                    
                    # --- GUARD 2: Skip if sender is our own page/bot ---
                    # This is the PRIMARY fix for the infinite loop.
                    # When the bot sends a DM, Instagram may fire a webhook where
                    # sender_id == our page ID. We must NOT reply to ourselves.
                    our_page_id = settings.INSTAGRAM_PAGE_ID
                    if sender_id and our_page_id and str(sender_id) == str(our_page_id):
                        logger.info(f"Skipping self-sent message (sender {sender_id} == page {our_page_id})")
                        continue
                    
                    # --- GUARD 3: Skip if no text (could be image/sticker/etc) ---
                    if not message_text:
                        logger.info(f"Non-text message from {sender_id}, skipping.")
                        continue
                    
                    # --- GUARD 4: Skip if this message ID was already processed ---
                    if message_id and _is_message_already_processed(message_id):
                        logger.info(f"Duplicate message {message_id} from {sender_id}, skipping.")
                        continue
                    
                    # --- GUARD 5: Skip if sender is on cooldown (too many messages too fast) ---
                    if _is_sender_on_cooldown(sender_id):
                        logger.info(f"Sender {sender_id} is on cooldown ({_COOLDOWN_SECONDS}s), skipping.")
                        continue
                    
                    # All guards passed — handle the DM with AI
                    logger.info(f"Processing DM from {sender_id}: {message_text[:100]}")
                    handle_incoming_dm(sender_id, message_text)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}
