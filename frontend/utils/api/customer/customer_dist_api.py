import requests
import streamlit as st
from utils.api import API_URL


# GET DATA REGION, ENTITY, BRANCH   
def get_region_entity_mapping_branch(token=None):
    if token is None:
        token = st.session_state.get("token")

    headers = {"Authorization": token}

    try:
        return requests.get(f"{API_URL}/list/area-mapping", headers=headers, timeout=30)
    except Exception as e:
        st.error(f"Gagal mengambil mapping region-entity-branch: {e}")
        return None
    
# GET DATA CUSTOMER DIST
def get_customer_dist(token=None, offset=0, limit=50, branch_dist=None):
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
        response = requests.get(f"{API_URL}/customer-dist/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# INSERT DATA CUSTOMER DIST
def insert_customer_dist(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/customer-dist/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# UPDATE CUSTOMER DIST
def update_customer_dist(token, custno_dist, custname, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {
        "custname" : custname,
        "updateby" : updateby
    }

    try: 
        response = requests.put(f"{API_URL}/customer-dist/update/{custno_dist}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update CUSTNO DIST {custno_dist} : {e}")
        return None
    

# DELETE CUSTOMER DIST
def delete_customer_dist(token, custno_dist):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": custno_dist}
    try:
        return requests.delete(f"{API_URL}/customer-dist/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus CUSTNO DIST: {e}")
        return None