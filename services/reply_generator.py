"""
AI Reply Generator — Uses Sarvam AI (OpenAI-compatible) to generate
human-like Instagram comment replies.

Response format from Sarvam AI:
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "The actual reply text here"
            },
            "finish_reason": "stop"
        }
    ],
    ...
}

We extract: response["choices"][0]["message"]["content"]
Then clean/slice the text to remove any AI artifacts (quotes, prefixes, etc.)
"""

import requests
import random
import re
import logging
from core.config import settings

logger = logging.getLogger(__name__)

    # Fallback endpoint

# --- Tone variations for prompt diversity ---
TONE_VARIANTS = [
    "Reply in a warm, nature-loving tone like a fellow outdoor enthusiast.",
    "Reply in a calm, peaceful tone inspired by nature.",
    "Reply in a cheerful and wonder-filled way about the beauty of nature.",
    "Reply with genuine enthusiasm about exploring the outdoors.",
    "Reply in a chill, laid-back, conversational tone about nature.",
    "Reply warmly, like a passionate nature photographer sharing the experience.",
]

# --- Fallback templates if AI fails ---
FALLBACK_REPLIES = {
    "question": [
        "Great question! 🌿 I'll share more about this spot soon!",
        "Love that you asked! 🏔️ Stay tuned for more nature content!",
        "Such a good question! I'll definitely cover this 🌅",
        "Ooh interesting question! 🤔 Nature always has answers ✨",
        "That's a great one! I'll share the details in my next post 🌊",
    ],
    "positive": [
        "Thank you! 🌿 Nature truly is the best artist!",
        "So glad you love it! 🏞️ This view was magical!",
        "That means a lot! 🥰 Nature never disappoints ✨",
        "You're amazing, thank you! 🌅 More views coming soon!",
        "This comment made my day! 🌸 Nature lovers are the best!",
        "So kind of you! 💚 The beauty of nature brings us together!",
        "Thank you! 🌄 Wait till you see what's next!",
        "You just put a smile on my face! 😊🌲 Thank you!",
    ],
    "general": [
        "Nature is the best therapy 🌿✨",
        "Thanks for stopping by! 🏞️ More views coming!",
        "The outdoors never gets old! 🌅",
        "Glad you enjoyed this! 🌲",
        "Thank you! 💚 Stay close to nature!",
        "Every view tells a story 🌄",
        "Nature always finds a way to amaze 🌊✨",
        "Sending peaceful vibes your way! 🌿🤗",
    ],
}


def _clean_ai_reply(raw_text: str) -> str:
    """
    Clean and slice the AI-generated reply to remove artifacts.
    
    Sarvam AI response content may include:
    - Leading/trailing quotes
    - "Reply:" or "Response:" prefixes
    - Multiple sentences (we want 1-2 max)
    - Hashtags (not appropriate for replies)
    - @mentions we didn't ask for
    - Excessive emojis
    """
    if not raw_text:
        return ""
    
    text = raw_text.strip().replace('\\n', '\n')
    
    # Remove wrapping quotes (single or double)
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    
    # Remove common AI prefixes
    prefixes_to_remove = [
        r"^(Reply|Response|Answer|Here'?s?\s*(a|my|the)?\s*(reply|response)?)\s*:\s*",
        r"^(Sure!?\s*)?Here'?s?\s*(a|my)?\s*(suggested|possible)?\s*(reply|response)\s*:\s*",
        r"^\"",  # Leading quote
    ]
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, "", text, flags=re.IGNORECASE).strip()
    
    # Remove trailing quote if orphaned
    if text.endswith('"') and '"' not in text[:-1]:
        text = text[:-1].strip()
    
    # Remove hashtags (not natural in replies)
    text = re.sub(r"#\w+", "", text).strip()
    
    # Remove @mentions we didn't add
    text = re.sub(r"@\w+", "", text).strip()
    
    # Limit to 2 sentences max for natural feel
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 2:
        text = " ".join(sentences[:2])
    
    # Cap length at ~200 chars for Instagram reply naturalness
    if len(text) > 200:
        # Cut at last complete word before 200 chars
        text = text[:200].rsplit(" ", 1)[0]
        if not text.endswith(("!", ".", "?", "✨", "💕", "💖", "🥰", "😊")):
            text += " ✨"
    
    # Ensure it doesn't start with whitespace or weird chars
    text = text.strip(" \n\t\r\"'")
    
    return text


