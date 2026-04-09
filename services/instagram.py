import requests
import time
from core.config import settings
import logging

logger = logging.getLogger(__name__)


def post_image_to_instagram(image_url: str, caption: str) -> str:
    """
    Publish an image post to Instagram feed.
    image_url must be a publicly accessible URL.
    """
    if not settings.INSTAGRAM_PAGE_ID or not settings.INSTAGRAM_ACCESS_TOKEN:
        raise Exception("Instagram credentials not configured.")

    # Step 1: Create media container (IMAGE type)
    url_media = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }

    res = requests.post(url_media, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create image container: {res.text}")

    container_id = res.json()["id"]
    logger.info(f"Image container created with ID: {container_id}")

    # Step 2: Publish (images process quickly, but wait briefly)
    time.sleep(3)

    publish_url = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }

    pub_res = requests.post(publish_url, data=publish_payload)
    if pub_res.status_code != 200:
        raise Exception(f"Failed to publish image: {pub_res.text}")

    media_id = pub_res.json()["id"]
    logger.info(f"Image posted to Instagram! Media ID: {media_id}")
    return media_id


def post_reels_to_instagram(video_url: str, caption: str) -> str:
    """
    Publish a Reels video to Instagram.
    video_url must be accessible over the public internet.
    """
    if not settings.INSTAGRAM_PAGE_ID or not settings.INSTAGRAM_ACCESS_TOKEN:
        raise Exception("Instagram credentials not configured.")
        
    # Step 1: Create media container
    url_media = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    res = requests.post(url_media, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create media container: {res.text}")
        
    container_id = res.json()["id"]
    logger.info(f"Container created with ID: {container_id}. Waiting for processing...")
    
    # Step 2: Wait for it to process (Instagram processes videos asynchronously)
    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    max_retries = 10
    for i in range(max_retries):
        time.sleep(10)
        status_res = requests.get(status_url, params=params)
        if status_res.status_code == 200:
            status = status_res.json().get("status_code", "")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception("Instagram video processing failed.")
        else:
            logger.warning(f"Failed to fetch status: {status_res.text}")
            
    # Step 3: Publish
    publish_url = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    pub_res = requests.post(publish_url, data=publish_payload)
    if pub_res.status_code != 200:
        raise Exception(f"Failed to publish media: {pub_res.text}")
        
    media_id = pub_res.json()["id"]
    return media_id


def post_video_to_story(video_url: str) -> str:
    """
    Publish a video to Instagram Stories.
    """
    if not settings.INSTAGRAM_PAGE_ID or not settings.INSTAGRAM_ACCESS_TOKEN:
        raise Exception("Instagram credentials not configured.")
        
    # Step 1: Create media container
    url_media = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media"
    payload = {
        "media_type": "STORIES",
        "video_url": video_url,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    res = requests.post(url_media, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create story container: {res.text}")
        
    container_id = res.json()["id"]
    logger.info(f"Story container created: {container_id}. Waiting for processing...")
    
    # Step 2: Wait for it to process
    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    max_retries = 10
    for i in range(max_retries):
        time.sleep(10)
        status_res = requests.get(status_url, params=params)
        if status_res.status_code == 200:
            status = status_res.json().get("status_code", "")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception("Instagram story processing failed.")
                
    # Step 3: Publish
    publish_url = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    pub_res = requests.post(publish_url, data=publish_payload)
    if pub_res.status_code != 200:
        raise Exception(f"Failed to publish story: {pub_res.text}")
        
    media_id = pub_res.json()["id"]
    logger.info(f"Successfully published story! Media ID: {media_id}")
    return media_id


def post_image_to_story(image_url: str) -> str:
    """
    Publish an image to Instagram Stories.
    """
    if not settings.INSTAGRAM_PAGE_ID or not settings.INSTAGRAM_ACCESS_TOKEN:
        raise Exception("Instagram credentials not configured.")
        
    # Step 1: Create media container (STORIES type for image format)
    url_media = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media"
    payload = {
        "media_type": "STORIES",
        "image_url": image_url,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    res = requests.post(url_media, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create story image container: {res.text}")
        
    container_id = res.json()["id"]
    logger.info(f"Story image container created: {container_id}. Waiting for processing...")
    
    # Step 2: Publish (Stories parse quickly but waiting briefly is safer)
    time.sleep(3)
    
    publish_url = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_PAGE_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    
    pub_res = requests.post(publish_url, data=publish_payload)
    if pub_res.status_code != 200:
        raise Exception(f"Failed to publish story image: {pub_res.text}")
        
    media_id = pub_res.json()["id"]
    logger.info(f"Successfully published image to story! Media ID: {media_id}")
    return media_id

