# language/translate.py
from googletrans import Translator

translator = Translator()

def translate_to_english(text: str) -> str:
    try:
        result = translator.translate(text, dest="en")
        return result.text
    except Exception:
        return text
