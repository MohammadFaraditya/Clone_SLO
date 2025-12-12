import streamlit as st
import pandas as pd
from utils.api.product.product_prc_api import get_product_prc, update_product_prc, delete_product_prc
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100  

# Fetch semua data product prc
def fetch_all_product_prc(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_product_prc(token, offset=offset, limit=limit)
        if not res:
            break
        if res.status_code != 200:
            try:
                err = res.json().get("error") or res.json().get("message") or "Gagal memuat data product prc."
            except Exception:
                err = "Gagal memuat data product prc."
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
    gb.configure_column("prlin", header_name="KODE PRLIN", editable=False)
    gb.configure_column("prlinname", header_name="NAMA PRLIN NAME", editable=False)
    gb.configure_column("pcode", header_name="PCODE", width=150, editable=False)
    gb.configure_column("pcodename", header_name="PCODENAME", width=250, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("unit1", header_name="UNIT 1", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("unit2", header_name="UNIT 2", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("unit3", header_name="UNIT 3", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice1", header_name="SELL PRICE 1", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice2", header_name="SELL PRICE 2", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice3", header_name="SELL PRICE 3", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("convunit2", header_name="KONVERSI UNIT 2", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("convunit3", header_name="KONVERSI UNIT 3", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
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
        key="product_prc_grid_all"
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

    st.title("🍘 PRODUCT PRC")

    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.button("⬆️ Upload product prc"):
        st.session_state.page = "upload_product_prc"
        st.rerun()
        return

    # Refresh data hanya jika belum ada atau flag refresh aktif
    if "product_prc_data" not in st.session_state or st.session_state.get("refresh_product_prc", True):
        with st.spinner("Memuat semua data product prc..."):
            all_data, total_count = fetch_all_product_prc(token)
            st.session_state["product_prc_data"] = all_data
            st.session_state["product_prc_total"] = total_count
            st.session_state["refresh_product_prc"] = False

    data = st.session_state.get("product_prc_data", [])
    total_rows = st.session_state.get("product_prc_total", len(data))

    if not data:
        st.info("Tidak ada data product prc yang ditemukan.")
        return

    st.markdown(f"**Total Data product prc: {total_rows}**")

    # Buat DataFrame lengkap
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "prlin", "prlinname", "pcode", "pcodename", "unit1", "unit2", "unit3", "sellprice1", "sellprice2", "sellprice3",
        "convunit2","convunit3","createdate", "createby", "updatedate", "updateby"
    ]
    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="product_prc_data_all.csv",
        mime="text/csv"
    )

# Tampilkan grid
    updated_df, selected_rows = render_grid(df_page)
    full_data = st.session_state["product_prc_data"]
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
                    (row.get("pcodename") or "") != (orig.get("pcodename") or "") or
                    (row.get("unit1") or "") != (orig.get("unit1") or "") or
                    (row.get("unit2") or "") != (orig.get("unit2") or "") or
                    (row.get("unit3") or "") != (orig.get("unit3") or "") or
                    (row.get("sellprice1") or "") != (orig.get("sellprice1") or "") or
                    (row.get("sellprice2") or "") != (orig.get("sellprice2") or "") or
                    (row.get("sellprice3") or "") != (orig.get("sellprice3") or "") or
                    (row.get("convunit2") or "") != (orig.get("convunit2") or "") or
                    str(row.get("convunit3") or "") != str(orig.get("convunit3") or "")
                )

                if not is_changed:
                    continue


                changed_rows.append({
                    "pcode": sid,
                    "pcodename": row.get("pcodename") or "",
                    "unit1": row.get("unit1") or "",
                    "unit2": row.get("unit2") or "",
                    "unit3": row.get("unit3") or "",
                    "sellprice1": row.get("sellprice1") or "",
                    "sellprice2": row.get("sellprice2") or "",
                    "sellprice3": row.get("sellprice3") or "",
                    "convunit2": row.get("convunit2") or "",
                    "convunit3": row.get("convunit3") or "",
                    "updateby": updateby
                })

            if not changed_rows:
                st.info("Tidak ada perubahan yang disimpan.")
            else:
                success = 0
                fail_list = []
                with st.spinner(f"Menyimpan {len(changed_rows)} perubahan..."):
                    for r in changed_rows:
                        res = update_product_prc(
                            token,
                            r["pcode"],
                            r["pcodename"],
                            r["unit1"],
                            r["unit2"],
                            r["unit3"],
                            r["convunit2"],
                            r["convunit3"],
                            r["sellprice1"],
                            r["sellprice2"],
                            r["sellprice3"],
                            r["updateby"]
                        )
                        if res and res.status_code == 200:
                            success += 1
                        else:
                            fail_list.append(r["pcode"])

                if success > 0:
                    st.success(f"{success} perubahan berhasil disimpan.")
                    st.session_state["product_prc_data"]
                if fail_list:
                    st.error(f"Gagal menyimpan untuk pcode: {', '.join(fail_list)}")


    #Tombol Hapus Baris Terpilih
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox.")
        else:
            ids_to_delete = selected_rows["pcode"].tolist()
            res = delete_product_prc(token, ids_to_delete)
            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
                st.session_state["refresh_product_prc"] = True
                st.rerun()
            else:
                try:
                    err = res.json().get("error") or res.json().get("message") or "Gagal menghapus data."
                except Exception:
                    err = "Gagal menghapus data."
                st.error(err)

    # Tombol Segarkan
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("🔄 Segarkan Data"):
            st.session_state["refresh_product_prc"] = True
            st.rerun()
    with col2:
        st.markdown(
            f"### Menampilkan {len(st.session_state['product_prc_data'])} / {total_rows} baris",
            unsafe_allow_html=True
        )
    with col3:
        pass

# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()
