import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from streamlit import cache_data
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode
from utils.api.product.product_dist_api import (
    get_region_entity_mapping_branch,
    get_product_dist,
    update_product_dist,
    delete_product_dist
)

PAGE_CHUNK = 100

# CACHE: ambil seluruh data branch
@cache_data(ttl=600)
def fetch_all_product_dist_cached(token, branch_dist=None, chunk_limit=2000):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_product_dist(token, offset=offset, limit=limit, branch_dist=branch_dist)
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

# RENDER AG-GRID
def render_grid(df, grid_key):
    df_local = df.copy()
    ordered_columns = [
        "branch_dist",
        "pcode_dist",
        "pcodename",
        "createdate",
        "createby",
        "updatedate",
        "updateby"
    ]

    for col in ordered_columns:
        if col not in df_local.columns:
            df_local[col] = ""

    df_local = df_local[ordered_columns]

    columnDefs = [
        {"field": "branch_dist", "checkboxSelection": True, "headerCheckboxSelection": True, "pinned": "left"},
        {"field": "pcode_dist", "pinned": "left"},
        {"field": "pcodename", "editable": True, "cellStyle": {"backgroundColor": "#E2EAF4"}},
        {"field": "createdate"},
        {"field": "createby"},
        {"field": "updatedate"},
        {"field": "updateby"},
    ]

    grid_options = {
        "columnDefs": columnDefs,
        "defaultColDef": {"sortable": True, "filter": True, "resizable": True},
        "rowSelection": "multiple",
        "suppressMovableColumns": True,
        "animateRows": True
    }

    grid_response = AgGrid(
        df_local,
        gridOptions=grid_options,
        height=550,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=grid_key
    )

    updated_df = pd.DataFrame(grid_response["data"])
    selected_rows = pd.DataFrame(grid_response["selected_rows"])
    return updated_df, selected_rows

# EXPORT EXCEL
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    buffer.write(df.to_csv(index=False).encode('utf-8'))
    buffer.seek(0)
    return buffer.read()

