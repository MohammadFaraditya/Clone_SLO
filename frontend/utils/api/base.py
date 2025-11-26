import os

API_URL = os.getenv("API_URL", "http://localhost:5000")

def get_headers(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
