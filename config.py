import os

class Config:
    # Unleashed placeholders (fill these in tonight)
    UNLEASHED_API_ID = os.getenv("UNLEASHED_API_ID", "")
    UNLEASHED_API_KEY = os.getenv("UNLEASHED_API_KEY", "")
    UNLEASHED_BASE_URL = os.getenv("UNLEASHED_BASE_URL", "https://api.unleashedsoftware.com")

    USE_UNLEASHED_API = os.getenv("USE_UNLEASHED_API", "false").lower() == "true"
    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
