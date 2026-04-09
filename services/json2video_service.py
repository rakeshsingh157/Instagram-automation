"""
JSON2Video Reel Generator — Creates professional inspirational nature reels
using JSON2Video's template system with AI-generated images, voiceover, and music.
"""

import requests
import time
import json
import random
import logging
from core.config import settings

logger = logging.getLogger(__name__)

JSON2VIDEO_URL = "https://api.json2video.com/v2/movies"
TEMPLATE_ID = "fOnm0pvJFwKBtwgcCDTk"

# Background music options (from JSON2Video CDN)
MUSIC_URLS = [
    "https://cdn.json2video.com/assets/audios/inspirational-03.mp3",
    "https://cdn.json2video.com/assets/audios/inspirational-05.mp3",
]


def _generate_reel_scenes() -> dict:
    """
    Use Sarvam AI to generate a title + 4 scene descriptions with image prompts.
    Falls back to hardcoded nature scenes if AI fails.
    """
    from services.captioner import _call_ai

    system_prompt = """You are an expert nature content creator for Instagram.
Generate a short inspirational nature video script. Return ONLY valid JSON with this exact format:
{
  "title": "Short inspiring title about nature (3-5 words)",
  "scenes": [
    {"voiceover_text": "One sentence narration about nature", "image_prompt": "Detailed photorealistic image description of a nature scene"},
    {"voiceover_text": "...", "image_prompt": "..."},
    {"voiceover_text": "...", "image_prompt": "..."},
    {"voiceover_text": "...", "image_prompt": "..."}
  ]
}
Rules:
- Exactly 4 scenes.
- voiceover_text: One peaceful, inspiring sentence about nature (English).
- image_prompt: Detailed photorealistic description of a stunning nature/landscape scene. STRICT RULE: NO HUMANS, NO PEOPLE, NO FACES. 100% wilderness. Include lighting, mood, and atmosphere keywords.
- title: Short and catchy (3-5 words).
- Output ONLY the JSON, nothing else."""

    themes = [
        "misty mountain sunrise", "tropical waterfall paradise", "autumn forest magic",
        "ocean horizon sunset", "starry night wilderness", "cherry blossom spring",
        "northern lights wonder", "desert golden hour", "rainforest serenity",
        "snowy peak adventure", "wildflower meadow", "river valley morning mist",
    ]
    theme = random.choice(themes)
    user_prompt = f"Create a nature video script about: {theme}"

    ai_response = _call_ai(system_prompt, user_prompt)

    if ai_response:
        try:
            # Try to extract JSON from the response
            # Sometimes AI wraps it in ```json ... ```
            cleaned = ai_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            data = json.loads(cleaned)
            if "title" in data and "scenes" in data and len(data["scenes"]) >= 3:
                logger.info(f"AI generated reel script: {data['title']}")
                return data
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse AI reel scenes: {e}")

    # Fallback hardcoded nature scenes
    logger.info("Using fallback reel scenes")
    return {
        "title": "Nature Heals The Soul",
        "scenes": [
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
                "image_prompt": "A stunning sunset over a vast ocean with dramatic orange and purple clouds, photorealistic, cinematic"
            }
        ]
    }


def create_reel_video() -> str | None:
    """
    Creates an inspirational nature reel using JSON2Video.
    Returns the public video URL, or None if it fails.
    """
    api_key = settings.JSON2VIDEO_API_KEY
    if not api_key:
        logger.error("JSON2VIDEO_API_KEY not configured in .env")
        return None

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    # Generate scenes (AI or fallback)
    script = _generate_reel_scenes()

    movie_data = {
        "template": TEMPLATE_ID,
        "variables": {
            "voice_model": "azure",
            "voice_name": "en-US-JennyMultilingualNeural",
            "image_model": "flux-schnell",
            "subtitles_model": "default",
            "subtitles_font": "Montserrat",
            "music_url": random.choice(MUSIC_URLS),
            "title": script["title"],
            "title_font": "Oswald Bold",
            "scene_list": script["scenes"]
        }
    }

    # Submit the render task
    logger.info(f"Submitting reel to JSON2Video: '{script['title']}' ({len(script['scenes'])} scenes)")
    response = requests.post(JSON2VIDEO_URL, headers=headers, json=movie_data, timeout=600)

    if response.status_code != 200:
        logger.error(f"JSON2Video submit failed: {response.status_code} {response.text}")
        return None

    result = response.json()
    if not result.get("success"):
        logger.error(f"JSON2Video submit error: {result}")
        return None

    project_id = result.get("project")
    logger.info(f"JSON2Video project created: {project_id}")

    # Poll for completion (up to 10 minutes)
    video_url = _poll_for_video(project_id, api_key, timeout=600)
    return video_url


def _poll_for_video(project_id: str, api_key: str, interval: int = 15, timeout: int = 600) -> str | None:
    """Polls JSON2Video until the render is complete."""
    url = f"{JSON2VIDEO_URL}?project={project_id}"
    headers = {"x-api-key": api_key}

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()
                movie = result.get("movie", {})
                status = movie.get("status")
                elapsed = int(time.time() - start_time)

                if status == "done":
                    video_url = movie.get("url")
                    logger.info(f"Reel rendered in {elapsed}s! URL: {video_url}")
                    return video_url
                elif status == "error":
                    logger.error(f"Reel render failed: {movie.get('message')}")
                    return None
                else:
                    logger.debug(f"[{elapsed}s] Reel render status: {status}")
            else:
                logger.warning(f"Polling warning: API returned {response.status_code}")
        except requests.exceptions.Timeout:
            logger.warning(f"Polling timeout (request took >60s). Retrying in {interval}s...")
        except Exception as e:
            logger.warning(f"Polling error: {e}")

        time.sleep(interval)

    logger.error("Reel render timed out after 10 minutes.")
    return None
