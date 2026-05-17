from abc import ABC, abstractmethod
import random
import time
from typing import List, Dict, Any


class SourceAdapter(ABC):
    name: str
    country: str
    min_request_interval_seconds: float = 3.0
    retry_backoff_seconds: tuple[float, ...] = (2.0, 8.0, 30.0)

    def _throttle(self) -> None:
        """Simple per-source pacing to reduce blocking risk."""
        jitter = random.uniform(0.0, 0.5)
        time.sleep(self.min_request_interval_seconds + jitter)

    def _run_with_retry(self, fn):
        """Retry helper with exponential backoff + jitter."""
        attempts = len(self.retry_backoff_seconds) + 1
        last_error = None

        for attempt in range(attempts):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break

                base = self.retry_backoff_seconds[attempt]
                delay = base + random.uniform(0.0, base * 0.2)
                time.sleep(delay)

        raise last_error

    @abstractmethod
    def search(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute search against this source."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw source response into normalized schema."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Quick health check for this source."""
        raise NotImplementedError
