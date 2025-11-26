import requests
import streamlit as st
from utils.api import API_URL

# get data entity
def get_all_entity(token=None, offset=0, limit=50):
    if token is None:
        token = st.session_state.get("token", None)

    if not token:
        raise ValueError("Token tidak ditemukan. Pastikan user sudah login.")
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    params = {"offset":offset, "limit":limit}
    try:
        response = requests.get(f"{API_URL}/entity/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# insert data entity
def insert_entity(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/entity/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

 #UPDATE ENTITY
def update_entity(token, id_entity, keterangan, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Conten-Type": "apllication/json"}
    payload = {
        "keterangan" : keterangan,
        "updateby" : updateby
    }
    try:
        response = requests.put(f"{API_URL}/entity/update/{id_entity}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update entity {id_entity}: {e}")
        return None
    
#DELETE ENTITY
def delete_entity(token, id_entity):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": id_entity}
    try:
        return requests.delete(f"{API_URL}/entity/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus entity: {e}")
        return None

