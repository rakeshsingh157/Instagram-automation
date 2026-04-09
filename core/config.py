from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HUGGINGFACE_API_KEY: str
    IMGBB_API_KEY: str
    INSTAGRAM_PAGE_ID: str
    INSTAGRAM_ACCESS_TOKEN: str
    PUBLIC_URL: str
    
    BOT_USERNAME: str
    BOT_PASSWORD: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Database
    DATABASE_URL: str
    DB_SSL_CA: str = ""
    
    # AI Modules
    SARVAM_AI_KEY: str = ""
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # JSON2Video (Reel Generation)
    JSON2VIDEO_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
