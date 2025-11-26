import requests
import streamlit as st
from utils.api import API_URL

#get data area
def get_all_areas(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/area/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

#insert data area
def insert_areas(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/area/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

#update data area
def update_area(token, id_area, description, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "description": description,
        "updateby": updateby
    }
    try:
        response = requests.put(f"{API_URL}/area/update/{id_area}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update area {id_area}: {e}")
        return None

# delete data area
def delete_areas(token, id_list):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"ids": id_list}
    try:
        return requests.delete(f"{API_URL}/area/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus area: {e}")
        return None
