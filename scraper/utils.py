"""
Utility helpers: logging setup, retry decorator, rate-limiter, URL cleaning.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from functools import wraps
from typing import Any, Callable, TypeVar
from urllib.parse import urljoin, urlparse, urlunparse

try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal envs
    retry = None
    retry_if_exception_type = None
    stop_after_attempt = None
    wait_exponential = None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root 'scraper' logger."""
    logger = logging.getLogger("scraper")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = setup_logging()

# ---------------------------------------------------------------------------
# Simple rate-limiter (tracks last request time)
# ---------------------------------------------------------------------------

_last_request_time: float = 0.0


def rate_limit(min_delay: float = 1.5) -> None:
    """Block until at least *min_delay* seconds have passed since the last call."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < min_delay:
        time.sleep(min_delay - elapsed)
    _last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(max_attempts: int = 3, base_wait: float = 2.0) -> Callable[[F], F]:
    """Return a tenacity-based retry decorator with exponential backoff."""
    if retry is None:
        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Exception | None = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:
                        last_exc = exc
                        if attempt >= max_attempts:
                            raise
                        time.sleep(base_wait * (2 ** (attempt - 1)))
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError("retry wrapper exited unexpectedly")

            return wrapper  # type: ignore[return-value]

        return decorator

    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, min=base_wait, max=60),
        retry=retry_if_exception_type(Exception),
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalise_url(url: str, base: str) -> str:
    """Return an absolute URL, stripping fragments and trailing whitespace."""
    url = url.strip()
    if not url or url.startswith(("#", "javascript:", "mailto:", "tel:")):
        return ""
    absolute = urljoin(base, url)
    parsed = urlparse(absolute)
    # Strip fragment
    clean = urlunparse(parsed._replace(fragment=""))
    return clean


def same_domain(url: str, base: str) -> bool:
    """Return True when *url* belongs to the same (sub)domain as *base*."""
    base_netloc = urlparse(base).netloc.lstrip("www.")
    url_netloc = urlparse(url).netloc.lstrip("www.")
    return url_netloc == base_netloc or url_netloc.endswith("." + base_netloc)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    """Collapse whitespace and normalise unicode; return empty string for None."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def extract_phone(text: str) -> str | None:
    """Return the first US-style phone number found in *text*, or None."""
    match = re.search(
        r"(?:\(\d{3}\)[\s\-.]+|\d{3}[\s\-.]+)\d{3}[\s\-.]+\d{4}", text
    )
    return match.group(0).strip() if match else None


def extract_zip(text: str) -> str | None:
    """Return the first 5-digit US ZIP code found in *text*, or None."""
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", text)
    return match.group(1) if match else None
