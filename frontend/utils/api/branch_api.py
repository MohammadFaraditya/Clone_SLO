import requests
import streamlit as st
from utils.api import API_URL

# GET DATA ENTITY
def get_all_branch(token=None, offset=0, limit=50):
    if token is None:
        token = st.session_state.get("token", None)

    if not token:
        raise ValueError("Token tidak ditemukan. Pastikan user sudah login")
    
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }

    params = {"offset":offset, "limit":limit}
    try:
        response = requests.get(f"{API_URL}/branch/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

#INSERT DATA BRANCH
def insert_branch(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        payload = df.to_dict(orient="reccords")
        response = requests.post(f"{API_URL}/branch/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
