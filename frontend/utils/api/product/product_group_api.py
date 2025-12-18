import requests
import streamlit as st
from utils.api import API_URL

# GET DATA PRODUCT GROUP
def get_product_group(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/product-group/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    

# INSERT PRODUCT GROUP
def insert_product_group(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/product-group/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    

# UPDATE PRODUCT GROUP
def update_product_group(token, pcode, product_group_1, product_group_2, product_group_3, category_item, vtkp, npd, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "product_group_1": product_group_1,
        "product_group_2" : product_group_2,
        "product_group_3" : product_group_3,
        "category_item" : category_item,
        "vtkp": vtkp,
        "npd": npd,
        "updateby": updateby
    }
    try:
        response = requests.put(f"{API_URL}/product-group/update/{pcode}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update product group {pcode}: {e}")
        return None


# DELETE PRODUCT GROUP
def delete_product_group(token, pcode):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"ids": pcode}
    try:
        return requests.delete(f"{API_URL}/product-group/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus product group: {e}")
        return None