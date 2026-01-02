import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from streamlit import cache_data
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode

from utils.api.customer.customer_prc_api import (
    get_region_entity_branch_mapping,
    get_customer_prc,
    update_customer_prc,
    delete_customer_prc
)

PAGE_CHUNK = 100 

# CACHE: ambil seluruh data (chunked) sekali
@cache_data(ttl=600) 
def fetch_all_customer_prc_cached(token, kodebranch, chunk_limit=2000):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_customer_prc(token, offset=offset, limit=limit, kodebranch=kodebranch)
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
    """Cache mapping region/entity/branch (1 jam)."""
    res = get_region_entity_branch_mapping(token)
    if res and res.status_code == 200:
        return res.json().get("data", [])
    return []


# RENDER AG-GRID
def render_grid(df, grid_key):
    """
    Render AgGrid and return updated dataframe + selected rows as DataFrames.
    Keep columns order stable.
    """
    df_local = df.copy()
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

    for col in ordered_columns:
        if col not in df_local.columns:
            df_local[col] = ""

    df_local = df_local[ordered_columns]

    columnDefs = [
        {"field": "kodebranch", "checkboxSelection": True, "headerCheckboxSelection": True, "pinned": "left"},
        {"field": "custno", "pinned": "left"},
        {"field": "custname", "editable": True, "cellStyle": {"backgroundColor": "#E8F0FE"}},
        {"field": "custadd", "editable": True, "cellStyle": {"backgroundColor": "#E8F0FE"}},
        {"field": "city", "editable": True, "cellStyle": {"backgroundColor": "#E8F0FE"}},
        {"field": "type", "editable": True, "cellStyle": {"backgroundColor": "#E8F0FE"}},
        {"field": "gharga", "editable": True, "cellStyle": {"backgroundColor": "#E8F0FE"}},
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
        "animateRows": True,
    }

    grid_response = AgGrid(
        df_local,
        gridOptions=grid_options,
        height=520,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=grid_key,
    )

    updated_df = pd.DataFrame(grid_response["data"])
    selected_rows = pd.DataFrame(grid_response["selected_rows"])

    return updated_df, selected_rows

# HELPERS
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Return excel bytes for download from a DataFrame."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.read()


