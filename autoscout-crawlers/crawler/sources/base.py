from abc import ABC, abstractmethod
from typing import List, Dict, Any


class SourceAdapter(ABC):
    name: str
    country: str

    @abstractmethod
    def search(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute search against this source."""
        pass

    @abstractmethod
    def parse(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw source response into normalized schema."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Quick health check for this source."""
        pass
