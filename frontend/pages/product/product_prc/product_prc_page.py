import streamlit as st
import pandas as pd
from utils.api.product.product_prc_api import get_product_prc, update_product_prc, delete_product_prc
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 200  # jumlah data yang diambil sekali dari API

# Fungsi untuk fetch data dari API sekali saja
def fetch_product_prc_data(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_product_prc(token, offset=offset, limit=limit)
        if not res or res.status_code != 200:
            return None

        payload = res.json()
        data_chunk = payload.get("data", [])
        all_data.extend(data_chunk)

        total = payload.get("total", 0)
        offset += len(data_chunk)
        if not data_chunk or offset >= total:
            break
    return all_data

# Fungsi render AgGrid
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("No", header_name="No", width=60, pinned="left", editable=False)
    gb.configure_column("prlin", header_name="KODE PRLIN", editable=False)
    gb.configure_column("prlinname", header_name="NAMA PRLIN NAME", editable=False)
    gb.configure_column("pcode", header_name="PCODE", width=150, editable=False)
    editable_cols = ["pcodename", "unit1", "unit2", "unit3", "convunit2", "convunit3"]
    for col in editable_cols:
        if col in df.columns:
            gb.configure_column(col, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
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

# Halaman Product PRC
def app():
    # --- Validasi login ---
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("🍘 PRODUCT PRC")
    token = st.session_state.token
    updateby = st.session_state.user['nama']

    # --- Load data pertama kali jika belum ada ---
    if "product_prc_data" not in st.session_state or st.session_state.get("refresh_product_prc", True):
        with st.spinner("Memuat data product PRC..."):
            data = fetch_product_prc_data(token)
            if data is None:
                st.error("Gagal memuat data product PRC. Silahkan coba refresh halaman.")
                return
            st.session_state["product_prc_data"] = data
            st.session_state["refresh_product_prc"] = False

    data = st.session_state["product_prc_data"]
    if not data:
        st.info("Data belum tersedia.")
        return

    # --- Buat DataFrame ---
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "prlin", "prlinname", "pcode", "pcodename", "unit1", "unit2", "unit3",
        "convunit2","convunit3","createdate", "createby", "updatedate", "updateby"
    ]
    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    st.markdown(f"**Total Data product PRC: {len(df_page)}**")

    # --- Download CSV semua data ---
    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="product_prc_data_all.csv",
        mime="text/csv"
    )

    # --- Render grid ---
    updated_df, selected_rows = render_grid(df_page)
    original_map = {str(r["pcode"]): r for r in data}

    # --- Tombol Simpan Perubahan ---
    if st.button("💾 Simpan Perubahan"):
        changed_rows = []
        for _, row in updated_df.iterrows():
            sid = str(row.get("pcode"))
            orig = original_map.get(sid)
            if not orig:
                continue
            is_changed = any(
                str(row.get(c) or "") != str(orig.get(c) or "")
                for c in ["pcodename", "unit1", "unit2", "unit3", "convunit2", "convunit3"]
            )
            if is_changed:
                changed_rows.append({
                    "pcode": sid,
                    "pcodename": row.get("pcodename") or "",
                    "unit1": row.get("unit1") or "",
                    "unit2": row.get("unit2") or "",
                    "unit3": row.get("unit3") or "",
                    "convunit2": row.get("convunit2") or "",
                    "convunit3": row.get("convunit3") or "",
                    "prlin": row.get("prlin") or "",
                    "prlinname": row.get("prlinname") or "",
                    "updateby": updateby
                })

        if not changed_rows:
            st.info("Tidak ada perubahan yang disimpan.")
        else:
            success = 0
            fail_list = []
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
                    r["prlin"],
                    r["prlinname"],
                    r["updateby"]
                )
                if res and res.status_code == 200:
                    # update langsung di session state
                    for i, item in enumerate(st.session_state["product_prc_data"]):
                        if item["pcode"] == r["pcode"]:
                            st.session_state["product_prc_data"][i].update(r)
                    success += 1
                else:
                    fail_list.append(r["pcode"])

            if success > 0:
                st.success(f"{success} perubahan berhasil disimpan.")
            if fail_list:
                st.error(f"Gagal menyimpan untuk pcode: {', '.join(fail_list)}")

    # --- Tombol Hapus Data Terpilih ---
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox.")
        else:
            ids_to_delete = selected_rows["pcode"].tolist()
            res = delete_product_prc(token, ids_to_delete)
            if res and res.status_code == 200:
                # hapus langsung dari session state
                st.session_state["product_prc_data"] = [
                    r for r in st.session_state["product_prc_data"] if r["pcode"] not in ids_to_delete
                ]
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
            else:
                try:
                    err = res.json().get("error") or res.json().get("message") or "Gagal menghapus data."
                except Exception:
                    err = "Gagal menghapus data."
                st.error(err)

    # --- Tombol Segarkan Data (API ulang jika diperlukan) ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("🔄 Segarkan Data"):
            st.session_state["refresh_product_prc"] = True
            st.experimental_rerun()
    with col2:
        st.markdown(f"### Menampilkan {len(st.session_state['product_prc_data'])} baris", unsafe_allow_html=True)
    with col3:
        pass

# Jalankan langsung
if __name__ == "__main__":
    app()
