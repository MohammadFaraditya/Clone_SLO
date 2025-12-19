import requests
import streamlit as st
from utils.api import API_URL

# GET DATA PRICEGROUP
def get_data_pricegroup(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/pricegroup/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
#INSERT DATA PRICEGROUP
def insert_pricegroup(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/pricegroup/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    
# UPDATE DATA PRICEGROUP
def update_pricegroup(token, pcode, pricecode, sellprice1, sellprice2, sellprice3, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token,
        "Content-Type": "application/json"}
    payload = {
        "pricecode" : pricecode,
        "sellprice1" : sellprice1,
        "sellprice2" : sellprice2,
        "sellprice3" : sellprice3,
        "updateby" : updateby
    }
    try:
        response = requests.put(f"{API_URL}/pricegroup/update/{pcode}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update entity {pcode}: {e}")
        return None
    
# DELETE PRICEGROUP
def delete_pricegroup(token, items):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token,
        "Content-Type": "application/json"}
    payload = {"ids": items}
    try:
        return requests.delete(f"{API_URL}/pricegroup/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus entity: {e}")
        return None
