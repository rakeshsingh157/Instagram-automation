"""
Image Validator — Multi-pass OCR-based text detection for AI-generated images.
Uses Tesseract OCR (100% free, open source) with multiple pre-processing
passes to catch text that a single scan might miss.

If text is found, the image should be regenerated before posting.
"""

import pytesseract
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import re
import logging

logger = logging.getLogger(__name__)

# Minimum confidence threshold for detected text (0-100)
# Lower = more sensitive (catches faint/blurry text), Higher = only catches clear text
_MIN_CONFIDENCE = 30

# Minimum length of detected text to consider it "real" text (not noise)
# Single random characters from OCR noise are ignored
_MIN_TEXT_LENGTH = 2


def _scan_for_text(image: Image.Image, label: str = "") -> list[str]:
    """
    Runs Tesseract OCR on a single PIL Image.
    Returns a list of detected words (with confidence) that pass the filters.
    """
    try:
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception as e:
        logger.warning(f"Tesseract scan failed ({label}): {e}")
        return []

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

    return detected_words


def _create_preprocessed_variants(image: Image.Image) -> list[tuple[Image.Image, str]]:
    """
    Creates multiple preprocessed versions of the image to catch text
    that might be missed in a single-pass scan.
    Returns list of (image, label) tuples.
    """
    variants = []

    # 1. Original (as-is)
    variants.append((image, "original"))

    # 2. Grayscale — removes color distractions, helps OCR focus on shapes
    gray = ImageOps.grayscale(image)
    variants.append((gray, "grayscale"))

    # 3. High contrast grayscale — makes faint text stand out
    gray_enhanced = ImageEnhance.Contrast(gray).enhance(2.5)
    variants.append((gray_enhanced, "high-contrast"))

    # 4. Inverted (white-on-dark text becomes dark-on-white, easier for Tesseract)
    inverted = ImageOps.invert(gray)
    variants.append((inverted, "inverted"))

    # 5. Sharpened — helps with blurry/soft text
    sharpened = image.filter(ImageFilter.SHARPEN)
    sharp_gray = ImageOps.grayscale(sharpened)
    variants.append((sharp_gray, "sharpened"))

    # 6. Binarized (Otsu-style threshold) — pure black/white for maximum OCR accuracy
    try:
        binary = gray_enhanced.point(lambda x: 0 if x < 128 else 255, '1')
        variants.append((binary, "binarized"))
    except Exception:
        pass

    return variants


# Common phrases found in AI-generated error/refusal images
_AI_REFUSAL_PATTERNS = [
    "sorry", "cannot", "can't", "cant", "unable", "generate", "error",
    "failed", "apologize", "inappropriate", "request", "assist",
    "policy", "guidelines", "violat", "restrict", "not able",
    "image generation", "content policy", "unable to create",
    "i can", "i cannot", "i can't", "not possible", "forbidden",
]


def is_ai_refusal(detected_text: str) -> bool:
    """
    Check if the detected OCR text looks like an AI refusal/error message
    (e.g., 'Sorry, I cannot generate this image').
    
    Returns True if the text matches common AI error phrases.
    """
    text_lower = detected_text.lower()
    # Strip confidence markers like "(85%)"
    text_clean = re.sub(r'\(\d+%\)', '', text_lower).strip()
    
    matches = sum(1 for pattern in _AI_REFUSAL_PATTERNS if pattern in text_clean)
    # If 2+ refusal keywords found, it's very likely an AI error image
    return matches >= 2


def has_text_in_image(image_path: str) -> tuple[bool, str, bool]:
    """
    Multi-pass text detection: scans the image in multiple preprocessed
    variants to catch text that a single OCR pass might miss.

    Returns:
        (has_text: bool, detected_text: str, is_refusal: bool)
        - has_text: True if meaningful text was found in ANY scan pass
        - detected_text: The actual text that was detected (for logging)
        - is_refusal: True if the text looks like an AI error/refusal message
    """
    try:
        image = Image.open(image_path).convert("RGB")

        all_detected = set()

        # Run OCR on each preprocessed variant
        variants = _create_preprocessed_variants(image)

        for variant_image, label in variants:
            words = _scan_for_text(variant_image, label)
            if words:
                logger.info(f"  [{label}] pass found: {words}")
                all_detected.update(words)

        if all_detected:
            # Deduplicate by word (ignoring confidence)
            unique_words = set()
            display_list = []
            for entry in all_detected:
                word_only = re.sub(r'\(\d+%\)', '', entry).strip().lower()
                if word_only not in unique_words:
                    unique_words.add(word_only)
                    display_list.append(entry)

            detected_text = ", ".join(sorted(display_list)[:15])
            refusal = is_ai_refusal(detected_text)
            
            if refusal:
                logger.warning(f"🚫 AI REFUSAL IMAGE detected in '{image_path}': [{detected_text}]")
            else:
                logger.warning(f"⚠️ TEXT DETECTED in image '{image_path}': [{detected_text}]")
            
            return True, detected_text, refusal

        logger.info(f"✅ No text found in image '{image_path}' — clean image!")
        return False, "", False

    except Exception as e:
        logger.error(f"OCR validation error for '{image_path}': {e}")
        # If OCR fails, allow the image through (don't block posting)
        return False, "", False
