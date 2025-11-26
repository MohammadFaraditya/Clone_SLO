import requests
import streamlit as st
from utils.api import API_URL

# get data salesman team
def get_all_team(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/salesman-team/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# insert data salesman team
def insert_salesman_team(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/salesman-team/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# update data salesman team
def update_salesman_team(token, id, description, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "description": description,
        "updateby": updateby
    }
    try:
        response = requests.put(f"{API_URL}/salesman-team/update/{id}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update salesman team {id}: {e}")
        return None
    
# delete data salesman team
def delete_salesman_team(token, id_list):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"ids": id_list}
    try:
        return requests.delete(f"{API_URL}/salesman-team/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus salesman team: {e}")
        return None