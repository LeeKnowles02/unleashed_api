from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

# NOTE:
# We are intentionally NOT importing requests yet to avoid dependency/errors
# until you are ready to turn the API on.

@dataclass
class UnleashedClient:
    base_url: str
    api_id: str
    api_key: str
    timeout_seconds: int = 30

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_id and self.api_key)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Placeholder GET. When you’re ready, we will implement:
          - HMAC/signature or required auth headers for Unleashed
          - requests.get(...)
          - error handling + pagination support
        """
        raise NotImplementedError("Unleashed API client not enabled yet.")

    def healthcheck(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "timestamp": int(time.time()),
        }
