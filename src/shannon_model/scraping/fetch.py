"""Descarga HTTP con rate limiting, user-agent identificable y reintentos."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import requests

USER_AGENT = "ShannonNewsScraper/0.1 (+https://github.com/isaacgrimaldovo/shannon_model)"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    ok: bool
    http_status: int | None
    html: str | None
    error_msg: str | None


class RateLimiter:
    """Asegura al menos `delay` segundos entre inicios de requests consecutivos.

    Thread-safe vía lock interno. En uso concurrente, cada worker debe tener su
    propia instancia (ver `pipeline.py`) — compartir una sola instancia entre
    workers serializaría el ritmo de arranque de requests a nivel global y
    anularía la ganancia de velocidad de la concurrencia.
    """

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._last_start: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            if self._last_start is not None:
                elapsed = time.monotonic() - self._last_start
                remaining = self.delay - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            self._last_start = time.monotonic()


def fetch_html(
    url: str,
    session: requests.Session,
    limiter: RateLimiter,
    timeout: float = 15.0,
    max_retries: int = 2,
) -> FetchResult:
    last_error: str | None = None
    last_status: int | None = None

    for _ in range(max_retries + 1):
        limiter.wait()
        try:
            response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        except requests.RequestException as exc:
            last_error = f"request error: {exc}"
            continue

        last_status = response.status_code
        if response.status_code == 200:
            # El sitio sirve UTF-8 pero no lo declara en Content-Type, así que
            # requests cae a ISO-8859-1 por default y rompe acentos/ñ.
            response.encoding = "utf-8"
            return FetchResult(True, response.status_code, response.text, None)

        last_error = f"http {response.status_code}"
        if response.status_code not in RETRYABLE_STATUS:
            break

    return FetchResult(False, last_status, None, last_error)
