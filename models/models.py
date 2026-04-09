from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.database import Base

class BotSettings(Base):
    __tablename__ = "bot_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=False)
    image_prompt = Column(Text, default="breathtaking landscape nature scene, mountains, forest, dramatic sky, golden hour lighting, professional photography, high quality, 4k")
    negative_prompt = Column(Text, default="ugly, blurry, low quality, text, watermark, humans, people, faces, portrait, nsfw, woman, girl, man, person, sexy, bikini, lingerie, clothes, models")
    run_interval_hours = Column(Integer, default=24) # Daily by default
    story_automation = Column(Boolean, default=False)

class PostHistory(Base):
    __tablename__ = "post_history"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(255), default="Success") # Success or Failed
    post_type = Column(String(50), default="image")  # "image" or "reel"
    image_url = Column(String(500), nullable=True)  # ImgBB URL
    video_path = Column(String(500), nullable=True) # Local path maybe
    ig_post_id = Column(String(255), nullable=True) # Instagram media ID
    caption = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)


class RepliedComment(Base):
    """Tracks every comment that has been replied to — prevents duplicates."""
    __tablename__ = "replied_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String(255), unique=True, nullable=False, index=True)
    post_id = Column(String(255), nullable=True)
    comment_text = Column(Text, nullable=True)
    comment_username = Column(String(255), nullable=True)
    reply_text = Column(Text, nullable=True)
    reply_id = Column(String(255), nullable=True)  # Instagram reply ID
    status = Column(String(50), default="replied")  # replied / skipped / failed
    replied_at = Column(DateTime(timezone=True), server_default=func.now())


class CommentReplySettings(Base):
    """Configuration for the comment reply system."""
    __tablename__ = "comment_reply_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=False)
    max_replies_per_day = Column(Integer, default=15)
    min_delay_seconds = Column(Integer, default=10)
    max_delay_seconds = Column(Integer, default=30)
    monitor_recent_posts = Column(Integer, default=5)  # How many recent posts to scan
    reply_style = Column(Text, default="warm nature enthusiast — peaceful, inspiring, and wonder-filled")


class CommentReplyLog(Base):
    """Detailed action log for every comment processed."""
    __tablename__ = "comment_reply_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String(255), nullable=True)
    post_id = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False)  # replied / skipped_spam / skipped_duplicate / skipped_short / skipped_abuse / error
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class DMChatHistory(Base):
    """Stores DM conversation history for context-aware AI replies."""
    __tablename__ = "dm_chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String(255), index=True, nullable=False) # The Instagram user ID
    role = Column(String(50), nullable=False) # 'user' or 'ai'
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
