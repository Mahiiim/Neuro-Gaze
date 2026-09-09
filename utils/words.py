"""
utils/words.py
--------------
A lightweight vocabulary of common English words for predictive text.
Using a predefined set ensures zero latency during typing and avoids pulling in heavy NLP libraries.
"""

COMMON_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
    "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "yes", "no", "hello", "help", "please", "thank", "sorry", "water", "food", "pain",
    "tired", "rest", "stop", "go", "bathroom", "hot", "cold", "bed", "chair", "nurse",
    "doctor", "family", "call", "need", "more", "less", "up", "down", "left", "right"
]

def get_suggestions(prefix: str, max_count: int = 4) -> list[str]:
    """Return up to `max_count` words starting with `prefix`, sorted by length/frequency."""
    if not prefix:
        return []
    
    prefix = prefix.lower()
    matches = [w for w in COMMON_WORDS if w.startswith(prefix) and w != prefix]
    
    # Sort by length so shorter common words appear first, but preserve original frequency order somewhat
    matches.sort(key=lambda x: len(x))
    return matches[:max_count]
