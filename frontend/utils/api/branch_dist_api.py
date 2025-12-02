import requests
import streamlit as st
from utils.api import API_URL

# GET DATA BRANCH DIST
def get_all_branch_dist(token=None, offset=0, limit=50):
    if token is None:
        token = st.session_state.get("token", None)
    
    if not token:
        raise ValueError("Token tidak ditemukan. Pastikan user sudah login")
    
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }

    params = {"offset" : offset, "limit" : limit}
    try:
        response = requests.get(f"{API_URL}/branch-dist/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# INSERT DATA BRANCH DIST
def insert_branch_dist(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/branch-dist/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# UPDATE DATA BRANCH DIST
def update_branch_dist(token, branch_dist, nama_branch_dist, alamat, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "branch_dist": branch_dist,
        "nama_branch_dist" : nama_branch_dist,
        "alamat" : alamat,
        "updateby" : updateby
    }
    try:
        response = requests.put(f"{API_URL}/branch-dist/update/{branch_dist}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update branch dist {branch_dist}: {e}")
        return None
    
# DELETE DATA BRANCH DIST
def delete_branch_dist(token, id_list):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {"ids": id_list}
    try:
        return requests.delete(f"{API_URL}/branch-dist/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus branch dist: {e}")
        return None