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
from services.dm_replier import handle_incoming_dm

logger = logging.getLogger(__name__)
router = APIRouter()

# This token is used by Meta to verify your webhook endpoint.
# Set it to anything you want, but keep it consistent with Meta Dashboard.
WEBHOOK_VERIFY_TOKEN = "instagram_nature_bot_2026"


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
                    message = event.get("message", {})
                    message_text = message.get("text", "")
                    
                    # Skip if no text (could be image/sticker/etc)
                    if not message_text:
                        logger.info(f"Non-text message from {sender_id}, skipping.")
                        continue
                    
                    # Skip echo messages (messages sent BY the page itself)
                    if message.get("is_echo"):
                        continue
                    
                    # Handle the DM with AI
                    handle_incoming_dm(sender_id, message_text)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}
