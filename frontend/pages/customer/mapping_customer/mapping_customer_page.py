import streamlit as st
import pandas as pd
from utils.api.customer.mapping_customer_api import (
    get_region_entity_branch_mapping,
    get_data_mapping_customer,
    delete_mapping_customer
)
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode
from streamlit import cache_data

PAGE_CHUNK = 100

# CACHE DATA MAPPING
@cache_data(ttl=3600)
def get_mapping_cached(token):
    res = get_region_entity_branch_mapping(token)
    if res and res.status_code == 200:
        return res.json().get("data", [])
    return []


# FETCH ALL DATA (PAGINATION)
@cache_data(ttl=600)
def fetch_all_mapping_customer(token, kodebranch=None, chunk_limit=2000):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_data_mapping_customer(token, offset=offset, limit=limit, kodebranch=kodebranch)
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
        "branch_prc",
        "custno",
        "custname_prc",
        "branch_dist",
        "custno_dist",
        "custname_dist",
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
        {"field": "branch_prc", "checkboxSelection": True, "headerCheckboxSelection": True},
        {"field": "custno"},
        {"field": "custname_prc"},
        {"field": "branch_dist"},
        {"field": "custno_dist"},
        {"field": "custname_dist"},
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
        key=f"mapping_customer_grid_{st.session_state.grid_version}"
    )

    updated_df = pd.DataFrame(grid_response["data"])
    selected_rows = pd.DataFrame(grid_response["selected_rows"])
    return updated_df, selected_rows

# MAIN APP
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token

    # INIT SESSION KEYS
    st.session_state.setdefault("grid_version", 1)
    st.session_state.setdefault("mapping_customer", None)
    st.session_state.setdefault("mapping_customer_display", None)
    st.session_state.setdefault("last_kodebranch", None)

    st.title("👥 Mapping Customer")

    # LOAD MAPPING REGION/ENTITY/BRANCH
    if st.session_state.get("mapping_customer") is None:
        with st.spinner("Memuat data region/entity/branch..."):
            st.session_state.mapping_customer = get_mapping_cached(token)
    mapping_df = pd.DataFrame(st.session_state.mapping_customer)

    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    # BUTTON UPLOAD
    if st.button("⬆️ Upload Mapping Customer"):
        st.session_state.page = "upload_mapping_customer"
        st.session_state.refresh_mapping_customer = True
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
            branch_df["branch_display"] = branch_df["kodebranch"].fillna('') + " - " + branch_df["nama_branch"].fillna('')
            branch_list = sorted(branch_df["branch_display"].dropna().unique().tolist())

        selected_branch = st.selectbox("Pilih Branch:", ["(Pilih Branch)"] + branch_list)

        if st.button("▶ Terapkan Filter"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch dahulu")
            else:
                kodebranch = selected_branch.split(" - ")[0]
                st.session_state["last_kodebranch"] = kodebranch
                with st.spinner("Mengambil data mapping customer..."):
                    data = fetch_all_mapping_customer(token, kodebranch)
                st.session_state["mapping_customer_display"] = data
                st.success(f"Berhasil memuat {len(data)} data!")

    # DISPLAY GRID
    if st.session_state.get("mapping_customer_display"):
        df = pd.DataFrame(st.session_state["mapping_customer_display"])
        df.insert(0, "No", range(1, len(df)+1))

        updated_df, selected_rows = render_grid(df)
        st.markdown("---")
        st.info(f"Total Data : **{len(df)}**")

        st.subheader("📥 Download Data")
        st.download_button(
            label="📄 Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="mapping_customer.csv",
            mime="text/csv"
        )

        # DELETE SELECTED
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                ids = [{"custno": r["custno"], "custno_dist": r["custno_dist"]} for _, r in selected_rows.iterrows()]
                res = delete_mapping_customer(token, ids)
                if res and res.status_code == 200:
                    st.success(f"{len(ids)} data berhasil dihapus")
                    # FORCE RELOAD otomatis
                    kodebranch = st.session_state.get("last_kodebranch")
                    if kodebranch:
                        fetch_all_mapping_customer.clear()
                        data = fetch_all_mapping_customer(token, kodebranch)
                        st.session_state["mapping_customer_display"] = data
                    st.session_state.grid_version += 1
                    st.rerun()
                else:
                    st.error("Gagal menghapus data")

if __name__ == "__main__":
    app()
