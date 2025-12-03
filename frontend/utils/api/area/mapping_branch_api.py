import requests
import streamlit as st
from utils.api import API_URL

# GET DATA MAPPING BRANCH
def get_all_mapping_branch(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/mapping-branch/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

#INSERT DATA MAPPING BRANCH
def insert_mapping_branch(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/mapping-branch/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# DELETE MAPPING BRANCH
def delete_mapping_branch(token, kodebranch):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": kodebranch}
    try:
        return requests.delete(f"{API_URL}/mapping-branch/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus branch: {e}")
        return None
