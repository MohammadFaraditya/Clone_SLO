import streamlit as st
import pandas as pd
from utils.api.product.product_group_api import get_product_group, update_product_group, delete_product_group
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100  

# Fetch semua data product group
def fetch_all_product_group(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_product_group(token, offset=offset, limit=limit)
        if not res:
            break
        if res.status_code != 200:
            try:
                err = res.json().get("error") or res.json().get("message") or "Gagal memuat data product group."
            except Exception:
                err = "Gagal memuat data product group."
            st.error(err)
            break

        payload = res.json()
        data_chunk = payload.get("data", [])
        all_data.extend(data_chunk)

        total = payload.get("total", 0)
        offset += len(data_chunk)
        if not data_chunk or offset >= total:
            break

    return all_data, len(all_data)


# Render grid dengan checkbox
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("No", header_name="No", width=60, pinned="left", editable=False)
    gb.configure_column("brand", header_name="BRAND", editable=False)
    gb.configure_column("pcode", header_name="PCODE", width=150, editable=False)
    gb.configure_column("pcodename", header_name="PCODENAME", width=250, editable=False)
    gb.configure_column("product_group_1", header_name="PRODUCT GROUP 1", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("product_group_2", header_name="PRODUCT GROUP 2", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("product_group_3", header_name="PRODUCT GROUP 3", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("category_item", header_name="CATEGORY ITEM", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("vtkp", header_name="VTKP", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("npd", header_name="NPD", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("createdate", header_name="Created Date", editable=False)
    gb.configure_column("createby", header_name="Create By", editable=False)
    gb.configure_column("updatedate", header_name="Update Date", editable=False)
    gb.configure_column("updateby", header_name="Update By", editable=False)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_grid_options(enableRangeSelection=True, suppressRowClickSelection=False)
    gb.configure_grid_options(sideBar={'toolPanels': ['columns', 'filters', 'export']})
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        width='100%',
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        key="product_group_grid_all"
    )

    updated_df = pd.DataFrame(grid_response['data']).drop(columns=["No"], errors='ignore')
    selected_rows = pd.DataFrame(grid_response['selected_rows']).drop(columns=["No"], errors='ignore')
    return updated_df, selected_rows

# Halaman Region Page
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("🍱 PRODUCT GROUP")

    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.button("⬆️ Upload product group"):
        st.session_state.page = "upload_product_group"
        st.rerun()
        return

    # Refresh data hanya jika belum ada atau flag refresh aktif
    if "product_group_data" not in st.session_state or st.session_state.get("refresh_product_group", True):
        with st.spinner("Memuat semua data product group..."):
            all_data, total_count = fetch_all_product_group(token)
            st.session_state["product_group_data"] = all_data
            st.session_state["product_group_total"] = total_count
            st.session_state["refresh_product_group"] = False

    data = st.session_state.get("product_group_data", [])
    total_rows = st.session_state.get("product_group_total", len(data))

    if not data:
        st.info("Tidak ada data product group yang ditemukan.")
        return

    st.markdown(f"**Total Data product group: {total_rows}**")

    # Buat DataFrame lengkap
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "brand", "prlinname", "pcode", "pcodename", "product_group_1", "product_group_2", "product_group_3",
        "category_item","vtkp","npd", "createdate", "createby", "updatedate", "updateby"
    ]
    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="product_group_data_all.csv",
        mime="text/csv"
    )

# Tampilkan grid
    updated_df, selected_rows = render_grid(df_page)
    full_data = st.session_state["product_group_data"]
    original_map = {str(r["pcode"]): r for r in full_data}

    # Tombol Simpan Perubahan 
    if st.button("💾 Simpan Perubahan"):
            changed_rows = []
            for _, row in updated_df.iterrows():
                sid = str(row.get("pcode"))
                if sid not in original_map:
                    continue
                orig = original_map[sid]

                is_changed = (
                    (row.get("product_group_1") or "") != (orig.get("product_group_1") or "") or
                    (row.get("product_group_2") or "") != (orig.get("product_group_2") or "") or
                    (row.get("product_group_3") or "") != (orig.get("product_group_3") or "") or
                    (row.get("category_item") or "") != (orig.get("category_item") or "") or
                    (row.get("vtkp") or "") != (orig.get("vtkp") or "") or
                    str(row.get("npd") or "") != str(orig.get("npd") or "")
                )

                if not is_changed:
                    continue


                changed_rows.append({
                    "pcode": sid,
                    "product_group_1": row.get("product_group_1") or "",
                    "product_group_2": row.get("product_group_2") or "",
                    "product_group_3": row.get("product_group_3") or "",
                    "category_item": row.get("category_item") or "",
                    "vtkp": row.get("vtkp") or "",
                    "npd": row.get("npd") or "",
                    "updateby": updateby
                })

            if not changed_rows:
                st.info("Tidak ada perubahan yang disimpan.")
            else:
                success = 0
                fail_list = []
                with st.spinner(f"Menyimpan {len(changed_rows)} perubahan..."):
                    for r in changed_rows:
                        res = update_product_group(
                            token,
                            r["pcode"],
                            r["product_group_1"],
                            r["product_group_2"],
                            r["product_group_3"],
                            r["category_item"],
                            r["vtkp"],
                            r["npd"],
                            r["updateby"]
                        )
                        if res and res.status_code == 200:
                            success += 1
                        else:
                            fail_list.append(r["pcode"])

                if success > 0:
                    st.success(f"{success} perubahan berhasil disimpan.")
                    st.session_state["refresh_product_group"] = True
                    st.rerun()
                if fail_list:
                    st.error(f"Gagal menyimpan untuk pcode: {', '.join(fail_list)}")

    #Tombol Hapus Baris Terpilih
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox.")
        else:
            ids_to_delete = selected_rows["pcode"].tolist()
            res = delete_product_group(token, ids_to_delete)
            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
                st.session_state["refresh_product_group"] = True
                st.rerun()
            else:
                try:
                    err = res.json().get("error") or res.json().get("message") or "Gagal menghapus data."
                except Exception:
                    err = "Gagal menghapus data."
                st.error(err)