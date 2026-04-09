import requests
import time
import os

# Configuration
API_KEY = "apikey-5efeee0ad14b44319c1346f72e5c7a81"
BASE_URL = "https://api.atlascloud.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def generate_video(prompt, model="wan-2.6"):
    """
    Submit a text-to-video generation task.
    Available models from your list include:
    - wan-2.6 (Wan 2.6 Beta)
    - klingai-3.0
    - vidu-q3
    - luma-dream-2.5
    - google-veo-3.1
    """
    url = f"{BASE_URL}/model/generateVideo"
    payload = {
        "model": model,
        "input": {
            "prompt": prompt
        }
    }
    
    print(f"Submitting request to {model}...")
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        response.raise_for_status()
    
    # The API returns a prediction ID
    prediction_id = response.json().get("id")
    print(f"Generation started successfully. Prediction ID: {prediction_id}")
    return prediction_id

def poll_for_result(prediction_id, interval=10, timeout=600):
    """Poll the status endpoint until the video is generated."""
    url = f"{BASE_URL}/model/prediction/{prediction_id}"
    elapsed = 0
    
    print("Waiting for video generation...")
    while elapsed < timeout:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Polling error: {response.status_code}")
            print(response.text)
            time.sleep(interval)
            elapsed += interval
            continue

        result = response.json()
        
        # Access the status within the data object
        data = result.get("data", {})
        status = data.get("status")
        
        print(f"[{elapsed}s] Status: {status}")
        
        if status in ["completed", "succeeded"]:
            output_urls = data.get("outputs", [])
            if output_urls:
                return output_urls
            else:
                print("No output URLs found in completed response.")
                return None
        elif status == "failed":
            error_msg = data.get("error", "Unknown error")
            raise Exception(f"Generation failed: {error_msg}")
            
        time.sleep(interval)
        elapsed += interval
        
    raise TimeoutError("Generation timed out.")

if __name__ == "__main__":
    try:
        # Test prompt
        prompt_text = "A breathtaking cinematic drone shot of a lush tropical island with turquoise water and white sand."
        
        # Submit task
        pred_id = generate_video(prompt_text)
        
        # Poll for result
        video_urls = poll_for_result(pred_id)
        
        if video_urls:
            print("\n" + "="*50)
            print("SUCCESS! Video generation complete.")
            print(f"Video URL: {video_urls[0]}")
            print("="*50)
        else:
            print("Task completed but no video URL was returned.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
