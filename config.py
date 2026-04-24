import os


class Config:
    UNLEASHED_API_ID = os.getenv("UNLEASHED_API_ID", "")
    UNLEASHED_API_KEY = os.getenv("UNLEASHED_API_KEY", "")
    UNLEASHED_CLIENT_TYPE = os.getenv("UNLEASHED_CLIENT_TYPE", "")
    UNLEASHED_BASE_URL = os.getenv(
        "UNLEASHED_BASE_URL",
        "https://api.unleashedsoftware.com"
    )

    USE_UNLEASHED_API = os.getenv("USE_UNLEASHED_API", "false").lower() == "true"

    _raw_timeout = os.getenv("REQUEST_TIMEOUT_SECONDS", "30")
    try:
        REQUEST_TIMEOUT_SECONDS = int(_raw_timeout)
    except ValueError:
        REQUEST_TIMEOUT_SECONDS = 30

    FRANKFURTER_BASE_URL = os.getenv(
        "FRANKFURTER_BASE_URL",
        "https://api.frankfurter.dev/v2/rates",
    )
    FRANKFURTER_BASE = os.getenv("FRANKFURTER_BASE", "USD").strip().upper()
    FRANKFURTER_QUOTES = os.getenv("FRANKFURTER_QUOTES", "ZAR,GBP,EUR")
    FRANKFURTER_PROVIDER = os.getenv("FRANKFURTER_PROVIDER", "ECB").strip()
