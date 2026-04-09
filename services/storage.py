import requests
import base64
from core.config import settings

def upload_to_imgbb(image_path: str) -> str:
    """
    Uploads an image to ImgBB and returns the public URL.
    This fulfills the requirement of 'free image hosting'.
    """
    if not settings.IMGBB_API_KEY:
        raise Exception("IMGBB_API_KEY is not set.")
        
    with open(image_path, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode('utf-8')
        
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": settings.IMGBB_API_KEY,
        "image": encoded_string,
    }
    
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        return res.json()["data"]["url"]
    else:
        raise Exception(f"Failed to upload to ImgBB: {res.text}")
