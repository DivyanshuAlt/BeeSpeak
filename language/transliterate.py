# language/transliterate.py
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

def transliterate_to_native(text: str, lang: str) -> str:
    if lang == "ROMANIZED_HINDI":
        return transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)

    if lang == "ROMANIZED_TAMIL":
        return transliterate(text, sanscript.ITRANS, sanscript.TAMIL)

    return text
