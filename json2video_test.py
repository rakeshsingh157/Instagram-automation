import requests
import time
import json

# Configuration
API_KEY = "2WG8mrJgDmnJCLAqAn62cfI01phfGD0teGbFbaum"
URL = "https://api.json2video.com/v2/movies"

def create_inspirational_reel():
    """
    Creates an inspirational nature video using JSON2Video's template system.
    The template auto-generates:
    - AI images from prompts (via flux-schnell)
    - Voiceover from text
    - Background music
    - Subtitles
    """
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    # Using JSON2Video's inspirational video template
    movie_data = {
        "template": "fOnm0pvJFwKBtwgcCDTk",
        "variables": {
            "voice_model": "azure",
            "voice_name": "en-US-JennyMultilingualNeural",
            "image_model": "flux-schnell",
            "subtitles_model": "default",
            "subtitles_font": "Montserrat",
            "music_url": "https://cdn.json2video.com/assets/audios/inspirational-03.mp3",
            "title": "Nature Heals The Soul",
            "title_font": "Oswald Bold",
            "scene_list": [
                {
                    "voiceover_text": "In the heart of nature, we find the peace that our souls truly crave.",
                    "image_prompt": "A breathtaking misty forest at sunrise, golden light filtering through tall pine trees, photorealistic, cinematic, 4k"
                },
                {
                    "voiceover_text": "Every mountain, every river, every sunset reminds us of the beauty that surrounds us.",
                    "image_prompt": "A majestic snow-capped mountain range reflected in a crystal clear lake at golden hour, photorealistic, cinematic"
                },
                {
                    "voiceover_text": "Take a moment. Breathe in the fresh air. Let nature remind you of what truly matters.",
                    "image_prompt": "A peaceful waterfall cascading into a turquoise pool surrounded by lush tropical greenery, morning mist, photorealistic"
                },
                {
                    "voiceover_text": "The earth has music for those who listen. Stay close to nature, and it will never fail you.",
                    "image_prompt": "A stunning sunset over a vast ocean with dramatic orange and purple clouds, a lone tree silhouette on a cliff, photorealistic, cinematic"
                }
            ]
        }
    }

    print("Submitting inspirational nature video to JSON2Video...")
    print(f"Template: fOnm0pvJFwKBtwgcCDTk")
    print(f"Scenes: {len(movie_data['variables']['scene_list'])}")
    
    response = requests.post(URL, headers=headers, json=movie_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        if result.get("success"):
            project_id = result.get("project")
            print(f"\nTask created! Project ID: {project_id}")
            return project_id
    
    print(f"Error: {response.status_code} {response.text}")
    return None

def poll_status(project_id, interval=10, timeout=600):
    """Polls for render completion (longer timeout for complex videos)."""
    url = f"{URL}?project={project_id}"
    headers = {"x-api-key": API_KEY}
    
    start_time = time.time()
    print("\nRendering video (this may take a few minutes for AI image generation + voiceover)...\n")
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            movie = result.get("movie", {})
            status = movie.get("status")
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] Status: {status}")
            
            if status == "done":
                return movie.get("url")
            elif status == "error":
                print(f"Failed: {movie.get('message')}")
                print(json.dumps(result, indent=2))
                return None
        
        time.sleep(interval)
    
    print("Timed out.")
    return None

if __name__ == "__main__":
    project_id = create_inspirational_reel()
    if project_id:
        video_url = poll_status(project_id)
        if video_url:
            print("\n" + "="*60)
            print("SUCCESS! Inspirational Nature Video Rendered!")
            print(f"Video URL: {video_url}")
            print("="*60)
