import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit import cache_data
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from utils.api.sellout.mapping_error_api import (
    get_region_entity_mapping_branch,
    get_mapping_error_data
)

PAGE_CHUNK = 2000

# CACHE 

@cache_data(ttl=600)
def fetch_all_mapping_error_cached(token, kodebranch, date_from, date_to, chunk_limit=PAGE_CHUNK):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_mapping_error_data(
            kodebranch=kodebranch,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            token=token
        )

        if not res or res.status_code != 200:
            break

        payload = res.json()
        chunk = payload.get("data", [])
        total = payload.get("total", 0)

        all_data.extend(chunk)
        offset += len(chunk)

        if not chunk or offset >= total:
            break

    return all_data

@cache_data(ttl=3600)
def get_mapping_cached(token):
    res = get_region_entity_mapping_branch(token)
    if res and res.status_code == 200:
        return res.json().get("data", [])
    return []

#  GRID 

def render_grid(df, grid_key):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True
    )
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_grid_options(
        suppressMovableColumns=True,
        animateRows=True
    )

    grid_response = AgGrid(
        df,
        gridOptions=gb.build(),
        height=520,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.NO_UPDATE,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=grid_key
    )

    return pd.DataFrame(grid_response["data"])

# MAIN 

def app():
    #  AUTH 
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token
    st.session_state.setdefault("me_full_data", None)
    st.session_state.setdefault("me_last_branch", None)
    st.session_state.setdefault("me_last_from", None)
    st.session_state.setdefault("me_last_to", None)
    st.session_state.setdefault("me_mapping_list", None)
    st.session_state.setdefault("me_grid_version", 1)

    st.title("❌ Mapping Error Data")
    st.info("Halaman ini menampilkan data yang gagal terproses karena kesalahan mapping (Product/Customer/Salesman).")

    #  MAPPING DATA 
    if st.session_state["me_mapping_list"] is None:
        with st.spinner("Memuat mapping region / entity / branch..."):
            st.session_state["me_mapping_list"] = get_mapping_cached(token)

    mapping_df = pd.DataFrame(st.session_state["me_mapping_list"])

    #  FILTER SECTION 
    with st.expander("🔍 Filter Mapping Error", expanded=True):
        
        # Region
        mapping_df["region_display"] = (
            mapping_df["koderegion"].fillna("") + " - " +
            mapping_df["region_name"].fillna("")
        )
        region_list = sorted(mapping_df["region_display"].unique().tolist())
        selected_region = st.selectbox("Pilih Region", ["(Pilih Region)"] + region_list)

        # Entity
        entity_list = []
        if selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion].copy()
            entity_df["entity_display"] = (
                entity_df["id_entity"].fillna("") + " - " +
                entity_df["entity_name"].fillna("")
            )
            entity_list = sorted(entity_df["entity_display"].unique().tolist())

        selected_entity = st.selectbox("Pilih Entity", ["(Pilih Entity)"] + entity_list)

        # Branch
        branch_list = []
        if selected_entity != "(Pilih Entity)":
            id_entity = selected_entity.split(" - ")[0]
            branch_df = mapping_df[mapping_df["id_entity"] == id_entity].copy()
            branch_df["branch_display"] = (
                branch_df["branch_dist"].fillna("") + " - " +
                branch_df["nama_branch_dist"].fillna("")
            )
            branch_list = sorted(branch_df["branch_display"].unique().tolist())

        selected_branch = st.selectbox("Pilih Branch", ["(Pilih Branch)"] + branch_list)

        # Date Range
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("From Date", value=None, format="YYYY-MM-DD")
        with col2:
            date_to = st.date_input("To Date", value=None, format="YYYY-MM-DD")

        # Tombol Terapkan
        if st.button("▶ Tampilkan Data Error"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch terlebih dahulu")
            elif not date_from or not date_to:
                st.warning("⚠ Tanggal From dan To wajib diisi")
            elif date_from > date_to:
                st.warning("⚠ Tanggal From tidak boleh lebih besar dari To")
            else:
                kodebranch = selected_branch.split(" - ")[0]
                st.session_state["me_last_branch"] = kodebranch
                st.session_state["me_last_from"] = str(date_from)
                st.session_state["me_last_to"] = str(date_to)

                with st.spinner("Mengambil data mapping error..."):
                    data = fetch_all_mapping_error_cached(
                        token, kodebranch, str(date_from), str(date_to)
                    )
                
                st.session_state["me_full_data"] = data
                st.session_state["me_grid_version"] += 1
                st.success(f"Ditemukan {len(data)} baris bermasalah.")

    # ACTION BUTTONS 
    cols = st.columns([1, 6, 1])
    with cols[0]:
        if st.button("🔄 Refresh"):
            fetch_all_mapping_error_cached.clear()
            get_mapping_cached.clear()
            st.rerun()

    with cols[2]:
        if st.button("🧹 Clear"):
            st.session_state["me_full_data"] = None
            st.session_state["me_grid_version"] += 1
            st.rerun()

    #  DATA GRID DISPLAY 
    if st.session_state.get("me_full_data"):
        df = pd.DataFrame(st.session_state["me_full_data"])
        
        df.insert(0, "No", range(1, len(df) + 1))

        render_grid(
            df, 
            grid_key=f"me_grid_{st.session_state.me_grid_version}"
        )
    else:
        st.info("Gunakan filter di atas untuk melihat data error.")

if __name__ == "__main__":
    app()