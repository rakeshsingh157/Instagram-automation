from apscheduler.schedulers.background import BackgroundScheduler
import traceback
from datetime import datetime, timedelta
from core.database import SessionLocal
from models.models import BotSettings, PostHistory, CommentReplySettings
from services.ai_generator import generate_image
from services.captioner import generate_caption
from services.instagram import post_image_to_instagram, post_reels_to_instagram, post_video_to_story, post_image_to_story
from services.cloudinary_service import upload_image_to_cloudinary
import logging
from core.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _should_post_reel(db) -> bool:
    """
    Check if it's time to post a weekly reel.
    Returns True if the last reel was posted 7+ days ago (or never).
    """
    last_reel = (
        db.query(PostHistory)
        .filter(PostHistory.post_type == "reel", PostHistory.status == "Success")
        .order_by(PostHistory.timestamp.desc())
        .first()
    )
    
    if not last_reel:
        # Never posted a reel before — post one now
        return True
    
    days_since = (datetime.utcnow() - last_reel.timestamp.replace(tzinfo=None)).days
    logger.info(f"Days since last reel: {days_since}")
    return days_since >= 7


def bot_pipeline_job(force: bool = False):
    """
    The main job that runs the entire sequence.
    Posting strategy:
    - Default: Post an AI-generated nature IMAGE.
    - Once per week: Post an inspirational nature REEL (via JSON2Video).
    """
    db = SessionLocal()
    try:
        # 1. Fetch config
        cfg = db.query(BotSettings).first()
        if not cfg:
            logger.warning("BotSettings empty. Creating default config...")
            cfg = BotSettings()
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
            
        if not cfg.is_active and not force:
            logger.info("Scheduler skipped: Bot is inactive and not forced.")
            return

        logger.info("Starting automation pipeline...")
        
        # 2. Decide: Image post or Weekly Reel?
        post_reel = _should_post_reel(db)
        
        if post_reel:
            # === WEEKLY REEL via JSON2Video ===
            logger.info("Posting WEEKLY REEL (JSON2Video with AI images + voiceover)...")
            _post_reel_pipeline(db)
        else:
            # === DAILY IMAGE POST ===
            logger.info("Posting IMAGE (AI-generated nature photo)...")
            _post_image_pipeline(db, cfg)

    except Exception as e:
        error_msg = str(e) + "\n" + traceback.format_exc()
        logger.error(f"Pipeline failed: {error_msg}")
        log = PostHistory(status="Failed", error_log=error_msg)
        db.add(log)
        db.commit()
    finally:
        db.close()


def _post_image_pipeline(db, cfg):
    """Posts an AI-generated nature image to Instagram."""
    # Generate AI-enhanced image prompt
    from services.captioner import generate_image_prompt
    ai_prompt = generate_image_prompt(cfg.image_prompt)
    logger.info(f"AI-enhanced prompt: {ai_prompt[:100]}...")
    
    image_path = generate_image(ai_prompt, cfg.negative_prompt)
    logger.info(f"Image generated at {image_path}")
    
    # Generate caption
    caption = generate_caption()
    
    # Upload to Cloudinary and post
    public_image_url = upload_image_to_cloudinary(image_path)
    ig_media_id = post_image_to_instagram(public_image_url, caption)
    logger.info(f"Successfully posted IMAGE to Instagram Feed! Media ID: {ig_media_id}")
    
    # Also post to Story if enabled
    if cfg.story_automation:
        try:
            story_id = post_image_to_story(public_image_url)
            logger.info(f"Successfully posted IMAGE to Instagram Story! Media ID: {story_id}")
        except Exception as e:
            logger.error(f"Failed to post image to story: {e}")
    
    # Log success
    log = PostHistory(
        status="Success",
        post_type="image",
        image_url=image_path,
        ig_post_id=ig_media_id,
        caption=caption
    )
    db.add(log)
    db.commit()


def _post_reel_pipeline(db):
    """Creates and posts an inspirational nature reel via JSON2Video."""
    from services.json2video_service import create_reel_video
    
    # Generate the reel video (AI images + voiceover + music)
    video_url = create_reel_video()
    
    if not video_url:
        raise Exception("JSON2Video reel generation failed — no video URL returned.")
    
    logger.info(f"Reel video ready: {video_url}")
    
    # Generate a caption for the reel
    caption = generate_caption()
    
    # Post directly to Instagram (JSON2Video gives us a public URL already)
    ig_media_id = post_reels_to_instagram(video_url, caption)
    logger.info(f"Successfully posted REEL to Instagram Feed! Media ID: {ig_media_id}")
    
    # Also post to Story if enabled
    # We fetch cfg to check story_automation flag
    cfg = db.query(BotSettings).first()
    if cfg and cfg.story_automation:
        try:
            story_id = post_video_to_story(video_url)
            logger.info(f"Successfully posted REEL to Instagram Story! Media ID: {story_id}")
        except Exception as e:
            logger.error(f"Failed to post reel to story: {e}")
    
    # Log success
    log = PostHistory(
        status="Success",
        post_type="reel",
        video_path=video_url,
        ig_post_id=ig_media_id,
        caption=caption
    )
    db.add(log)
    db.commit()


def comment_reply_job():
    """
    Scheduled job for the comment reply system.
    Runs independently of the content posting pipeline.
    """
    from services.comment_replier import run_comment_reply_pipeline
    
    logger.info("Comment reply scheduled job triggered.")
    try:
        run_comment_reply_pipeline(force=False)
    except Exception as e:
        logger.error(f"Comment reply job failed: {e}\n{traceback.format_exc()}")


def start_scheduler():
    db = SessionLocal()
    cfg = db.query(BotSettings).first()
    db.close()
    
    interval = cfg.run_interval_hours if cfg else 24
    
    # Content posting job
    scheduler.add_job(
        bot_pipeline_job, 'interval', 
        hours=interval, id='main_job', 
        replace_existing=True
    )
    
    # Comment reply job — runs every 3 hours
    scheduler.add_job(
        comment_reply_job, 'interval', 
        hours=3, id='comment_reply_job', 
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(
        f"Scheduler started: content posting every {interval}h, "
        f"comment replies every 3h. Reels post once per week."
    )

def update_scheduler_interval(hours: int):
    scheduler.reschedule_job('main_job', trigger='interval', hours=hours)
    logger.info(f"Scheduler interval updated to {hours} hours.")
