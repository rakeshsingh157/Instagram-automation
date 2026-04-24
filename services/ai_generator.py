import requests
import io
from PIL import Image
import uuid
import os
import random
from core.config import settings

# Using a public default SD model. Requires a HF API Token.
API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

# Maximum number of times to regenerate if text is detected in the image
MAX_REGENERATION_ATTEMPTS = 3


def _generate_single_image(prompt: str, negative_prompt: str = "") -> str:
    """
    Generates a single image via Hugging Face Inference API and saves it locally.
    Returns the file path. (Internal — does NOT check for text.)
    """
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "seed": random.randint(0, 1000000)
        }
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to generate image: {response.text}")
        
    image_bytes = response.content
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise Exception(f"Failed to parse returned image data: {e}, Response: {response.content[:100]}...")

    # Ensure output directory exists (using /tmp/ or a static folder)
    output_dir = "generated_content"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(output_dir, filename)
    image.save(filepath)
    
    return filepath


def generate_image(prompt: str, negative_prompt: str = "") -> str:
    """
    Generates an image via Hugging Face Inference API with OCR text detection.
    
    Flow:
    1. Generate an image
    2. Run free OCR (Tesseract) to check for text in the image
    3. If text is detected → delete the bad image and regenerate (up to MAX_REGENERATION_ATTEMPTS)
    4. If clean (no text) → return the image path for posting
    
    Returns the file path of a text-free image.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Enhance the negative prompt to discourage text generation
    enhanced_negative = negative_prompt
    text_blockers = "text, words, letters, writing, watermark, signature, font, typography, caption, logo, label, stamp, handwriting"
    if "text" not in negative_prompt.lower():
        enhanced_negative = f"{negative_prompt}, {text_blockers}" if negative_prompt else text_blockers
    
    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        logger.info(f"🖼️ Image generation attempt {attempt}/{MAX_REGENERATION_ATTEMPTS}...")
        
        filepath = _generate_single_image(prompt, enhanced_negative)
        
        # OCR text detection (free via Tesseract)
        try:
            from services.image_validator import has_text_in_image
            has_text, detected_text = has_text_in_image(filepath)
        except ImportError:
            logger.warning("pytesseract not installed — skipping OCR check. pip install pytesseract")
            return filepath
        except Exception as e:
            logger.warning(f"OCR check failed (allowing image): {e}")
            return filepath
        
        if not has_text:
            logger.info(f"✅ Image is clean (no text detected) on attempt {attempt}. Ready to post!")
            return filepath
        
        # Text was detected — delete the bad image and retry
        logger.warning(f"⚠️ Attempt {attempt}: Text detected [{detected_text}] — regenerating...")
        try:
            os.remove(filepath)
        except OSError:
            pass
    
    # All attempts had text — use the last one anyway (better than nothing)
    logger.warning(f"⚠️ All {MAX_REGENERATION_ATTEMPTS} attempts had text. Using last generated image.")
    return _generate_single_image(prompt, enhanced_negative)
