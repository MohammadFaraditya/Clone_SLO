import requests
import streamlit as st
from utils.api import API_URL


# GET DATA REGION, ENTITY, BRANCH   
def get_region_entity_branch_mapping(token=None):
    if token is None:
        token = st.session_state.get("token")

    headers = {"Authorization": token}

    try:
        return requests.get(f"{API_URL}/list/area", headers=headers, timeout=30)
    except Exception as e:
        st.error(f"Gagal mengambil mapping region-entity-branch: {e}")
        return None

# GET DATA SELLOUT
def get_sellout_data(
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
        f"{API_URL}/sellout/data",
        headers=headers,
        params=params,
        timeout=30
    )


# UPLOAD DATA SELLOUT
def upload_sellout_data(
    branch,
    file,
    username="system",
    token=None
):
    if token is None:
        token = st.session_state.get("token")

    headers = {
        "Authorization": token
    }

    files = {
        "file": (file.name, file, file.type)
    }

    data = {
        "branch": branch,
        "username": username
    }

    try:
        return requests.post(
            f"{API_URL}/sellout/upload",  # ✅ FIXED
            headers=headers,
            files=files,
            data=data,
            timeout=300
        )
    except Exception as e:
        st.error(f"Gagal upload sellout: {e}")
        return None