# MAIN APP
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token
    updateby = st.session_state.user.get("nama", "SYSTEM")

    st.session_state.setdefault("grid_version", 1)
    st.session_state.setdefault("product_dist_full", None)
    st.session_state.setdefault("last_branch_dist", None)
    st.session_state.setdefault("mapping_product_dist", None)
    st.session_state.setdefault("show_delete_confirm", False)
    st.session_state.setdefault("delete_ids", [])

    st.title("🍘 Product Dist")

    # Load mapping
    if st.session_state.get("mapping_product_dist") is None:
        with st.spinner("Memuat mapping region/entity/branch..."):
            st.session_state["mapping_product_dist"] = get_mapping_cached(token)

    mapping_df = pd.DataFrame(st.session_state.get("mapping_product_dist", []))

    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    # BUTTON UPLOAD
    if st.button("⬆️ Upload Product Dist"):
        st.session_state.page = "upload_product_dist"
        st.rerun()
        return

    # FILTER
    with st.expander("🔍 Filter Data", expanded=st.session_state.filter_expander_open):
        mapping_df["region_display"] = mapping_df["koderegion"].fillna("") + " - " + mapping_df["region_name"].fillna("")
        region_list = sorted(mapping_df["region_display"].dropna().unique().tolist())
        selected_region = st.selectbox("Pilih Region:", ["(Pilih Region)"] + region_list)

        entity_list = []
        if selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion].copy()
            entity_df["entity_display"] = entity_df["id_entity"].fillna("") + " - " + entity_df["entity_name"].fillna("")
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
                with st.spinner("Mengambil data product dist..."):
                    all_rows = fetch_all_product_dist_cached(token, branch_dist)
                st.session_state["product_dist_full"] = all_rows
                st.session_state["grid_version"] += 1
                st.success(f"Berhasil memuat {len(all_rows)} data!")

    # MANUAL RELOAD / CLEAR
    cols = st.columns([1, 6, 1])
    with cols[0]:
        if st.button("🔄 Force Reload"):
            fetch_all_product_dist_cached.clear()
            get_mapping_cached.clear()
            branch_dist = st.session_state.get("last_branch_dist")
            if branch_dist:
                with st.spinner("Memuat ulang data (fresh)..."):
                    all_rows = fetch_all_product_dist_cached(token, branch_dist)
                st.session_state["product_dist_full"] = all_rows
                st.session_state["grid_version"] += 1
                st.success(f"Reload selesai, {len(all_rows)} rows.")

    with cols[2]:
        if st.button("🔁 Clear Local Data"):
            st.session_state["product_dist_full"] = None
            st.session_state["last_branch_dist"] = None
            st.session_state["grid_version"] += 1
            st.info("Data lokal dihapus. Terapkan filter lagi untuk memuat data.")

    # DISPLAY GRID
    if st.session_state.get("product_dist_full"):
        full_data = st.session_state["product_dist_full"]
        df = pd.DataFrame(full_data)
        df.insert(0, "No", range(1, len(df) + 1))

        updated_df, selected_rows = render_grid(df, grid_key=f"product_dist_grid_{st.session_state.grid_version}")

        st.markdown("---")
        st.info(f"Total Data : **{len(df)}**")

        # SAVE CHANGES
        if st.button("💾 Simpan Perubahan"):
            changed_rows = []
            original_map = {str(r["pcode_dist"]): r for r in full_data}

            for _, row in updated_df.iterrows():
                sid = str(row["pcode_dist"])
                if sid not in original_map:
                    continue
                orig = original_map[sid]

                if (row["pcodename"] != orig.get("pcodename")):
                    changed_rows.append({
                        "pcode_dist": sid,
                        "pcodename": row["pcodename"] or "",
                        "updateby": updateby
                    })

            if not changed_rows:
                st.info("Tidak ada perubahan yang disimpan.")
            else:
                success = 0
                fail_list = []
                with st.spinner(f"Menyimpan {len(changed_rows)} perubahan..."):
                    for r in changed_rows:
                        res = update_product_dist(token, r["pcode_dist"], r["pcodename"], r["updateby"])
                        if res and res.status_code == 200:
                            success += 1
                            # update lokal
                            for local_r in st.session_state["product_dist_full"]:
                                if str(local_r.get("pcode_dist")) == r["pcode_dist"]:
                                    local_r["pcodename"] = r["pcodename"]
                                    local_r["updatedate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    local_r["updateby"] = updateby
                                    break
                        else:
                            fail_list.append(r["pcode_dist"])

                if success > 0:
                    st.success(f"{success} perubahan berhasil disimpan.")
                    st.session_state["grid_version"] += 1
                if fail_list:
                    st.error(f"Gagal menyimpan untuk pcode_dist: {', '.join(fail_list)}")

        # DELETE SELECTED
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                st.session_state["delete_ids"] = selected_rows["pcode_dist"].astype(str).tolist()
                st.session_state["show_delete_confirm"] = True

        if st.session_state.get("show_delete_confirm", False):
            st.warning(f"Yakin ingin menghapus {len(st.session_state['delete_ids'])} data?")

            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("Ya, Hapus", key="confirm_delete_yes"):
                    ids = st.session_state["delete_ids"]
                    res = delete_product_dist(token, ids)
                    if res and res.status_code == 200:
                        st.session_state["product_dist_full"] = [
                            r for r in st.session_state["product_dist_full"]
                            if str(r.get("pcode_dist")) not in set(ids)
                        ]
                        st.success(f"{len(ids)} data berhasil dihapus.")
                        st.session_state["grid_version"] += 1
                    else:
                        st.error("Gagal menghapus data di server.")
                    st.session_state["show_delete_confirm"] = False
                    st.session_state["delete_ids"] = []

            with c2:
                if st.button("Batal", key="confirm_delete_no"):
                    st.session_state["show_delete_confirm"] = False
                    st.session_state["delete_ids"] = []
                    st.info("Penghapusan dibatalkan.")

        # EXPORT EXCEL
        if st.button("📥 Export Current View to CSV"):
            export_df = updated_df.copy()
            if "No" in export_df.columns:
                export_df = export_df.drop(columns=["No"])
            excel_bytes = to_csv_bytes(export_df)
            st.download_button(
                label="Download .csv",
                data=excel_bytes,
                file_name=f"product_dist_{st.session_state.get('last_branch_dist','all')}.csv",
                mime="text/csv"
            )

    else:
        st.info("Silakan terapkan filter branch untuk memuat data full.")

if __name__ == "__main__":
    app()