import streamlit as st
import pandas as pd
from utils.api.salesman.mapping_salesman_api import (
    get_all_mapping_salesman,
    get_region_entity_branch_mapping,
    update_mapping_salesman,
    delete_mapping_salesman
)
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

# FETCH DATA PAGINATION
def fetch_all_mapping_salesman(token, kodebranch=None):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_all_mapping_salesman(
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


# RENDER GRID
def render_grid(df):
    df = df.copy()
    ordered_columns = [
        "kodebranch",
        "id_salesman",
        "nama",
        "id_salesman_dist",
        "nama_salesman_dist",
        "createdate",
        "createby",
        "updatedate",
        "updateby"
    ]

    # pastikan semua kolom yang di-order ada di df, bila tidak ada buat kolom kosong agar indexing tidak error
    for col in ordered_columns:
        if col not in df.columns:
            df[col] = ""

    df = df[ordered_columns]

    columnDefs = [
        {"field": "kodebranch", "checkboxSelection": True, "headerCheckboxSelection": True},
        {"field": "id_salesman"},
        {"field": "nama"},
        {"field": "id_salesman_dist","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "nama_salesman_dist","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
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
        key=f"mapping_salesman_grid_{st.session_state.grid_version}"
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
    
    if "grid_version" not in st.session_state:
        st.session_state.grid_version = 1

    st.title("👥 Mapping Salesman")
    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.session_state.get("refresh_mapping_salesman"):
        st.session_state.refresh_mapping_salesman = False 

        kodebranch = st.session_state.get("last_kodebranch")
        if kodebranch:
            with st.spinner("Memuat ulang data setelah upload..."):
                data = fetch_all_mapping_salesman(token, kodebranch)

            st.session_state["mapping_salesman_display"] = data
            st.session_state.grid_version += 1
            st.success(f"Data berhasil diperbarui (Branch: {kodebranch})")

    # LOAD MAPPING REGION/ENTITY/BRANCH
    if "mapping_salesman" not in st.session_state:
        with st.spinner("Memuat data region/entity/branch..."):
            res = get_region_entity_branch_mapping(token)
            if res and res.status_code == 200:
                st.session_state.mapping_salesman = res.json().get("data", [])
            else:
                st.error("Gagal memuat mapping region/entity/branch")
                return

    mapping_df = pd.DataFrame(st.session_state.mapping_salesman)

    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    # BUTTON UPLOAD
    if st.button("⬆️ Upload Mapping Salesman"):
        st.session_state.page = "upload_mapping_salesman"
        st.rerun()
        return

    # POPUP FILTER REGION → ENTITY → BRANCH
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
                    data = fetch_all_mapping_salesman(token, kodebranch)

                st.session_state["mapping_salesman_display"] = data
                st.success(f"Berhasil memuat {len(data)} data!")


    # DISPLAY GRID
    if "mapping_salesman_display" in st.session_state and st.session_state["mapping_salesman_display"]:

        df = pd.DataFrame(st.session_state["mapping_salesman_display"])
        df.insert(0, "No", range(1, len(df) + 1))

        updated_df, selected_rows = render_grid(df)

        st.markdown("---")

        st.info(f"Total Data : **{len(df)}**")

        #  BUTTON SIMPAN PERUBAHAN

        if st.button("💾 Simpan Perubahan"):
            success = 0

            original_dict = {str(r["id_salesman"]): r for r in st.session_state["mapping_salesman_display"]}
            updateby = st.session_state.user['nama']

            for _, row in updated_df.iterrows():
                sid = str(row["id_salesman"])

                if sid not in original_dict:
                    continue

                original_row = original_dict[sid]

                # kolom yang boleh diedit
                changed = (
                    row["id_salesman_dist"] != original_row.get("id_salesman_dist") or
                    row["nama_salesman_dist"] != original_row.get("nama_salesman_dist")
                )

                if not changed:
                    continue

                res = update_mapping_salesman(
                    token,
                    sid,
                    row["id_salesman_dist"],
                    row["nama_salesman_dist"],
                    updateby
                )

                if res and res.status_code == 200:
                    success += 1
                else:
                    st.error(f"Gagal update mapping salesman {sid}")

            if success > 0:
                st.success(f"Berhasil update {success} data mapping salesman")

                # REFRESH DATA seperti di salesman_master_page.py
                kodebranch = st.session_state.get("last_kodebranch")

                if kodebranch:
                    data = fetch_all_mapping_salesman(token, kodebranch)
                    st.session_state["mapping_salesman_display"] = data

                st.session_state.grid_version += 1
                st.rerun()
            else:
                st.info("Tidak ada perubahan yang disimpan.")

        #DELETE BRANCH  
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                ids = selected_rows["id_salesman"].astype(str).tolist()
                res = delete_mapping_salesman(token, ids)

                if res and res.status_code == 200:
                    st.success(f"{len(ids)} data berhasil dihapus")

                    # REFRESH DATA seperti di salesman_master_page.py
                    kodebranch = st.session_state.get("last_kodebranch")
                    if kodebranch:
                        data = fetch_all_mapping_salesman(token, kodebranch)
                        st.session_state["mapping_salesman_display"] = data

                    st.session_state.grid_version += 1
                    st.rerun()
                else:
                    st.error("Gagal menghapus data")


if __name__ == "__main__":
    app()
