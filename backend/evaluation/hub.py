"""Read rows from the Hugging Face dataset viewer API.

The API limits how fast an anonymous client may ask (HTTP 429) and sometimes answers 5xx for a moment, so pages are
fetched with a short pause between them, and a failed page is retried after waiting.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

ROWS_URL = "https://datasets-server.huggingface.co/rows"
PAUSE_BETWEEN_PAGES = 0.5  # seconds


def fetch_page(dataset: str, config: str, split: str, offset: int, length: int = 100, retries: int = 8) -> dict:
    query = urllib.parse.urlencode(
        {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": length}
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(f"{ROWS_URL}?{query}", timeout=60) as response:
                page = json.load(response)
            time.sleep(PAUSE_BETWEEN_PAGES)
            return page
        except (urllib.error.URLError, TimeoutError) as error:  # HTTPError is a URLError: 429, 502, a dropped connection
            if attempt == retries:
                raise
            retry_after = getattr(error, "headers", None) and error.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else 10 * attempt
            time.sleep(min(wait, 90))
