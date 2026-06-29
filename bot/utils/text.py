import re
from typing import List, Tuple, Optional
from bot.database.models import BlacklistWord


# Pattern to match separators between characters: spaces, dots, dashes, underscores, etc.
SEPARATORS_PATTERN = re.compile(r"[\s\.\-\_\*\+\=\|\\\/\[\]\(\)\{\}\<\>\~\`\'\"]+")


def normalize_for_blacklist(text: str) -> str:
    """
    Normalizes text for blacklist checking:
    - Converts to lowercase
    - Removes all separators between characters (spaces, dots, dashes, etc.)
    - Keeps only letters and numbers (Unicode-aware)

    Examples:
    "П р и в е т"      -> "привет"
    "ПРИВЕТ"           -> "привет"
    "ПрИвЕт"           -> "привет"
    "п.р.и.в.е.т"      -> "привет"
    "п-р-и-в-е-т"      -> "привет"
    "п*р*и*в*е*т"      -> "привет"
    "П   Р   И   В   Е   Т" -> "привет"
    "Hello World"      -> "helloworld"
    "h.e.l.l.o"        -> "hello"
    """
    # Remove all separators between characters
    cleaned = SEPARATORS_PATTERN.sub("", text)
    # Keep only letters and numbers (works with standard re module)
    normalized = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]", "", cleaned)
    return normalized.lower()


def check_blacklist_match(text: str, words: List[BlacklistWord]) -> Tuple[bool, Optional[BlacklistWord]]:
    """
    Checks if text contains any blacklisted words.
    Returns (matched, matched_word).
    """
    normalized = normalize_for_blacklist(text)

    for word in words:
        if word.normalized_word in normalized:
            return True, word

    return False, None


def normalize_word_for_storage(word: str) -> str:
    """Normalizes a word before storing in database."""
    return normalize_for_blacklist(word)