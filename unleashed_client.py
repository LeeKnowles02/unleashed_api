from dataclasses import dataclass
from typing import Any, Dict, Optional
import base64
import hashlib
import hmac
import time
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
        from integration_log_writer import (
            log_error,
            log_info,
            safe_headers_json,
            safe_url,
            summarize_payload,
        )

        if not self.is_configured():
            log_error(
                "UnleashedClient.get aborted: client not fully configured (base_url, api_id, api_key, client_type required).",
                integration_name="unleashed_api",
                module_name="unleashed_client",
                function_name="UnleashedClient.get",
                event_type="api_request_skipped",
                action="GET",
                endpoint=path,
                status="FAIL",
                detail="Set UNLEASHED_* environment variables and USE_UNLEASHED_API as needed, then retry.",
            )
            raise RuntimeError("UnleashedClient not configured (missing base_url/api_id/api_key/client_type).")

        params = params or {}

        # stable ordering for signature showing comments
        query_string = urlencode(sorted(params.items()), doseq=True)

        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if query_string:
            url = f"{url}?{query_string}"

        hdrs = self._headers(query_string)
        log_info(
            f"HTTP GET to Unleashed API path '{path}' starting (query keys: {list(params.keys())}).",
            integration_name="unleashed_api",
            module_name="unleashed_client",
            function_name="UnleashedClient.get",
            event_type="api_request_started",
            action="GET",
            step_name="requests.get",
            endpoint=path,
            status="STARTED",
            request_method="GET",
            request_url=safe_url(url),
            request_params=query_string or None,
            request_headers_safe=safe_headers_json(hdrs),
            detail="Signature and api-auth-id are masked in request_headers_safe; full credentials never logged.",
        )

        t0 = time.perf_counter()
        try:
            resp = requests.get(url, headers=hdrs, timeout=self.timeout_seconds)
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            log_error(
                f"HTTP GET to Unleashed failed before response: path='{path}'.",
                exc=exc,
                integration_name="unleashed_api",
                module_name="unleashed_client",
                function_name="UnleashedClient.get",
                event_type="api_request_exception",
                action="GET",
                endpoint=path,
                request_url=safe_url(url),
                request_method="GET",
                duration_ms=ms,
                detail="Check network, DNS, firewall, and Unleashed service status. Retry after confirming connectivity.",
            )
            raise

        self.last_status_code = resp.status_code
        self.last_url = resp.url
        ms = int((time.perf_counter() - t0) * 1000)

        body_preview = None
        try:
            body_preview = resp.text[:2000] if resp.text else None
        except Exception:
            body_preview = None

        if not resp.ok:
            log_error(
                f"Unleashed API returned non-success HTTP {resp.status_code} for GET '{path}'.",
                integration_name="unleashed_api",
                module_name="unleashed_client",
                function_name="UnleashedClient.get",
                event_type="api_response_error",
                action="GET",
                endpoint=path,
                status="FAIL",
                http_status_code=resp.status_code,
                duration_ms=ms,
                request_url=safe_url(resp.url),
                request_method="GET",
                response_body_safe=body_preview,
                detail="Inspect error_message/response_body_safe and Unleashed docs for this endpoint. Fix auth or query and retry.",
            )
            resp.raise_for_status()

        log_info(
            f"Parsing Unleashed JSON response body for GET '{path}' (HTTP {resp.status_code}, content_length≈{len(resp.content or b'')} bytes).",
            integration_name="unleashed_api",
            module_name="unleashed_client",
            function_name="UnleashedClient.get",
            event_type="api_response_parse_started",
            action="GET",
            endpoint=path,
            status="IN_PROGRESS",
            http_status_code=resp.status_code,
            duration_ms=ms,
            detail="Next: resp.json(); failures logged as api_response_parse_error.",
        )

        try:
            data = resp.json()
        except Exception as exc:
            log_error(
                f"Unleashed API response for '{path}' was not valid JSON (HTTP {resp.status_code}).",
                exc=exc,
                integration_name="unleashed_api",
                module_name="unleashed_client",
                function_name="UnleashedClient.get",
                event_type="api_response_parse_error",
                action="GET",
                endpoint=path,
                http_status_code=resp.status_code,
                duration_ms=ms,
                response_body_safe=body_preview,
            )
            raise

        items = data.get("Items") if isinstance(data, dict) else None
        item_count = len(items) if isinstance(items, list) else None
        pag = data.get("Pagination") if isinstance(data, dict) else None

        log_info(
            f"HTTP GET '{path}' completed: status={resp.status_code}, duration_ms={ms}, Items_count={item_count}, Pagination={pag}.",
            integration_name="unleashed_api",
            module_name="unleashed_client",
            function_name="UnleashedClient.get",
            event_type="api_response_received",
            action="GET",
            endpoint=path,
            status="SUCCESS",
            http_status_code=resp.status_code,
            duration_ms=ms,
            record_count=item_count,
            request_url=safe_url(resp.url),
            request_method="GET",
            response_summary=summarize_payload(data, max_len=2000),
            detail="If Items_count is lower than expected, pagination may apply (see fetch_all_pages logs).",
        )

        return data