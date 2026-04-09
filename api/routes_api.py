from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from models.models import BotSettings, PostHistory
from schemas.schemas import SettingsUpdate, SettingsResponse, PostHistoryResponse
from core.security import get_current_user
from services.scheduler import bot_pipeline_job, update_scheduler_interval

router = APIRouter()

# --- Config & Settings ---
@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), _: bool = Depends(get_current_user)):
    cfg = db.query(BotSettings).first()
    if not cfg:
        # Create default config initially
        cfg = BotSettings()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

@router.put("/settings", response_model=SettingsResponse)
def update_settings(settings_update: SettingsUpdate, db: Session = Depends(get_db), _: bool = Depends(get_current_user)):
    cfg = db.query(BotSettings).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Settings not found")
        
    cfg.is_active = settings_update.is_active
    cfg.image_prompt = settings_update.image_prompt
    cfg.negative_prompt = settings_update.negative_prompt
    cfg.story_automation = settings_update.story_automation
    
    if cfg.run_interval_hours != settings_update.run_interval_hours:
        update_scheduler_interval(settings_update.run_interval_hours)
    
    cfg.run_interval_hours = settings_update.run_interval_hours

    db.commit()
    db.refresh(cfg)
    return cfg

# --- Post History ---
@router.get("/history", response_model=List[PostHistoryResponse])
def get_history(limit: int = 10, db: Session = Depends(get_db), _: bool = Depends(get_current_user)):
    logs = db.query(PostHistory).order_by(PostHistory.timestamp.desc()).limit(limit).all()
    return logs

# --- Manual Trigger (Dashboard Form) ---
@router.post("/trigger")
def manual_trigger(background_tasks: BackgroundTasks, _: bool = Depends(get_current_user)):
    background_tasks.add_task(bot_pipeline_job, force=True)
    return {"message": "Pipeline started in the background."}

# --- Independent Manual Triggers (Unauthenticated GET) ---
@router.get("/trigger/feed/image")
def trigger_feed_image(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Instantly posts an AI Image to the Feed (and story if enabled)."""
    cfg = db.query(BotSettings).first()
    from services.scheduler import _post_image_pipeline
    background_tasks.add_task(_post_image_pipeline, db, cfg)
    return {"message": "AI Image -> Feed generation started."}

@router.get("/trigger/feed/video")
def trigger_feed_video(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Instantly posts an AI Reel to the Feed (and story if enabled)."""
    from services.scheduler import _post_reel_pipeline
    background_tasks.add_task(_post_reel_pipeline, db)
    return {"message": "AI Reel -> Feed generation started."}

@router.get("/trigger/story/image")
def trigger_story_image(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Instantly posts an AI Image ONLY to the Story (bypassing Feed completely)."""
    cfg = db.query(BotSettings).first()
    def _only_story_image(db, cfg):
        from services.ai_generator import generate_image
        from services.captioner import generate_image_prompt
        from services.cloudinary_service import upload_image_to_cloudinary
        from services.instagram import post_image_to_story
        import logging
        logger = logging.getLogger(__name__)

        ai_prompt = generate_image_prompt(cfg.image_prompt)
        image_path = generate_image(ai_prompt, cfg.negative_prompt)
        public_image_url = upload_image_to_cloudinary(image_path)
        try:
            story_id = post_image_to_story(public_image_url)
            logger.info(f"[Manual Trigger] Image posted directly to Story! ID: {story_id}")
        except Exception as e:
            logger.error(f"[Manual Trigger] Story Image Error: {e}")
            
    background_tasks.add_task(_only_story_image, db, cfg)
    return {"message": "AI Image -> Story generation started."}

@router.get("/trigger/story/video")
def trigger_story_video(background_tasks: BackgroundTasks):
    """Instantly posts an AI Video ONLY to the Story (bypassing Feed completely)."""
    def _only_story_video():
        from services.json2video_service import create_reel_video
        from services.instagram import post_video_to_story
        import logging
        logger = logging.getLogger(__name__)

        video_url = create_reel_video()
        if video_url:
            try:
                story_id = post_video_to_story(video_url)
                logger.info(f"[Manual Trigger] Reel posted directly to Story! ID: {story_id}")
            except Exception as e:
                logger.error(f"[Manual Trigger] Story Video Error: {e}")
                
    background_tasks.add_task(_only_story_video)
    return {"message": "AI Reel -> Story generation started."}

@router.get("/trigger/comments")
def trigger_comments(background_tasks: BackgroundTasks):
    """Instantly runs the AI Comment Responder."""
    from services.scheduler import comment_reply_job
    background_tasks.add_task(comment_reply_job)
    return {"message": "AI Comment Pipeline task started."}
