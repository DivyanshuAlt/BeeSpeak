# language/script_detect.py
import re

def detect_script(text: str) -> str:
    """
    Detects dominant script / language form.
    Returns:
    ENGLISH
    HINDI_SCRIPT
    TAMIL_SCRIPT
    ROMANIZED
    MIXED
    """

    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
    has_latin = bool(re.search(r'[a-zA-Z]', text))

    if has_devanagari and not has_latin:
        return "HINDI_SCRIPT"

    if has_tamil and not has_latin:
        return "TAMIL_SCRIPT"

    if has_latin and not (has_devanagari or has_tamil):
        return "LATIN_ONLY"

    if has_latin and (has_devanagari or has_tamil):
        return "MIXED"

    return "UNKNOWN"

HINDI_ROMAN_WORDS = {
    "bhai", "kya", "hai", "ho", "kr", "rha", "jayega", "mat", "kyu"
}

TAMIL_ROMAN_WORDS = {
    "unga", "pannunga", "illa", "iruku", "vendam", "anna"
}

def detect_romanized_language(text: str) -> str:
    words = set(text.lower().split())

    hindi_hits = len(words & HINDI_ROMAN_WORDS)
    tamil_hits = len(words & TAMIL_ROMAN_WORDS)

    if hindi_hits > tamil_hits and hindi_hits >= 1:
        return "ROMANIZED_HINDI"

    if tamil_hits > hindi_hits and tamil_hits >= 1:
        return "ROMANIZED_TAMIL"

    return "ENGLISH"
