"""
Comment Filter — Smart classification and spam detection for Instagram comments.

Classifies comments into:
  - Priority 0: Skip (spam, abuse, too short, emoji-only)
  - Priority 1: Questions (contain "?")
  - Priority 2: Compliments / positive engagement
  - Priority 3: General valid comments
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- Spam Patterns ---
SPAM_PATTERNS = [
    r"\bfollow\s*(me|back)\b",
    r"\bf4f\b",
    r"\bl4l\b",
    r"\bdm\s*(me|for)\b",
    r"\bcheck\s*(my|out)\b",
    r"\bfree\s*(followers|likes|money)\b",
    r"\bclick\s*(the\s*)?link\b",
    r"\blink\s*in\s*(my\s*)?bio\b",
    r"\bvisit\s*(my|our)\b",
    r"\bpromo(tion|te)?\b",
    r"\bgiveaway\b",
    r"\bwin\s*(free|a)\b",
    r"\bsubscribe\b",
    r"\bgo\s*to\s*(my|www)\b",
    r"\bbuy\s*(now|this|from)\b",
    r"\bdiscount\s*code\b",
    r"\bcoupon\b",
    r"\beach\s*other\b.*follow",
    r"https?://",                    # URLs
    r"www\.",                         # URLs without protocol
    r"bit\.ly|tinyurl|t\.co",        # Shorteners
]

# --- Abuse / Offensive Keywords ---
ABUSE_KEYWORDS = [
    "ugly", "stupid", "idiot", "dumb", "trash", "garbage", "loser",
    "shut up", "stfu", "wtf", "hate you", "die", "kill",
    "fake", "scam", "fraud", "pathetic", "disgusting", "useless",
    "worst", "terrible", "horrible", "suck", "sucks",
]

# --- Positive / Compliment Keywords ---
POSITIVE_KEYWORDS = [
    "love", "beautiful", "amazing", "gorgeous", "stunning", "awesome",
    "great", "fantastic", "incredible", "perfect", "wonderful",
    "queen", "king", "goals", "fire", "lit", "slay",
    "inspire", "motivation", "best", "nice", "pretty", "cute",
    "wow", "omg", "damn", "girl", "look", "outfit",
]

# Emoji-only pattern: string containing ONLY emojis, spaces, and variation selectors
EMOJI_ONLY_PATTERN = re.compile(
    r"^[\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF"
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\u200d\ufe0f\u20e3"
    r"\s]+$"
)


@dataclass
class FilterResult:
    """Result of comment filtering."""
    should_reply: bool
    reason: str
    priority: int  # 0=skip, 1=question(highest), 2=positive, 3=general


def _strip_emojis(text: str) -> str:
    """Remove emojis from text to get word count."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u200d\ufe0f\u20e3"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def filter_comment(comment_text: str, own_username: str = "") -> FilterResult:
    """
    Analyze a comment and determine if we should reply.
    
    Returns a FilterResult with should_reply, reason, and priority.
    """
    if not comment_text or not comment_text.strip():
        return FilterResult(should_reply=False, reason="empty_comment", priority=0)
    
    text = comment_text.strip()
    text_lower = text.lower()
    
    # --- 1. Skip our own comments ---
    # (handled upstream, but just in case)
    
    # --- 2. Emoji-only comments ---
    if EMOJI_ONLY_PATTERN.match(text):
        return FilterResult(should_reply=False, reason="emoji_only", priority=0)
    
    # --- 3. Spam detection ---
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return FilterResult(
                should_reply=False, 
                reason=f"spam_detected: matched '{pattern}'", 
                priority=0
            )
    
    # --- 4. Abuse detection ---
    for keyword in ABUSE_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            return FilterResult(
                should_reply=False, 
                reason=f"abuse_detected: '{keyword}'", 
                priority=0
            )
    
    # --- 5. Too short (less than 3 words after removing emojis) ---
    clean_text = _strip_emojis(text)
    word_count = len(clean_text.split()) if clean_text else 0
    
    if word_count < 2:
        return FilterResult(
            should_reply=False, 
            reason=f"too_short: {word_count} word(s)", 
            priority=0
        )
    
    # --- 6. Classify valid comments by priority ---
    
    # Priority 1: Questions
    if "?" in text:
        return FilterResult(
            should_reply=True, 
            reason="question_detected", 
            priority=1
        )
    
    # Priority 2: Positive / compliment / engagement
    for keyword in POSITIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            return FilterResult(
                should_reply=True, 
                reason=f"positive_engagement: '{keyword}'", 
                priority=2
            )
    
    # Priority 3: General valid comment (long enough, not spam/abuse)
    if word_count >= 3:
        return FilterResult(
            should_reply=True, 
            reason="general_valid_comment", 
            priority=3
        )
    
    # Default: borderline — still reply but lowest priority
    return FilterResult(
        should_reply=True, 
        reason="general_comment", 
        priority=3
    )
