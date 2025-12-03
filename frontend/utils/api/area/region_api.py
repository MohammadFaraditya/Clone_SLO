import requests
import streamlit as st
from utils.api import API_URL

# get data region
def get_all_region(token=None, offset=0, limit=50):
    if token is None:
        token = st.session_state.get("token", None)

    if not token:
        raise ValueError("Token tidak ditemukan. Pastikan user sudah login.")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    params = {"offset": offset, "limit": limit}
    try:
        response = requests.get(f"{API_URL}/region/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# insert data region
def insert_region(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/region/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# update data region
def update_region(token, koderegion, keterangan, pin, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "keterangan": keterangan,
        "pin" : pin,
        "updateby": updateby
    }
    try:
        response = requests.put(f"{API_URL}/region/update/{koderegion}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update region {koderegion}: {e}")
        return None
    
# delete data region
def delete_region(token, id_list):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"ids": id_list}
    try:
        return requests.delete(f"{API_URL}/region/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus region: {e}")
        return None