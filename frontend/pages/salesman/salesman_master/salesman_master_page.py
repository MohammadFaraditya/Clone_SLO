import streamlit as st
import pandas as pd
from utils.api.salesman.salesman_master_api import (
    get_all_salesman_master,
    get_region_entity_branch_mapping,
    update_salesman_master,
    delete_salesman_master
)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100


# -----------------------------
# FETCH DATA PAGINATION
# -----------------------------
def fetch_all_salesman_data(token, kodebranch=None):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_all_salesman_master(
            token, offset=offset, limit=limit, kodebranch=kodebranch
        )

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


# -----------------------------
# RENDER GRID
# -----------------------------
def render_grid(df):
    df = df.copy()

    ordered_columns = [
        "No",
        "id_salesman",
        "nama",
        "id_team",
        "salesman_team",
        "kodebranch",
        "nama_branch",
        "createdate",
        "createby",
        "updatedate",
        "updateby"
    ]

    df = df[ordered_columns]

    columnDefs = [
        {"field": "No", "checkboxSelection": True, "headerCheckboxSelection": True},
        {"field": "id_salesman"},
        {"field": "nama", "editable": True,
         "cellStyle": {"backgroundColor": "#E2EAF4"}},   # warna kolom editable
        {"field": "id_team"},
        {"field": "salesman_team"},
        {"field": "kodebranch"},
        {"field": "nama_branch"},
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
        key="salesman_master_grid"
    )

    updated_df = pd.DataFrame(grid_response["data"])
    selected_rows = pd.DataFrame(grid_response["selected_rows"])

    return updated_df, selected_rows


# -----------------------------
# MAIN APP
# -----------------------------
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("👥 Salesman Master")
    token = st.session_state.token

    # LOAD MAPPING REGION/ENTITY/BRANCH
    if "mapping" not in st.session_state:
        with st.spinner("Memuat data region/entity/branch..."):
            res = get_region_entity_branch_mapping(token)
            if res and res.status_code == 200:
                st.session_state.mapping = res.json().get("data", [])
            else:
                st.error("Gagal memuat mapping region/entity/branch")
                return

    mapping_df = pd.DataFrame(st.session_state.mapping)

    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    # BUTTON UPLOAD
    if st.button("⬆️ Upload Salesman Master"):
        st.session_state.page = "upload_salesman_master"
        st.rerun()
        return

    # -----------------------------------------
    # POPUP FILTER REGION → ENTITY → BRANCH
    # -----------------------------------------
    with st.expander("🔍 Filter Data", expanded=st.session_state.filter_expander_open):

        mapping_df["region_display"] = (
            mapping_df["koderegion"].fillna('') + " - " + mapping_df["region_name"].fillna('')
        )
        region_list = sorted(mapping_df["region_display"].dropna().unique().tolist())
        selected_region = st.selectbox("Pilih Region:", ["(Pilih Region)"] + region_list)

        entity_list = []
        if selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]

            # FIX: kasih .copy()
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion].copy()

            entity_df["entity_display"] = (
                entity_df["id_entity"].fillna('') + " - " + entity_df["entity_name"].fillna('')
            )
            entity_list = sorted(entity_df["entity_display"].dropna().unique().tolist())

        selected_entity = st.selectbox("Pilih Entity:", ["(Pilih Entity)"] + entity_list)

        branch_list = []
        if selected_entity != "(Pilih Entity)":
            id_entity = selected_entity.split(" - ")[0]

            # FIX: kasih .copy()
            branch_df = mapping_df[mapping_df["id_entity"] == id_entity].copy()

            branch_df["branch_display"] = (
                branch_df["kodebranch"].fillna('') + " - " + branch_df["nama_branch"].fillna('')
            )
            branch_list = sorted(branch_df["branch_display"].dropna().unique().tolist())

        selected_branch = st.selectbox("Pilih Branch:", ["(Pilih Branch)"] + branch_list)

        if st.button("▶ Terapkan Filter"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch dahulu")
            else:
                kodebranch = selected_branch.split(" - ")[0]
                st.session_state["last_kodebranch"] = kodebranch 
                with st.spinner("Mengambil data salesman..."):
                    data = fetch_all_salesman_data(token, kodebranch)

                st.session_state["salesman_master_display"] = data
                st.success(f"Berhasil memuat {len(data)} data!")


    # -----------------------------------------
    # DISPLAY GRID
    # -----------------------------------------
    if "salesman_master_display" in st.session_state and st.session_state["salesman_master_display"]:

        df = pd.DataFrame(st.session_state["salesman_master_display"])
        df.insert(0, "No", range(1, len(df) + 1))

        updated_df, selected_rows = render_grid(df)

        st.markdown("---")

        #  BUTTON SIMPAN PERUBAHAN

        if st.button("💾 Simpan Perubahan"):
            success = 0

            original_dict = {str(r["id_salesman"]): r for r in st.session_state["salesman_master_display"]}

            updateby = st.session_state.get("username", "system")

            for _, row in updated_df.iterrows():
                sid = str(row["id_salesman"])

                if sid not in original_dict:
                    continue

                original_row = original_dict[sid]

                # hanya kolom nama yang editable
                if row["nama"] != original_row.get("nama"):

                    res = update_salesman_master(
                        token,
                        sid,
                        row["nama"],
                        updateby
                    )

                    if res and res.status_code == 200:
                        success += 1
                    else:
                        st.error(f"Gagal update salesman {sid}")

            if success > 0:
                st.success(f"Berhasil update {success} data salesman")
                kodebranch = st.session_state.get("last_kodebranch")

                if kodebranch:
                    data = fetch_all_salesman_data(token, kodebranch)
                    st.session_state["salesman_master_display"] = data

                st.rerun()
            else:
                st.info("Tidak ada perubahan yang disimpan.")

        # ===============================
        # HAPUS DATA TERPILIH
        # ===============================
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                ids = selected_rows["id_salesman"].astype(str).tolist()
                res = delete_salesman_master(token, ids)

                if res and res.status_code == 200:
                    st.success(f"{len(ids)} data berhasil dihapus")
                    kodebranch = st.session_state.get("last_kodebranch")
                    if kodebranch:
                        data = fetch_all_salesman_data(token, kodebranch)
                        st.session_state["salesman_master_display"] = data

                    st.rerun()
                else:
                    st.error("Gagal menghapus data")


if __name__ == "__main__":
    app()
