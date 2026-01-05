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
    

def get_mapping_error_data(
    kodebranch,
    date_from,
    date_to,
    limit=50,
    offset=0,
    token=None
):
    headers = {
        "Authorization": token
    }

    params = {
        "kodebranch": kodebranch,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
        "offset": offset
    }

    return requests.get(
        f"{API_URL}/mapping-error/data",
        headers=headers,
        params=params,
        timeout=30
    )