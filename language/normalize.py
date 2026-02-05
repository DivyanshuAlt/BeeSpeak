# language/normalize.py
from language.script_detect import detect_script, detect_romanized_language
from language.transliterate import transliterate_to_native
from language.translate import translate_to_english

def normalize_text(raw_text: str) -> str:
    script = detect_script(raw_text)

    # Case 1: Native scripts
    if script == "HINDI_SCRIPT" or script == "TAMIL_SCRIPT":
        return translate_to_english(raw_text)

    # Case 2: Latin-only (English or Romanized)
    if script == "LATIN_ONLY":
        roman_lang = detect_romanized_language(raw_text)

        if roman_lang.startswith("ROMANIZED"):
            native = transliterate_to_native(raw_text, roman_lang)
            return translate_to_english(native)

        return raw_text  # real English

    # Case 3: Mixed
    if script == "MIXED":
        # Best effort: translate whole text
        return translate_to_english(raw_text)

    return raw_text
