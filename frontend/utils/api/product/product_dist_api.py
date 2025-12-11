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
    

# GET DATA PRODUCT DIST
def get_product_dist(token=None, offset=0, limit=50, branch_dist=None):
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
        response = requests.get(f"{API_URL}/product-dist/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# INSERT DATA PRODUCT DIST
def insert_product_dist(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/product-dist/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# UPDATE PRODUCT DIST
def update_product_dist(token, pcode_dist, pcodename, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {
        "pcodename" : pcodename,
        "updateby" : updateby
    }

    try: 
        response = requests.put(f"{API_URL}/product-dist/update/{pcode_dist}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update PRODUCT DIST {pcode_dist} : {e}")
        return None
    
# DELETE PRODUCT DIST
def delete_product_dist(token, pcode_dist):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": pcode_dist}
    try:
        return requests.delete(f"{API_URL}/product-dist/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus PRODUCT DIST: {e}")
        return None