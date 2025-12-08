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
    

# GET DATA CUSTOMER PRC
def get_customer_prc(token=None, offset=0, limit=50, kodebranch=None):
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
        response = requests.get(f"{API_URL}/customer-prc/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# INSERT DATA CUSTOMER PRC
def insert_customer_prc(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization" : token,
        "Content-Type" : "application/json"
    }
    try:
        df = df.fillna("") 
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/customer-prc/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# UPDATE CUSTOMER PRC
def update_customer_prc(token, custno, custname, custadd, city, typecustomer, gharga, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization" : token, "Content-Type": "application/json"}
    payload = {
        "custname" : custname,
        "custadd" : custadd,
        "city" : city,
        "typecustomer" : typecustomer,
        "gharga" : gharga,
        "updateby" : updateby
    }

    try: 
        response = requests.put(f"{API_URL}/customer-prc/update/{custno}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update Salesman {custno} : {e}")
        return None
    
# DELETE CUSTOMER PRC
def delete_customer_prc(token, custno):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": custno}
    try:
        return requests.delete(f"{API_URL}/customer-prc/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus salesman master: {e}")
        return None