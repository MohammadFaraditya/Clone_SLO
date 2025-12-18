import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from streamlit import cache_data
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode
from utils.api.product.mapping_product_api import (
    get_region_entity_mapping_branch,
    get_mapping_product,
    delete_mapping_product
)

PAGE_CHUNK = 100

# CACHE DATA MAPPING
@cache_data(ttl=3600)
def get_mapping_cached(token):
    res = get_region_entity_mapping_branch(token)
    if res and res.status_code == 200:
        return res.json().get("data", [])
    return []


# FETCH ALL DATA (PAGINATION)
@cache_data(ttl=600)
def fetch_all_mapping_product(token, branch_dist=None, chunk_limit=2000):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_mapping_product(token, offset=offset, limit=limit, branch_dist=branch_dist)
        if not res or res.status_code != 200:
            break

        payload = res.json()
        chunk = payload.get("data", [])
        all_data.extend(chunk)

        total = payload.get("total", 0)
        offset += len(chunk)
        if not chunk or offset >= total:
            break

    return all_data


# RENDER GRID
def render_grid(df):
    df = df.copy()
    ordered_columns = [
        "branch_dist",
        "pcode_dist",
        "pcode_dist_name",
        "pcode_prc",
        "pcode_prc_name",
        "createdate",
        "createby",
        "updatedate",
        "updateby"
    ]

    for col in ordered_columns:
        if col not in df.columns:
            df[col] = ""

    df = df[ordered_columns]

    columnDefs = [
        {"field": "branch_dist", "checkboxSelection": True, "headerCheckboxSelection": True},
        {"field": "pcode_dist"},
        {"field": "pcode_dist_name"},
        {"field": "pcode_prc"},
        {"field": "pcode_prc_name"},
        {"field": "createdate"},
        {"field": "createby"},
        {"field": "updatedate"},
        {"field": "updateby"},
    ]

    grid_options = {
        "columnDefs": columnDefs,
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
        },
        "rowSelection": "multiple",
        "suppressMovableColumns": True,
        "animateRows": True
    }

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=550,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=f"mapping_product_grid_{st.session_state.grid_version}"
    )

    updated_df = pd.DataFrame(grid_response["data"])
    selected_rows = pd.DataFrame(grid_response["selected_rows"])
    return updated_df, selected_rows

def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token

    if st.session_state.get("refresh_mapping_product"):
        branch_dist = st.session_state.get("last_branch_dist")
        if branch_dist:
            fetch_all_mapping_product.clear()
            data = fetch_all_mapping_product(token, branch_dist)
            st.session_state["mapping_product_display"] = data

        st.session_state.refresh_mapping_product = False
        st.session_state.grid_version += 1

    # INIT SESSION KEYS
    st.session_state.setdefault("grid_version", 1)
    st.session_state.setdefault("mapping_product", None)
    st.session_state.setdefault("mapping_product_display", None)
    st.session_state.setdefault("last_branch_dist", None)

    st.title("👥 Mapping Product")

    # LOAD MAPPING REGION/ENTITY/BRANCH
    if st.session_state.get("mapping_product") is None:
        with st.spinner("Memuat data region/entity/branch..."):
            st.session_state.mapping_product = get_mapping_cached(token)
    mapping_df = pd.DataFrame(st.session_state.mapping_product)

    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    # BUTTON UPLOAD
    if st.button("⬆️ Upload Mapping Product"):
        st.session_state.page = "upload_mapping_product"
        st.session_state.refresh_mapping_product = True
        st.rerun()
        return

    # FILTER REGION → ENTITY → BRANCH
    with st.expander("🔍 Filter Data", expanded=st.session_state.filter_expander_open):
        mapping_df["region_display"] = mapping_df["koderegion"].fillna('') + " - " + mapping_df["region_name"].fillna('')
        region_list = sorted(mapping_df["region_display"].dropna().unique().tolist())
        selected_region = st.selectbox("Pilih Region:", ["(Pilih Region)"] + region_list)

        entity_list = []
        if selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion].copy()
            entity_df["entity_display"] = entity_df["id_entity"].fillna('') + " - " + entity_df["entity_name"].fillna('')
            entity_list = sorted(entity_df["entity_display"].dropna().unique().tolist())

        selected_entity = st.selectbox("Pilih Entity:", ["(Pilih Entity)"] + entity_list)

        branch_list = []
        if selected_entity != "(Pilih Entity)":
            id_entity = selected_entity.split(" - ")[0]
            branch_df = mapping_df[mapping_df["id_entity"] == id_entity].copy()
            branch_df["branch_dist_display"] = branch_df["branch_dist"].fillna("") + " - " + branch_df["nama_branch_dist"].fillna("")
            branch_list = sorted(branch_df["branch_dist_display"].dropna().unique().tolist())

        selected_branch = st.selectbox("Pilih Branch:", ["(Pilih Branch)"] + branch_list)

        if st.button("▶ Terapkan Filter"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch dahulu")
            else:
                branch_dist = selected_branch.split(" - ")[0]
                st.session_state["last_branch_dist"] = branch_dist
                with st.spinner("Mengambil data Mapping Product..."):
                    data = fetch_all_mapping_product(token, branch_dist)
                st.session_state["mapping_product_display"] = data
                st.success(f"Berhasil memuat {len(data)} data!")

    # DISPLAY GRID
    if st.session_state.get("mapping_product_display"):
        df = pd.DataFrame(st.session_state["mapping_product_display"])
        df.insert(0, "No", range(1, len(df)+1))

        updated_df, selected_rows = render_grid(df)
        st.markdown("---")
        st.info(f"Total Data : **{len(df)}**")

        st.subheader("📥 Download Data")
        st.download_button(
            label="📄 Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="mapping_product.csv",
            mime="text/csv"
        )

        # DELETE SELECTED
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                ids = [{"pcode_prc": r["pcode_prc"], "pcode_dist": r["pcode_dist"]} for _, r in selected_rows.iterrows()]
                res = delete_mapping_product(token, ids)
                if res and res.status_code == 200:
                    st.success(f"{len(ids)} data berhasil dihapus")
                    # FORCE RELOAD otomatis
                    branch_dist = st.session_state.get("last_branch_dist")
                    if branch_dist:
                        fetch_all_mapping_product.clear()
                        data = fetch_all_mapping_product(token, branch_dist)
                        st.session_state["mapping_product_display"] = data
                    st.session_state.grid_version += 1
                    st.rerun()
                else:
                    st.error("Gagal menghapus data")

if __name__ == "__main__":
    app()