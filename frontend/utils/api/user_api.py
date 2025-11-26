import requests
from .base import API_URL, get_headers

def get_all_users(token):
    response = requests.get(f"{API_URL}/user/list", headers=get_headers(token))
    return response

def create_user(token, data):
    response = requests.post(f"{API_URL}/user/create", json=data, headers=get_headers(token))
    return response
