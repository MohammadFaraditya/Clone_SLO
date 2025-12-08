import streamlit as st
import pandas as pd
from utils.api.customer.customer_prc_api import (
    get_region_entity_branch_mapping,
    get_customer_prc,
    update_customer_prc,
    delete_customer_prc

)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

# FETCH DATA PAGINATION
def fetch_customer_prc(token, kodebranch=None):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_customer_prc(
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
        "custno",
        "custname",
        "custadd",
        "city",
        "type",
        "gharga",
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
        {"field": "custno"},
        {"field": "custname","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "custadd","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "city","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "type","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "gharga","editable": True,"cellStyle": {"backgroundColor": "#E2EAF4"}},
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
        key=f"customer_prc_grid_{st.session_state.grid_version}"
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

    st.title("🏪 Customer Master")
    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.session_state.get("refresh_customer_prc"):
        st.session_state.refresh_customer_prc = False 

        kodebranch = st.session_state.get("last_kodebranch")
        if kodebranch:
            with st.spinner("Memuat ulang data setelah upload..."):
                data = fetch_customer_prc(token, kodebranch)

            st.session_state["customer_prc_display"] = data
            st.session_state.grid_version += 1
            st.success(f"Data berhasil diperbarui (Branch: {kodebranch})")

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
    if st.button("⬆️ Upload Customer PRC"):
        st.session_state.page = "upload_customer_prc"
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
                with st.spinner("Mengambil data customer prc..."):
                    data = fetch_customer_prc(token, kodebranch)

                st.session_state["customer_prc_display"] = data
                st.success(f"Berhasil memuat {len(data)} data!")


    # DISPLAY GRID
    if "customer_prc_display" in st.session_state and st.session_state["customer_prc_display"]:

        df = pd.DataFrame(st.session_state["customer_prc_display"])
        df.insert(0, "No", range(1, len(df) + 1))

        updated_df, selected_rows = render_grid(df)

        st.markdown("---")

        # BUTTON SIMPAN PERUBAHAN

        if st.button("💾 Simpan Perubahan"):
            success = 0

            original_dict = {str(r["custno"]): r for r in st.session_state["customer_prc_display"]}
            updateby = st.session_state.user['nama']

            for _, row in updated_df.iterrows():
                sid = str(row["custno"])

                if sid not in original_dict:
                    continue

                original_row = original_dict[sid]

                # kolom yang boleh diedit
                changed = (
                    row["custname"] != original_row.get("custname") or
                    row["custadd"] != original_row.get("custadd") or
                    row["city"] != original_row.get("city") or
                    row["type"] != original_row.get("type") or
                    row["gharga"] != original_row.get("gharga")
                )

                if not changed:
                    continue

                res = update_customer_prc(
                    token,
                    sid,
                    row["custname"],
                    row["custadd"],
                    row["city"],
                    row["type"],
                    row["gharga"],
                    updateby
                )

                if res and res.status_code == 200:
                    success += 1
                else:
                    st.error(f"Gagal update Customer PRC {sid}")

            if success > 0:
                st.success(f"Berhasil update {success} data customer PRC")

                # REFRESH DATA seperti di salesman_master_page.py
                kodebranch = st.session_state.get("last_kodebranch")

                if kodebranch:
                    data = fetch_customer_prc(token, kodebranch)
                    st.session_state["customer_prc_display"] = data

                st.session_state.grid_version += 1
                st.rerun()
            else:
                st.info("Tidak ada perubahan yang disimpan.")

        # DELETE BRANCH  
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                ids = selected_rows["custno"].astype(str).tolist()
                res = delete_customer_prc(token, ids)

                if res and res.status_code == 200:
                    st.success(f"{len(ids)} data berhasil dihapus")

                    # REFRESH DATA seperti di salesman_master_page.py
                    kodebranch = st.session_state.get("last_kodebranch")
                    if kodebranch:
                        data = fetch_customer_prc(token, kodebranch)
                        st.session_state["customer_prc_display"] = data

                    st.session_state.grid_version += 1
                    st.rerun()
                else:
                    st.error("Gagal menghapus data")


if __name__ == "__main__":
    app()