# MAIN APP
def app():
    # auth check
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token
    updateby = st.session_state.user.get("nama", "SYSTEM")

    # init session keys
    st.session_state.setdefault("grid_version", 1)
    st.session_state.setdefault("customer_prc_full", None) 
    st.session_state.setdefault("last_kodebranch", None)
    st.session_state.setdefault("mapping_customer_prc", None)
    st.session_state.setdefault("show_delete_confirm", False)
    st.session_state.setdefault("delete_ids", [])

    st.title("🏪 Customer Master")

    # Mapping region/entity/branch (cached)
    if st.session_state.get("mapping_customer_prc") is None:
        with st.spinner("Memuat mapping region/entity/branch..."):
            st.session_state["mapping_customer_prc"] = get_mapping_cached(token)

    mapping_df = pd.DataFrame(st.session_state.get("mapping_customer_prc", []))

    # FILTER AREA
    if "filter_expander_open" not in st.session_state:
        st.session_state.filter_expander_open = True

    if st.button("⬆️ Upload Customer PRC"):
        st.session_state.page = "upload_customer_prc"
        st.rerun()
        return

    with st.expander("🔍 Filter Data", expanded=st.session_state.filter_expander_open):
        # prepare dropdowns
        mapping_df["region_display"] = mapping_df["koderegion"].fillna("") + " - " + mapping_df["region_name"].fillna("")
        region_list = sorted(mapping_df["region_display"].dropna().unique().tolist())
        selected_region = st.selectbox("Pilih Region:", ["(Pilih Region)"] + region_list)

        entity_list = []
        if selected_region and selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion].copy()
            entity_df["entity_display"] = entity_df["id_entity"].fillna("") + " - " + entity_df["entity_name"].fillna("")
            entity_list = sorted(entity_df["entity_display"].dropna().unique().tolist())

        selected_entity = st.selectbox("Pilih Entity:", ["(Pilih Entity)"] + entity_list)

        branch_list = []
        if selected_entity and selected_entity != "(Pilih Entity)":
            id_entity = selected_entity.split(" - ")[0]
            branch_df = mapping_df[mapping_df["id_entity"] == id_entity].copy()
            branch_df["branch_display"] = branch_df["kodebranch"].fillna("") + " - " + branch_df["nama_branch"].fillna("")
            branch_list = sorted(branch_df["branch_display"].dropna().unique().tolist())

        selected_branch = st.selectbox("Pilih Branch:", ["(Pilih Branch)"] + branch_list)

        # Apply Filter: fetch full data once and store into session_state
        if st.button("▶ Terapkan Filter"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch dahulu")
            else:
                kodebranch = selected_branch.split(" - ")[0]
                st.session_state["last_kodebranch"] = kodebranch

                with st.spinner("Mengambil semua data customer PRC (1x call, cached)..."):
                    all_rows = fetch_all_customer_prc_cached(token, kodebranch, chunk_limit=2000)

                st.session_state["customer_prc_full"] = all_rows
                st.session_state["grid_version"] += 1
                st.success(f"Berhasil memuat {len(all_rows)} data!")

    # MANUAL RELOAD (ignores cache)
    cols = st.columns([1, 6, 1])
    with cols[0]:
        if st.button("🔄 Force Reload"):
            # clear cache for this function
            fetch_all_customer_prc_cached.clear()
            # repopulate mapping cache as well
            get_mapping_cached.clear()
            kodebranch = st.session_state.get("last_kodebranch")
            if kodebranch:
                with st.spinner("Memuat ulang data (fresh)..."):
                    all_rows = fetch_all_customer_prc_cached(token, kodebranch, chunk_limit=2000)
                st.session_state["customer_prc_full"] = all_rows
                st.session_state["grid_version"] += 1
                st.success(f"Reload selesai, {len(all_rows)} rows.")
    with cols[2]:
        if st.button("🔁 Clear Local Data"):
            st.session_state["customer_prc_full"] = None
            st.session_state["last_kodebranch"] = None
            st.session_state["grid_version"] += 1
            st.info("Data lokal dihapus. Terapkan filter lagi untuk memuat data.")

    # DISPLAY GRID (full data from session)
    if st.session_state.get("customer_prc_full"):
        full_data = st.session_state["customer_prc_full"]
        df = pd.DataFrame(full_data)
        # keep stable index and No column
        df.insert(0, "No", range(1, len(df) + 1))

        # Render grid (key includes grid_version to force reinit when data changed)
        updated_df, selected_rows = render_grid(df, grid_key=f"customer_prc_grid_{st.session_state.grid_version}")

        st.markdown("---")
        st.info(f"Total Data : **{len(df)}** (Branch: {st.session_state.get('last_kodebranch')})")

        # Prepare original mapping for comparison
        original_map = {str(r["custno"]): r for r in full_data}

        # SAVE CHANGES (batch locally, update per-row to API)
        if st.button("💾 Simpan Perubahan"):
            changed_rows = []
            for _, row in updated_df.iterrows():
                sid = str(row.get("custno"))
                if sid not in original_map:
                    continue
                orig = original_map[sid]

                is_changed = (
                    (row.get("custname") or "") != (orig.get("custname") or "") or
                    (row.get("custadd") or "") != (orig.get("custadd") or "") or
                    (row.get("city") or "") != (orig.get("city") or "") or
                    (row.get("type") or "") != (orig.get("type") or "") or
                    str(row.get("gharga") or "") != str(orig.get("gharga") or "")
                )

                if not is_changed:
                    continue

                # NO VALIDATION for gharga — send as-is (string)
                gharga_clean = "" if row.get("gharga") is None else str(row.get("gharga"))

                changed_rows.append({
                    "custno": sid,
                    "custname": row.get("custname") or "",
                    "custadd": row.get("custadd") or "",
                    "city": row.get("city") or "",
                    "typecustomer": row.get("type") or "",
                    "gharga": gharga_clean,
                    "updateby": updateby
                })

            if not changed_rows:
                st.info("Tidak ada perubahan yang disimpan.")
            else:
                success = 0
                fail_list = []
                with st.spinner(f"Menyimpan {len(changed_rows)} perubahan..."):
                    for r in changed_rows:
                        # update_customer_prc(token, custno, custname, custadd, city, typecustomer, gharga, updateby)
                        res = update_customer_prc(
                            token,
                            r["custno"],
                            r["custname"],
                            r["custadd"],
                            r["city"],
                            r["typecustomer"],
                            r["gharga"],
                            r["updateby"]
                        )
                        if res and res.status_code == 200:
                            success += 1
                            # update local session_state data (mutate in place)
                            for local_r in st.session_state["customer_prc_full"]:
                                if str(local_r.get("custno")) == r["custno"]:
                                    local_r["custname"] = r["custname"]
                                    local_r["custadd"] = r["custadd"]
                                    local_r["city"] = r["city"]
                                    local_r["type"] = r["typecustomer"]
                                    local_r["gharga"] = r["gharga"]
                                    local_r["updatedate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    local_r["updateby"] = updateby
                                    break
                        else:
                            fail_list.append(r["custno"])

                if success > 0:
                    st.success(f"{success} perubahan berhasil disimpan.")
                    st.session_state["grid_version"] += 1
                if fail_list:
                    st.error(f"Gagal menyimpan untuk custno: {', '.join(fail_list)}")

        # DELETE SELECTED (2-step confirmation)
        if st.button("🗑️ Hapus Data Terpilih"):
            if selected_rows is None or selected_rows.empty:
                st.warning("⚠ Centang minimal satu baris")
            else:
                st.session_state["delete_ids"] = selected_rows["custno"].astype(str).tolist()
                st.session_state["show_delete_confirm"] = True

        if st.session_state.get("show_delete_confirm", False):
            st.warning(f"Yakin ingin menghapus {len(st.session_state.get('delete_ids', []))} data?")

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Ya, Hapus", key="confirm_delete_yes"):
                    ids = st.session_state.get("delete_ids", [])
                    res = delete_customer_prc(token, ids)
                    if res and res.status_code == 200:
                        # remove from local session_state
                        before = len(st.session_state["customer_prc_full"])
                        st.session_state["customer_prc_full"] = [
                            r for r in st.session_state["customer_prc_full"]
                            if str(r.get("custno")) not in set(ids)
                        ]
                        after = len(st.session_state["customer_prc_full"])
                        st.success(f"{before - after} data berhasil dihapus.")
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

        # OPTIONAL: Export current view to Excel
        if st.button("📥 Export Current View to Excel"):
            export_df = updated_df.copy()
            if "No" in export_df.columns:
                export_df = export_df.drop(columns=["No"])
            excel_bytes = to_excel_bytes(export_df)
            st.download_button(
                label="Download .xlsx",
                data=excel_bytes,
                file_name=f"customer_prc_{st.session_state.get('last_kodebranch','all')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Silakan terapkan filter branch untuk memuat data (full fetch).")


if __name__ == "__main__":
    app()
