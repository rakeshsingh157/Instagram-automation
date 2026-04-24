"""
API Routes for the Comment Reply System.

Endpoints:
  GET    /api/v1/comments/settings  — Get reply config
  PUT    /api/v1/comments/settings  — Update reply config
  GET    /api/v1/comments/history   — Replied comments history
  GET    /api/v1/comments/logs      — Action logs
  POST   /api/v1/comments/trigger   — Manual trigger
  GET    /api/v1/comments/stats     — Today's stats
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import threading
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone

from core.database import get_db
from core.security import get_current_user
from models.models import RepliedComment, CommentReplySettings, CommentReplyLog
from schemas.schemas import (
    CommentReplySettingsUpdate,
    CommentReplySettingsResponse,
    RepliedCommentResponse,
    CommentReplyLogResponse,
    CommentReplyStatsResponse,
)
from services.comment_replier import run_comment_reply_pipeline

router = APIRouter()


def _get_or_create_settings(db: Session) -> CommentReplySettings:
    cfg = db.query(CommentReplySettings).first()
    if not cfg:
        cfg = CommentReplySettings()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


# ── Settings ────────────────────────────────

@router.get("/settings", response_model=CommentReplySettingsResponse)
def get_comment_settings(
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user),
):
    return _get_or_create_settings(db)


@router.put("/settings", response_model=CommentReplySettingsResponse)
def update_comment_settings(
    update: CommentReplySettingsUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user),
):
    cfg = _get_or_create_settings(db)
    cfg.is_active = update.is_active
    cfg.max_replies_per_day = update.max_replies_per_day
    cfg.min_delay_seconds = update.min_delay_seconds
    cfg.max_delay_seconds = update.max_delay_seconds
    cfg.monitor_recent_posts = update.monitor_recent_posts
    cfg.reply_style = update.reply_style
    db.commit()
    db.refresh(cfg)
    return cfg


# ── History ─────────────────────────────────

@router.get("/history", response_model=List[RepliedCommentResponse])
def get_reply_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user),
):
    records = (
        db.query(RepliedComment)
        .order_by(RepliedComment.replied_at.desc())
        .limit(limit)
        .all()
    )
    return records


# ── Logs ────────────────────────────────────

@router.get("/logs", response_model=List[CommentReplyLogResponse])
def get_reply_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user),
):
    logs = (
        db.query(CommentReplyLog)
        .order_by(CommentReplyLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return logs


# ── Stats ───────────────────────────────────

@router.get("/stats", response_model=CommentReplyStatsResponse)
def get_reply_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user),
):
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    cfg = _get_or_create_settings(db)
    
    replies_today = db.query(RepliedComment).filter(
        RepliedComment.replied_at >= today_start,
        RepliedComment.status == "replied",
    ).count()
    
    skipped_today = db.query(CommentReplyLog).filter(
        CommentReplyLog.timestamp >= today_start,
        CommentReplyLog.action.like("skipped_%"),
    ).count()
    
    errors_today = db.query(CommentReplyLog).filter(
        CommentReplyLog.timestamp >= today_start,
        CommentReplyLog.action == "error",
    ).count()
    
    total_replies = db.query(RepliedComment).filter(
        RepliedComment.status == "replied"
    ).count()
    
    return CommentReplyStatsResponse(
        replies_today=replies_today,
        skipped_today=skipped_today,
        errors_today=errors_today,
        total_replies=total_replies,
        daily_limit=cfg.max_replies_per_day,
    )


# ── Manual Trigger ──────────────────────────

@router.post("/trigger")
def trigger_comment_replies(
    _: bool = Depends(get_current_user),
):
    thread = threading.Thread(
        target=run_comment_reply_pipeline, kwargs={"force": True}, daemon=True
    )
    thread.start()
    return {"message": "Comment reply pipeline started in the background."}
