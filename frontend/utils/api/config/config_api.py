import requests
import streamlit as st
from utils.api import API_URL

# GET DATA CONFIG
def get_data_config(token=None, offset=0, limit=50):
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
        response = requests.get(f"{API_URL}/config/data", headers=headers, params=params, timeout=30)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None
    

#INSERT DATA CONFIG
def insert_config(df, token=None):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    try:
        payload = df.to_dict(orient="records")
        response = requests.post(f"{API_URL}/config/insert", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal menghubungi server: {e}")
        return None

# UPDATE DATA CONFIG
def update_config(token, branch, kodebranch, id_salesman, id_customer, id_product, qty1, qty2, qty3, price, grossamount, discount1, discount2, discount3,
                  discount4, discount5, discount6, discount7, discount8, total_discount, dpp, tax, nett, order_no, order_date, invoice_no, invoice_date,
                  invoice_type, sfa_order_no, sfa_order_date, file_extension, separator_file, first_row, flag_bonus, updateby):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization": token,
        "Content-Type": "application/json"}
    payload = {
        "kodebranch" : kodebranch,
        "id_salesman" : id_salesman,
        "id_customer" : id_customer,
        "id_product" : id_product,
        "qty1" : qty1,
        "qty2" : qty2,
        "qty3" : qty3,
        "price" : price,
        "grossamount": grossamount,
        "discount1" : discount1,
        "discount2" : discount2,
        "discount3" : discount3,
        "discount4" : discount4,
        "discount5" : discount5,
        "discount6" : discount6,
        "discount7" : discount7,
        "discount8" : discount8,
        "total_discount" : total_discount,
        "dpp" : dpp,
        "tax" : tax,
        "nett" : nett,
        "order_no" : order_no,
        "order_date" : order_date,
        "invoice_no" : invoice_no,
        "invoice_date" : invoice_date,
        "invoice_type" : invoice_type,
        "sfa_order_no" : sfa_order_no,
        "sfa_order_date" : sfa_order_date,
        "file_extension" : file_extension,
        "separator_file" : separator_file,
        "first_row" : first_row,
        "flag_bonus": flag_bonus,
        "updateby" : updateby
    }
    try:
        response = requests.put(f"{API_URL}/config/update/{branch}", json=payload, headers=headers)
        return response
    except Exception as e:
        st.error(f"Gagal update entity {branch}: {e}")
        return None
    
#DELETE CONFIG
def delete_config(token, branch):
    if token is None:
        token = st.session_state.get("token", None)
    headers = {"Authorization":token, "Content-Type": "application/json"}
    payload = {"ids": branch}
    try:
        return requests.delete(f"{API_URL}/config/delete", json=payload, headers=headers)
    except Exception as e:
        st.error(f"Gagal hapus entity: {e}")
        return None