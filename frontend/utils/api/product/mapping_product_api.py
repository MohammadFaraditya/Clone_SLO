import requests
import streamlit as st
from utils.api import API_URL


# GET DATA REGION, ENTITY, BRANCH MAPPING
def get_region_entity_mapping_branch(token=None):
    if token is None:
        token = st.session_state.get("token")

    headers = {"Authorization": token}

    try:
        return requests.get(f"{API_URL}/list/area-mapping", headers=headers, timeout=30)
    except Exception as e:
        st.error(f"Gagal mengambil mapping region-entity-branch: {e}")
        return None
    
# GET DATA MAPPING PRODUCT
def get_mapping_product(token=None, offset=0, limit=50, branch_dist=None):
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
    if branch_dist:
        params["branch_dist"] = branch_dist

    try:
        response = requests.get(f"{API_URL}/mapping-product/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# INSERT DATA MAPPING PRODUCT
def insert_mapping_product(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/mapping-product/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# DELETE MAPPING PRODUCT
def delete_mapping_product(token, custno):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": custno}
    try:
        return requests.delete(f"{API_URL}/mapping-product/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus salesman master: {e}")
        return None