import os
import requests
import json
from dotenv import load_dotenv

# Load existing environment variables
load_dotenv()

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# This is a smaller, more accessible model for the shared free tier
MODEL_ID = "damo-vilab/text-to-video-ms-1.7b"
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}"

def generate_video_hf(prompt):
    if not HF_API_KEY:
        print("Error: HUGGINGFACE_API_KEY not found in .env")
        return

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # ms-1.7b uses a specific payload format
    payload = {
        "inputs": prompt,
        "parameters": {
            "num_frames": 16, # Short for free tier
        }
    }
    
    print(f"Submitting request to: {API_URL}")
    print(f"Prompt: {prompt}")
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            video_filename = "hf_test_video.mp4"
            with open(video_filename, "wb") as f:
                f.write(response.content)
            
            print("\n" + "="*50)
            print(f"SUCCESS! Video saved as {video_filename}")
            print("="*50)
            return video_filename
        
        elif response.status_code == 503:
            print(f"\nStatus 503: Model is loading on HF servers. Try again in 30 seconds.")
            return None
        else:
            print(f"\nError {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        return None

if __name__ == "__main__":
    test_prompt = "A cinematic shot of a tropical waterfall in a lush forest, 4k."
    generate_video_hf(test_prompt)
