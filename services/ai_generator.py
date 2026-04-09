import requests
import io
from PIL import Image
import uuid
import os
import random
from core.config import settings

# Using a public default SD model. Requires a HF API Token.
API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

def generate_image(prompt: str, negative_prompt: str = "") -> str:
    """
    Generates an image via Hugging Face Inference API and saves it locally.
    Returns the file path.
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
