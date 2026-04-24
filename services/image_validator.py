"""
Image Validator — OCR-based text detection for AI-generated images.
Uses Tesseract OCR (100% free, open source) to check if an image contains text.
If text is found, the image should be regenerated before posting.
"""

import pytesseract
from PIL import Image
import re
import logging

logger = logging.getLogger(__name__)

# Minimum confidence threshold for detected text (0-100)
# Lower = more sensitive (catches faint/blurry text), Higher = only catches clear text
_MIN_CONFIDENCE = 40

# Minimum length of detected text to consider it "real" text (not noise)
# Single random characters from OCR noise are ignored
_MIN_TEXT_LENGTH = 2


def has_text_in_image(image_path: str) -> tuple[bool, str]:
    """
    Scans an image for text using Tesseract OCR (free).
    
    Returns:
        (has_text: bool, detected_text: str)
        - has_text: True if meaningful text was found in the image
        - detected_text: The actual text that was detected (for logging)
    """
    try:
        image = Image.open(image_path)
        
        # Use pytesseract with detailed output (includes confidence scores)
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        detected_words = []
        
        for i, word in enumerate(ocr_data["text"]):
            # Skip empty results
            if not word or not word.strip():
                continue
            
            # Get confidence score for this word
            confidence = int(ocr_data["conf"][i])
            
            # Skip low-confidence detections (OCR noise from textures/patterns)
            if confidence < _MIN_CONFIDENCE:
                continue
            
            # Clean the word — remove single special characters, numbers-only, etc.
            clean_word = re.sub(r'[^a-zA-Z]', '', word).strip()
            
            # Only count words with at least _MIN_TEXT_LENGTH alphabetic characters
            if len(clean_word) >= _MIN_TEXT_LENGTH:
                detected_words.append(f"{clean_word}({confidence}%)")
        
        if detected_words:
            detected_text = ", ".join(detected_words[:10])  # Log first 10 words max
            logger.warning(f"⚠️ TEXT DETECTED in image '{image_path}': [{detected_text}]")
            return True, detected_text
        
        logger.info(f"✅ No text found in image '{image_path}' — clean image!")
        return False, ""
        
    except Exception as e:
        logger.error(f"OCR validation error for '{image_path}': {e}")
        # If OCR fails, allow the image through (don't block posting)
        return False, ""
