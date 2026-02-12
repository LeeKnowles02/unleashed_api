from dataclasses import dataclass
from typing import Any, Dict, Optional
import base64
import hashlib
import hmac
from urllib.parse import urlencode

import requests


@dataclass
class UnleashedClient:
    base_url: str
    api_id: str
    api_key: str
    client_type: str
    timeout_seconds: int = 30
    
    last_status_code: Optional[int] = None
    last_url: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_id and self.api_key and self.client_type)

    def _signature(self, query_string: str) -> str:
        digest = hmac.new(
            self.api_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _headers(self, query_string: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-auth-id": self.api_id,
            "api-auth-signature": self._signature(query_string),
            "client-type": self.client_type,
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("UnleashedClient not configured (missing base_url/api_id/api_key/client_type).")

        params = params or {}

        # stable ordering for signature showing comments
        query_string = urlencode(sorted(params.items()), doseq=True)

        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if query_string:
            url = f"{url}?{query_string}"

        resp = requests.get(url, headers=self._headers(query_string), timeout=self.timeout_seconds)
        
        self.last_status_code = resp.status_code
        self.last_url = resp.url
        
        resp.raise_for_status()
        return resp.json()