import requests
import streamlit as st
from utils.api import API_URL

# GET DATA BRANCH
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
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/branch/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# UPDATE BRANCH
def update_branch(token, kodebranch, nama_branch, alamat, host, ftp_user, ftp_password, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {
        "kodebranch" : kodebranch,
        "nama_branch" : nama_branch,
        "alamat" : alamat,
        "host" : host,
        "ftp_user" : ftp_user,
        "ftp_password" : ftp_password,
        "updateby" : updateby
    }

    try: 
        response = requests.put(f"{API_URL}/branch/update/{kodebranch}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update branch {kodebranch} : {e}")
        return None

# DELETE BRANCH
def delete_branch(token, kodebranch):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": kodebranch}
    try:
        return requests.delete(f"{API_URL}/branch/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus branch: {e}")
        return None
