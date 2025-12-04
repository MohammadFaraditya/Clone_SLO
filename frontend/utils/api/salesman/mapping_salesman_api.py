import requests
import streamlit as st
from utils.api import API_URL


# GET DATA REGION, ENTITY, BRANCH   
def get_region_entity_branch_mapping(token=None):
    if token is None:
        token = st.session_state.get("token")

    headers = {"Authorization": token}

    try:
        return requests.get(f"{API_URL}/list/mapping", headers=headers, timeout=30)
    except Exception as e:
        st.error(f"Gagal mengambil mapping region-entity-branch: {e}")
        return None
    
# GET DATA MAPPING SALESMAN
def get_all_mapping_salesman(token=None, offset=0, limit=50, kodebranch=None):
    if token is None:
        token = st.session_state.get("token", None)

    if not token:
        raise ValueError("Token tidak ditemukan. Pastikan user sudah login")
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    params = {
        "offset": offset,
        "limit": limit
    }

    # tambahkan hanya jika ada
    if kodebranch:
        params["kodebranch"] = kodebranch

    try:
        response = requests.get(f"{API_URL}/mapping-salesman/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None


# INSERT DATA MAPPING SALESMAN
def insert_mapping_salesman(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/mapping-salesman/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# UPDATE SMAPPING SALESMAN
def update_mapping_salesman(token, id_salesman, id_salesman_dist, nama_salesman_dist, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {
        "id_salesman_dist" : id_salesman_dist,
        "nama_salesman_dist" : nama_salesman_dist,
        "updateby" : updateby
    }

    try: 
        response = requests.put(f"{API_URL}/mapping-salesman/update/{id_salesman}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update Salesman {id_salesman} : {e}")
        return None
    
# DELETE SALESMAN MASTER
def delete_mapping_salesman(token, id_salesman):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": id_salesman}
    try:
        return requests.delete(f"{API_URL}/mapping-salesman/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus salesman master: {e}")
        return None