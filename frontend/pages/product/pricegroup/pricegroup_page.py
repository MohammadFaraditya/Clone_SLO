import streamlit as st
import pandas as pd
from utils.api.product.pricegroup_api import get_data_pricegroup, update_pricegroup, delete_pricegroup
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

def to_float(val):
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# FETCH
def fetch_all_pricegroup(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True: 
        res = get_data_pricegroup(token, offset=offset, limit=limit)
        if not res:
            break
        if res.status_code != 200:
            try:
                err = res.json().get("error") or res.json().get("message") or "Gagal memuat data pricegroup."
            except Exception:
                err = "Gagal memuat data pricegroup"
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
    gb.configure_column("No", header_name="No", width=80, pinned="left", editable=False)
    gb.configure_column("pricecode", header_name="PRICE CODE", width=100, editable=False)
    gb.configure_column("pricename", header_name="PRICE NAME", width=400, editable=False)
    gb.configure_column("pcode", header_name="PCODE", width=150, editable=False)
    gb.configure_column("pcodename", header_name="PCODE NAME", width=600, editable=False)
    gb.configure_column("sellprice1", header_name="SELLPRICE 1", width=200, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice2", header_name="SELLPRICE 2", width=200, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice3", header_name="SELLPRICE 3", width=200, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
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
        key="pricegroup_grid_all"
    )

    update_df = pd.DataFrame(grid_response['data']).drop(columns=["No"], errors='ignore')
    selected_rows = pd.DataFrame(grid_response['selected_rows']).drop(columns=["No"], errors='ignore')
    return update_df,selected_rows

# HALAMAN PRICEGROUP PAGE
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("📍 Data Pricegroup")

    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.button("⬆️ Upload Pricegroup"):
        st.session_state.page = "upload_pricegroup"
        st.rerun()
        return

    # Refresh data hanya jika belum ada atau flag refresh aktif
    if "pricegroup_data" not in st.session_state or st.session_state.get("refresh_pricegroup", True):
        with st.spinner("Memuat semua data pricegroup..."):
            all_data, total_count = fetch_all_pricegroup(token)
            st.session_state["pricegroup_data"] = all_data
            st.session_state["pricegroup_total"] = total_count
            st.session_state["refresh_pricegroup"] = False

    data = st.session_state.get("pricegroup_data", [])
    total_rows = st.session_state.get("pricegroup_total", len(data))

    if not data:
        st.info("Tidak ada data pricegroup yang ditemukan.")
        return

    st.markdown(f"**Total Data pricegroup: {total_rows}**")

    # Buat DataFrame lengkap
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "pricecode", "pricename", "pcode", "pcodename", "sellprice1", "sellprice2", "sellprice3",
        "createdate", "createby", "updatedate", "updateby"
    ]
    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="pricegroup_data_all.csv",
        mime="text/csv"
    )

    # Tampilkan grid
    updated_df, selected_rows = render_grid(df_page)

    # Tombol Simpan Perubahan 
    if st.button("💾 Simpan Perubahan"):
        success_count = 0
        original_dict = {(r["pcode"], r["pricecode"]): r for r in data}

        for _, row in updated_df.iterrows():
            key = (row["pcode"], row["pricecode"])
            if key not in original_dict:
                continue

            original_row = original_dict[key]

            # Cek apakah ada perubahan di salah satu sellprice
            if (
                    to_float(row["sellprice1"]) != to_float(original_row.get("sellprice1")) or
                    to_float(row["sellprice2"]) != to_float(original_row.get("sellprice2")) or
                    to_float(row["sellprice3"]) != to_float(original_row.get("sellprice3"))
                ):

                res = update_pricegroup(
                    token,
                    row["pcode"],
                    row["pricecode"],
                    row["sellprice1"],
                    row["sellprice2"],
                    row["sellprice3"],
                    updateby
                )

                if res and res.status_code == 200:
                    success_count += 1

        if success_count > 0:
            st.success(f"{success_count} data berhasil diperbarui!")
            st.session_state["refresh_pricegroup"] = True
            st.rerun()
        else:
            st.info("Tidak ada perubahan yang perlu disimpan.")


    #Tombol Hapus Baris Terpilih
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox.")
        else:
            # Buat list of dicts sesuai backend
            ids_to_delete = [
                {"pricecode": r["pricecode"], "pcode": r["pcode"]}
                for _, r in selected_rows.iterrows()
            ]
            res = delete_pricegroup(token, ids_to_delete)
            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
                st.session_state["refresh_pricegroup"] = True
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
            st.session_state["refresh_pricegroup"] = True
            st.rerun()
    with col2:
        st.markdown(
            f"### Menampilkan {len(st.session_state['pricegroup_data'])} / {total_rows} baris",
            unsafe_allow_html=True
        )
    with col3:
        pass

# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()