"""
Comment Replier — Core pipeline that orchestrates the entire comment reply flow.

Pipeline:
1. Check daily limit
2. Fetch recent posts from Instagram
3. Fetch comments for each post
4. Filter: skip duplicates, spam, abuse, short, emoji-only
5. Prioritize & randomly select a subset
6. Generate AI reply for each selected comment
7. Post reply via Instagram API
8. Log everything to DB
9. Retry failed replies (up to 2 retries)
"""

import requests
import random
import time
import traceback
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from core.config import settings
from core.database import SessionLocal
from models.models import RepliedComment, CommentReplySettings, CommentReplyLog
from services.comment_filter import filter_comment
from services.reply_generator import generate_ai_reply

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


# ──────────────────────────────────────────────
#  Instagram Graph API helpers
# ──────────────────────────────────────────────

def fetch_recent_posts(limit: int = 5) -> list:
    """Fetch recent media posts from the Instagram page."""
    url = f"{GRAPH_API_BASE}/{settings.INSTAGRAM_PAGE_ID}/media"
    params = {
        "fields": "id,caption,timestamp,media_type",
        "limit": limit,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch posts: {resp.status_code} - {resp.text[:200]}")
            return []
        
        data = resp.json()
        posts = data.get("data", [])
        logger.info(f"Fetched {len(posts)} recent posts")
        return posts
        
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return []


def fetch_comments(media_id: str, limit: int = 100) -> list:
    """Fetch comments for a specific Instagram post."""
    url = f"{GRAPH_API_BASE}/{media_id}/comments"
    params = {
        "fields": "id,text,timestamp,username,replies{id,text,username,timestamp}",
        "limit": limit,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch comments for {media_id}: {resp.status_code} - {resp.text[:200]}")
            return []
        
        data = resp.json()
        comments = data.get("data", [])
        logger.info(f"Fetched {len(comments)} comments for post {media_id}")
        return comments
        
    except Exception as e:
        logger.error(f"Error fetching comments for {media_id}: {e}")
        return []


def post_reply_to_instagram(comment_id: str, reply_text: str) -> str | None:
    """Post a reply to a comment via Instagram Graph API."""
    url = f"{GRAPH_API_BASE}/{comment_id}/replies"
    payload = {
        "message": reply_text,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    
    try:
        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Failed to post reply to {comment_id}: {resp.status_code} - {resp.text[:200]}")
            return None
        
        reply_id = resp.json().get("id")
        logger.info(f"Successfully replied to comment {comment_id}, reply ID: {reply_id}")
        return reply_id
        
    except Exception as e:
        logger.error(f"Error posting reply to {comment_id}: {e}")
        return None


# ──────────────────────────────────────────────
#  Database helpers
# ──────────────────────────────────────────────

def is_already_replied(db, comment_id: str) -> bool:
    """Check if we've already replied to this comment."""
    existing = db.query(RepliedComment).filter(
        RepliedComment.comment_id == comment_id
    ).first()
    return existing is not None


def has_bot_reply_in_api(comment_data: dict) -> bool:
    """
    Check if the comment already has a reply from us by inspecting
    the replies sub-field from the API response.
    This is an extra safety check beyond the DB.
    """
    replies = comment_data.get("replies", {}).get("data", [])
    # We can't easily know our own username from the API,
    # so this is a supplementary check — the DB is the primary source of truth.
    return len(replies) > 0


def get_replies_today_count(db) -> int:
    """Count how many replies we've sent today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    count = db.query(RepliedComment).filter(
        RepliedComment.replied_at >= today_start,
        RepliedComment.status == "replied"
    ).count()
    return count


def log_action(db, comment_id: str, post_id: str, action: str, details: str = ""):
    """Log an action to the comment_reply_logs table."""
    log = CommentReplyLog(
        comment_id=comment_id,
        post_id=post_id,
        action=action,
        details=details[:500] if details else None,  # Truncate long details
    )
    db.add(log)
    db.commit()


def get_or_create_settings(db) -> CommentReplySettings:
    """Get comment reply settings, creating defaults if none exist."""
    cfg = db.query(CommentReplySettings).first()
    if not cfg:
        cfg = CommentReplySettings()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


# ──────────────────────────────────────────────
#  Main Pipeline
# ──────────────────────────────────────────────

def run_comment_reply_pipeline(force: bool = False):
    """
    Main orchestration function for the comment reply system.
    
    Steps:
    1. Check if active & daily limit
    2. Fetch posts → comments
    3. Filter & prioritize
    4. Randomly select subset
    5. Generate AI replies
    6. Post with random delays
    7. Log everything
    """
    db = SessionLocal()
    
    try:
        # --- 1. Check config ---
        cfg = get_or_create_settings(db)
        
        if not cfg.is_active and not force:
            logger.info("Comment reply system is inactive. Skipping.")
            return
        
        # --- 2. Check daily limit ---
        replies_today = get_replies_today_count(db)
        remaining = cfg.max_replies_per_day - replies_today
        
        if remaining <= 0:
            logger.info(
                f"Daily reply limit reached ({cfg.max_replies_per_day}). "
                f"Skipping until tomorrow."
            )
            return
        
        logger.info(
            f"Comment reply pipeline started. "
            f"Replies today: {replies_today}/{cfg.max_replies_per_day}, "
            f"remaining: {remaining}"
        )
        
        # --- 3. Fetch recent posts ---
        posts = fetch_recent_posts(limit=cfg.monitor_recent_posts)
        if not posts:
            logger.warning("No posts found. Exiting pipeline.")
            return
        
        # --- 4. Collect & filter all comments ---
        candidates = []  # List of (comment_data, post_data, filter_result)
        
        for post in posts:
            post_id = post["id"]
            post_caption = post.get("caption", "")
            
            comments = fetch_comments(post_id, limit=100)
            
            for comment in comments:
                comment_id = comment.get("id")
                comment_text = comment.get("text", "")
                comment_username = comment.get("username", "")
                
                if not comment_id or not comment_text:
                    continue
                
                # Check DB for duplicate
                if is_already_replied(db, comment_id):
                    log_action(db, comment_id, post_id, "skipped_duplicate", 
                              "Already replied (found in DB)")
                    continue
                
                # Optional: check API replies as extra safety
                if has_bot_reply_in_api(comment):
                    log_action(db, comment_id, post_id, "skipped_duplicate", 
                              "Already has replies (API check)")
                    # Also save to DB so we don't check again
                    record = RepliedComment(
                        comment_id=comment_id,
                        post_id=post_id,
                        comment_text=comment_text[:500],
                        comment_username=comment_username,
                        status="skipped",
                    )
                    db.add(record)
                    db.commit()
                    continue
                
                # Run through filter
                result = filter_comment(comment_text)
                
                if not result.should_reply:
                    log_action(db, comment_id, post_id, 
                              f"skipped_{result.reason.split(':')[0]}", 
                              result.reason)
                    continue
                
                candidates.append({
                    "comment": comment,
                    "post": post,
                    "filter_result": result,
                    "post_caption": post_caption,
                })
        
        if not candidates:
            logger.info("No eligible comments found to reply to.")
            return
        
        logger.info(f"Found {len(candidates)} eligible comments")
        
        # --- 5. Sort by priority (1=highest) and randomly select ---
        candidates.sort(key=lambda x: x["filter_result"].priority)
        
        # Take at most `remaining` comments, with some randomness
        # First, take all priority 1 (questions)
        # Then randomly sample from priority 2 and 3
        selected = []
        priority_1 = [c for c in candidates if c["filter_result"].priority == 1]
        others = [c for c in candidates if c["filter_result"].priority > 1]
        
        # Add questions first (they deserve replies)
        selected.extend(priority_1[:remaining])
        spots_left = remaining - len(selected)
        
        # Fill remaining spots with random selection from others
        if spots_left > 0 and others:
            random.shuffle(others)
            selected.extend(others[:spots_left])
        
        logger.info(
            f"Selected {len(selected)} comments to reply to "
            f"(questions: {len(priority_1)}, others: {len(others)})"
        )
        
        # --- 6. Reply with delays ---
        success_count = 0
        error_count = 0
        
        for i, candidate in enumerate(selected):
            comment = candidate["comment"]
            post = candidate["post"]
            fr = candidate["filter_result"]
            post_caption = candidate["post_caption"]
            
            comment_id = comment["id"]
            comment_text = comment.get("text", "")
            comment_username = comment.get("username", "")
            post_id = post["id"]
            
            try:
                # Generate AI reply
                reply_text = generate_ai_reply(
                    comment_text=comment_text,
                    post_caption=post_caption,
                    reply_style=cfg.reply_style,
                    priority=fr.priority,
                )
                
                if not reply_text:
                    log_action(db, comment_id, post_id, "error", 
                              "Failed to generate reply text")
                    error_count += 1
                    continue
                
                # Post reply with retries
                reply_id = None
                max_retries = 2
                
                for attempt in range(max_retries + 1):
                    reply_id = post_reply_to_instagram(comment_id, reply_text)
                    if reply_id:
                        break
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for comment {comment_id}"
                        )
                        time.sleep(5)  # Short delay before retry
                
                if reply_id:
                    try:
                        # Save to DB
                        record = RepliedComment(
                            comment_id=comment_id,
                            post_id=post_id,
                            comment_text=comment_text[:500],
                            comment_username=comment_username,
                            reply_text=reply_text,
                            reply_id=reply_id,
                            status="replied",
                        )
                        db.add(record)
                        db.commit()
                        
                        log_action(db, comment_id, post_id, "replied",
                                  f"Reply: '{reply_text[:100]}' | Reason: {fr.reason}")
                        success_count += 1
                    except IntegrityError:
                        db.rollback()
                        logger.warning(f"Duplicate detection for comment {comment_id} during commit. Skipping.")
                        log_action(db, comment_id, post_id, "skipped_duplicate", "Detected during database commit")
                        continue
                else:
                    # All retries failed
                    record = RepliedComment(
                        comment_id=comment_id,
                        post_id=post_id,
                        comment_text=comment_text[:500],
                        comment_username=comment_username,
                        reply_text=reply_text,
                        status="failed",
                    )
                    db.add(record)
                    db.commit()
                    
                    log_action(db, comment_id, post_id, "error",
                              f"All {max_retries + 1} attempts failed")
                    error_count += 1
                
                # --- 7. Random delay between replies (human simulation) ---
                if i < len(selected) - 1:  # Don't delay after the last one
                    delay = random.uniform(
                        cfg.min_delay_seconds, 
                        cfg.max_delay_seconds
                    )
                    logger.info(f"Waiting {delay:.1f}s before next reply...")
                    time.sleep(delay)
                    
            except Exception as e:
                db.rollback()  # Crucial: Reset session state after any failure
                error_msg = str(e)
                logger.error(f"Error processing comment {comment_id}: {error_msg}")
                try:
                    log_action(db, comment_id, post_id, "error", error_msg[:500])
                except:
                    db.rollback()
                error_count += 1
        
        logger.info(
            f"Comment reply pipeline complete. "
            f"Success: {success_count}, Errors: {error_count}, "
            f"Total today: {replies_today + success_count}/{cfg.max_replies_per_day}"
        )
        
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Comment reply pipeline crashed: {error_msg}")
    finally:
        db.close()
