from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class SettingsUpdate(BaseModel):
    is_active: bool
    image_prompt: str
    negative_prompt: str
    run_interval_hours: int
    story_automation: bool = False
    
class SettingsResponse(SettingsUpdate):
    id: int

    class Config:
        from_attributes = True

class PostHistoryResponse(BaseModel):
    id: int
    timestamp: datetime
    status: str
    image_url: Optional[str] = None
    ig_post_id: Optional[str] = None
    caption: Optional[str] = None
    error_log: Optional[str] = None

    class Config:
        from_attributes = True


# --- Comment Reply System Schemas ---

class CommentReplySettingsUpdate(BaseModel):
    is_active: bool
    max_replies_per_day: int = 15
    min_delay_seconds: int = 10
    max_delay_seconds: int = 30
    monitor_recent_posts: int = 5
    reply_style: str = "friendly, casual influencer — short, warm, and engaging"

class CommentReplySettingsResponse(CommentReplySettingsUpdate):
    id: int

    class Config:
        from_attributes = True

class RepliedCommentResponse(BaseModel):
    id: int
    comment_id: str
    post_id: Optional[str] = None
    comment_text: Optional[str] = None
    comment_username: Optional[str] = None
    reply_text: Optional[str] = None
    reply_id: Optional[str] = None
    status: str
    replied_at: datetime

    class Config:
        from_attributes = True

class CommentReplyLogResponse(BaseModel):
    id: int
    comment_id: Optional[str] = None
    post_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class CommentReplyStatsResponse(BaseModel):
    replies_today: int
    skipped_today: int
    errors_today: int
    total_replies: int
    daily_limit: int
