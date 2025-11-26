import requests
from utils.api import API_URL


def login(username, password):
    try:
        response = requests.post(f"{API_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        return response 
    except requests.exceptions.RequestException:
        class FakeResponse:
            status_code = 500
            def json(self):
                return {"error": "Tidak dapat terhubung ke server backend."}
        return FakeResponse()

