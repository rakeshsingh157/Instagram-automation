"""
AI Caption Generator — Uses Sarvam AI to generate viral Instagram captions
and image prompts instead of hardcoded templates.
"""

import requests
import random
import re
import logging
from core.config import settings

logger = logging.getLogger(__name__)

SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions"

# Fallback hashtags pool in case AI doesn't generate enough
HASHTAG_POOL = [
    "#nature", "#landscape", "#naturephotography", "#scenic", "#earthpix",
    "#naturelovers", "#mountains", "#sunset", "#sunrise", "#wilderness",
    "#forest", "#ocean", "#hiking", "#outdoors", "#exploremore",
    "#travelgram", "#beautifuldestinations", "#earthfocus", "#natgeo",
    "#landscape_lovers", "#waterfall", "#skyline", "#cloudporn", "#flowers",
    "#wildlife", "#mothernature", "#naturegram", "#peaceful",
]

# Fallback captions if AI fails
FALLBACK_CAPTIONS = [
    "Nature never goes out of style 🌿 Where's your favorite escape?",
    "Lost in the beauty of this view 🏔️ Tag someone who needs to see this!",
    "Golden hour hits different when nature is the backdrop 🌅✨",
    "Sometimes the best therapy is a long walk in nature 🌲🍃",
    "The earth has music for those who listen 🎶🌍 What's your favorite sound in nature?",
    "Chasing waterfalls and mountain trails today 💧🏞️ Where would you go?",
    "The sky painted something beautiful today 🎨☁️ Rate this view 1-10! 👇",
]


def _call_ai(system_prompt: str, user_prompt: str) -> str | None:
    """Helper to call free Pollinations AI and extract the reply content with retry logic."""
    import time
    for attempt in range(3):
        try:
            payload = {
                "model": "openai",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "jsonMode": False
            }

            response = requests.post("https://text.pollinations.ai/", json=payload, timeout=30)

            if response.status_code == 200:
                return response.text.strip()
            
            if response.status_code == 429:
                logger.warning(f"Free AI rate limit/queue full (attempt {attempt+1}/3). Waiting...")
                time.sleep(5)
                continue
                
            logger.warning(f"Free AI returned {response.status_code}: {response.text[:200]}")
            return None

        except Exception as e:
            logger.error(f"Free AI call failed: {e}")
            if "timed out" in str(e).lower() and attempt < 2:
                time.sleep(5)
                continue
            return None
    return None


def generate_caption() -> str:
    """
    Generate a viral-style Instagram caption using Sarvam AI.
    Falls back to hardcoded templates if AI fails.
    """
    system_prompt = """You are a viral Instagram nature and landscape content writer.
Rules:
- Write ONE short, engaging, viral-style Instagram caption about nature/scenery (2-3 sentences max).
- Use 2-4 emojis naturally inside the caption.
- Make it peaceful, inspiring, or wonder-filled.
- Include a call-to-action (e.g., "Where's your favorite spot?", "Tag someone!", "Rate this view!").
- Do NOT include hashtags in the caption itself.
- Do NOT use quotes around the caption.
- Be creative and never repeat the same caption."""

    themes = [
        "majestic mountain sunrise", "peaceful forest trail", "ocean waves at sunset",
        "misty morning in the valley", "wildflower meadow", "starry night sky",
        "autumn leaves colors", "tropical waterfall", "snowy winter landscape",
        "golden hour over a lake", "dramatic storm clouds", "cherry blossom season",
        "northern lights aurora", "desert sand dunes", "rainforest canopy",
    ]
    theme = random.choice(themes)

    user_prompt = f"Write a viral Instagram caption about: {theme}"

    ai_caption = _call_ai(system_prompt, user_prompt)

    if ai_caption:
        # Clean up any wrapping quotes and literal escaped newlines
        caption = ai_caption.strip().strip('"').strip("'").replace('\\n', '\n')
        # Remove any hashtags the AI might have added
        caption = re.sub(r"#\w+", "", caption).strip()
    else:
        caption = random.choice(FALLBACK_CAPTIONS)

    # Generate hashtags
    hashtags = _generate_hashtags(theme)

    return f"{caption}\n\n.\n.\n.\n{hashtags}"


def _generate_hashtags(theme: str = "") -> str:
    """Generate 20 relevant hashtags — AI-generated with fallback."""
    system_prompt = """You are an Instagram hashtag expert.
Rules:
- Generate exactly 20 trending Instagram hashtags.
- Each hashtag starts with #, no spaces inside the hashtag.
- Mix popular (high reach) and niche (targeted) hashtags.
- Separate hashtags with spaces.
- Output ONLY the hashtags, nothing else."""

    user_prompt = f"Generate 20 Instagram hashtags for a post about: {theme}"

    ai_hashtags = _call_ai(system_prompt, user_prompt)

    if ai_hashtags:
        # Extract valid hashtags from AI response
        found = re.findall(r"#\w+", ai_hashtags)
        if len(found) >= 10:
            return " ".join(found[:20])

    # Fallback: random selection from pool
    selected = random.sample(HASHTAG_POOL, min(20, len(HASHTAG_POOL)))
    return " ".join(selected)


def generate_image_prompt(base_prompt: str = "") -> str:
    """
    Generate a creative Stable Diffusion image prompt using Sarvam AI.
    Enhances the base prompt with artistic details.
    """
    system_prompt = """You are an expert AI image prompt engineer for Stable Diffusion / FLUX models.
Rules:
- Write ONE detailed image generation prompt for a stunning nature/landscape scene.
- STRICT RULE: DO NOT INCLUDE ANY HUMANS, PEOPLE, OR MODELS. The scene must be 100% wilderness and nature.
- Include artistic style, lighting, mood, atmosphere, and quality keywords.
- Keep it under 100 words.
- Do NOT include negative prompt keywords.
- Do NOT use quotes around the prompt.
- Focus on: scenic beauty, dramatic lighting, professional landscape photography, 4K, high detail.
- Ensure every prompt is distinct and introduces unique natural elements (e.g., specific flowers, rock formations, weather patterns).
- Output ONLY the prompt text, nothing else."""

    if not base_prompt:
        base_prompt = "breathtaking landscape nature scene, dramatic lighting, professional photography"

    import random
    flavors = ["sunrise", "sunset", "stormy weather", "snowy", "autumn", "spring flowers", "foggy morning", "starry night", "golden hour", "rain forest", "desert oasis", "alpine lake"]
    random_flavor = random.choice(flavors)

    user_prompt = f"Enhance this image prompt with vivid creative details about a {random_flavor} setting: {base_prompt}. Make it wildly unique."

    ai_prompt = _call_ai(system_prompt, user_prompt)

    if ai_prompt:
        # Clean up
        prompt = ai_prompt.strip().strip('"').strip("'")
        return prompt

    # Fallback: return the base prompt with quality tags
    return f"{base_prompt}, pure nature, no humans, wilderness, stunning landscape, golden hour, professional nature photography, 4k, hyperrealistic, dramatic sky"
