import cloudinary
import cloudinary.uploader
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def upload_video_to_cloudinary(file_path: str) -> str:
    """
    Uploads a video file to Cloudinary and returns the public URL.
    """
    try:
        logger.info(f"Uploading {file_path} to Cloudinary...")
        response = cloudinary.uploader.upload(
            file_path,
            resource_type="video",
            folder="instagram_bot",
            use_filename=True,
            unique_filename=True
        )
        public_url = response.get("secure_url")
        logger.info(f"Successfully uploaded to Cloudinary: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise Exception(f"Failed to upload video to Cloudinary: {e}")


def upload_image_to_cloudinary(file_path: str) -> str:
    """
    Uploads an image file to Cloudinary and returns the public URL.
    """
    try:
        logger.info(f"Uploading image {file_path} to Cloudinary...")
        response = cloudinary.uploader.upload(
            file_path,
            resource_type="image",
            folder="instagram_bot",
            use_filename=True,
            unique_filename=True
        )
        public_url = response.get("secure_url")
        logger.info(f"Successfully uploaded image to Cloudinary: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"Cloudinary image upload failed: {e}")
        raise Exception(f"Failed to upload image to Cloudinary: {e}")
