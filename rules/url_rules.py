import re

URL_REGEX = re.compile(r"\b(?:https?://|www\.)[^\s<>()\[\]{}]+", re.IGNORECASE)
BARE_DOMAIN_REGEX = re.compile(
    r"\b[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:/[\w\-./?%&=+#]*)?\b",
    re.IGNORECASE,
)

SUSPICIOUS_URL_HINTS = (
    "bit.ly",
    "tinyurl",
    "verify",
    "secure",
    "update",
    "login",
)


def find_urls(text: str) -> list[str]:
    urls = []
    for token in URL_REGEX.findall(text or ""):
        urls.append(token.rstrip(".,;:!?)\"]}"))

    for token in BARE_DOMAIN_REGEX.findall(text or ""):
        if token.startswith("www.") or "." in token:
            if "@" in token:
                continue
            cleaned = token.rstrip(".,;:!?)\"]}")
            if cleaned not in urls:
                urls.append(cleaned)

    return urls


def evaluate(text: str) -> dict:
    urls = find_urls(text)
    suspicious = []

    for raw_url in urls:
        lower_url = raw_url.lower()
        if any(hint in lower_url for hint in SUSPICIOUS_URL_HINTS):
            suspicious.append(raw_url)

    return {
        "has_urls": bool(urls),
        "all_urls": urls,
        "suspicious_urls": suspicious,
    }