def generate_ai_reply(
    comment_text: str, 
    post_caption: str = "", 
    reply_style: str = "",
    priority: int = 3
) -> str:
    """
    Generate a human-like reply using Sarvam AI.
    
    Falls back to template replies if the API call fails.
    """
    # Pick a random tone variation for diversity
    tone = random.choice(TONE_VARIANTS)
    
    style_instruction = reply_style if reply_style else "friendly, casual influencer"
    
    system_prompt = f"""You are a nature and landscape Instagram page replying to comments on your posts.
Rules:
- {tone}
- Keep your reply to 1-2 SHORT sentences maximum (under 150 characters ideal).
- Be natural and human-like. DO NOT sound robotic or generic.
- Use 1-2 nature-themed emojis naturally (🌿🏔️🌅🌊🌲🌸🌄 etc.).
- Do NOT use hashtags in replies.
- Do NOT start with "Reply:" or "Response:" — just write the reply directly.
- Do NOT include @mentions.
- Vary your responses — never repeat the same reply.
- Style: {style_instruction}"""

    # Build context about what to reply to
    user_message = f"Someone commented on your Instagram post: \"{comment_text}\""
    if post_caption:
        # Truncate caption to save tokens
        short_caption = post_caption[:150] + "..." if len(post_caption) > 150 else post_caption
        user_message += f"\n\nYour post caption was: \"{short_caption}\""
    
    user_message += "\n\nWrite a short, natural reply to this comment:"
    
    try:
        import time
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "jsonMode": False
        }
        
        logger.info(f"Generating Free AI reply for comment: '{comment_text[:50]}...'")
        
        for attempt in range(3):
            try:
                response = requests.post("https://text.pollinations.ai/", json=payload, timeout=30)
                
                if response.status_code == 429:
                    logger.warning(f"Free AI rate limit (attempt {attempt+1}/3). Waiting 5s...")
                    time.sleep(5)
                    continue
                    
                if response.status_code != 200:
                    logger.warning(
                        f"Free AI returned status {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    return _get_fallback_reply(priority)
                
                raw_content = response.text.strip()
                
                if not raw_content:
                    logger.warning("Free AI returned empty content")
                    return _get_fallback_reply(priority)
                
                # Clean and format the reply
                cleaned_reply = _clean_ai_reply(raw_content)
                
                if not cleaned_reply or len(cleaned_reply) < 5:
                    logger.warning(f"Cleaned reply too short: '{cleaned_reply}'")
                    return _get_fallback_reply(priority)
                
                logger.info(f"AI reply generated: '{cleaned_reply}'")
                return cleaned_reply

            except Exception as e:
                logger.error(f"Free AI request failed on attempt {attempt+1}: {e}")
                if "timed out" in str(e).lower() and attempt < 2:
                    time.sleep(5)
                    continue
                return _get_fallback_reply(priority)
                
        return _get_fallback_reply(priority)
        
    except Exception as e:
        logger.error(f"Outer AI request block failed: {e}")
        return _get_fallback_reply(priority)


def _get_fallback_reply(priority: int) -> str:
    """Return a random template reply based on comment priority."""
    if priority == 1:
        return random.choice(FALLBACK_REPLIES["question"])
    elif priority == 2:
        return random.choice(FALLBACK_REPLIES["positive"])
    else:
        return random.choice(FALLBACK_REPLIES["general"])
