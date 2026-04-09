import requests
import time
import jwt
from dotenv import load_dotenv
import os

# --- Authentication Configuration ---
# Your Kling AI credentials
ACCESS_KEY = "AfeCRCFkfHETaYFMLpNb8HKHkQQJnGGk"
SECRET_KEY = "rbhhDfAgfMn8fyn4CJGBTbCQGkG8QBfr"

BASE_URL = "https://api-singapore.klingai.com/v1/videos/text2video"

def generate_kling_token(ak: str, sk: str) -> str:
    """
    Generates a JWT token for Kling AI API authentication.
    The token is valid for 30 minutes.
    """
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800, # 30 mins
        "nbf": int(time.time()) - 5      # 5 secs ago
    }
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    token = jwt.encode(payload, sk, algorithm="HS256", headers=headers)
    return token

def create_kling_task(prompt):
    """
    Submits a Text-to-Video task to Kling AI using JWT auth.
    """
    token = generate_kling_token(ACCESS_KEY, SECRET_KEY)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model_name": "kling-v2-6", # Latest 2026 version from documentation
        "prompt": prompt,
        "negative_prompt": "low quality, blurry, distorted, text, watermark, humans, faces",
        "duration": "5",
        "mode": "pro",
        "aspect_ratio": "9:16" # Best for Instagram Reels
    }
    
    print(f"Submitting Kling AI task with prompt: {prompt}")
    response = requests.post(BASE_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 0:
            task_id = data["data"]["task_id"]
            print(f"Task created successfully! ID: {task_id}")
            return task_id
        else:
            print(f"Error from Kling AI: {data.get('message')}")
            return None
    elif response.status_code == 401:
        print("Auth Error: Check if your Access Key and Secret Key are correct.")
        return None
    else:
        print(f"HTTP Error {response.status_code}: {response.text}")
        return None

def poll_kling_status(task_id, interval=15, timeout=900):
    """
    Polls for the video generation result.
    """
    token = generate_kling_token(ACCESS_KEY, SECRET_KEY)
    url = f"{BASE_URL}/{task_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    start_time = time.time()
    print("Waiting for Kling AI to generate your video...")
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                task = data["data"]
                status = task.get("task_status")
                
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] Status: {status}")
                
                if status == "succeed":
                    # Correct result extraction based on 2026 schema
                    video_url = task["task_result"]["videos"][0]["url"]
                    return video_url
                elif status == "failed":
                    error_msg = task.get("task_status_msg", "Unknown error")
                    print(f"Generation failed: {error_msg}")
                    return None
            else:
                print(f"Polling error: {data.get('message')}")
        else:
            print(f"HTTP Error during polling: {response.status_code}")
            
        time.sleep(interval)
        
    print("Generation timed out.")
    return None

if __name__ == "__main__":
    # Test prompt focusing on your Nature theme
    test_prompt = "A breathtaking cinematic drone shot of a misty tropical waterfall in a lush forest, morning sunlight, ultra realistic, 4k."
    
    task_id = create_kling_task(test_prompt)
    if task_id:
        video_url = poll_kling_status(task_id)
        if video_url:
            print("\n" + "="*50)
            print("SUCCESS! Video generation complete.")
            print(f"Video URL: {video_url}")
            print("="*50)
