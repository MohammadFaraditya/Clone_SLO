import streamlit as st
import pandas as pd
from utils.api.branch_dist_api import get_all_branch_dist, update_branch_dist, delete_branch_dist
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

# FETCH ALL DATA BRANCH DIST
def fetch_all_branch_dist(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_all_branch_dist(token, offset=offset, limit=limit)
        if not res:
            break
        if res.status_code != 200:
            try:
                err = res.json().get("error") or res.json().get("message") or "Gagal memuat data branch dist"
            except Exception:
                err = "Gagal memuat data branch dist"
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

# RENDER GRID 
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('multiple', use_checkbox=True)
    gb.configure_column("No", header_name="No", width=60, pinned="left", editable=False)
    gb.configure_column("branch_dist", header_name="Branch Dist", width=150, editable=False)
    gb.configure_column("nama_branch_dist", header_name="Nama Branch Dist", width=200, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("alamat", header_name="Alamat", width=250, editable=True, cellStyle={"backgroundColor" : "#E2EAF4"})
    gb.configure_column("createdate", header_name="Created Date", editable=False)
    gb.configure_column("createby", header_name="Create By", editable=False)
    gb.configure_column("updatedate", header_name="Update Date", editable=False)
    gb.configure_column("updateby", header_name="Update By", editable=False)
    gb.configure_grid_options(domLayout='normal')
    grid_options = gb.build()
    gb.configure_side_bar()

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
        key="branch_dist_grid_all"
    )

    updated_df = pd.DataFrame(grid_response['data']).drop(columns=["No"], errors='ignore')
    selected_rows = pd.DataFrame(grid_response['selected_rows']).drop(columns=["No"], errors='ignore')
    return updated_df, selected_rows

# BRANCH DIST PAGE
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return
    
    st.title("🏚️Data Branch Dist")

    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.button("⬆️ Upload Branch Dist"):
        st.session_state.page = "upload_branch_dist"
        st.rerun()
        return
    
    # REFRESH DATA JIKA BELUM FLAG REFRESH AKTIF
    if "branch_dist_data" not in st.session_state or st.session_state.get("refresh_branch_dist", True):
        with st.spinner("Memuat semua data branch dist..."):
            all_data, total_count = fetch_all_branch_dist(token)
            st.session_state["branch_dist_data"] = all_data
            st.session_state["branch_dist_total"] = total_count
            st.session_state["refresh_branch_dist"] = False

    data = st.session_state.get("branch_dist_data", [])
    total_rows = st.session_state.get("branch_dist_total", len(data))

    if not data:
        st.info("Tidak ada data branch dist yang ditemukan")
        return
        
    st.markdown(f"**Total Data Branch Dist** : {total_rows}")

    # BUAT DATA FRAME 
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "branch_dist", "nama_branch_dist", "alamat", "createdate", "createby", "updatedate", "updateby"
    ]

    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label = "⬇️ Download CSV (Semua Data)",
        data=csv,
         file_name="branch_dst_all.csv",
        mime="text/csv"
    )

    # TAMPILKAN FRID
    updated_df, selected_rows = render_grid(df_page)

    # UPDATE DATA
    if st.button("💾 Simpan Perubahan"):
        success_count = 0

        original_dict = {r["branch_dist"]: r for r in data}

        for _, row in updated_df.iterrows():
            branchdist = row["branch_dist"]

            if branchdist not in original_dict:
                continue

            original_row = original_dict[branchdist]

            fields = ["nama_branch_dist", "alamat"]

            # PENGECEKAN APAKAH ADA PERUBAHAN
            is_changed = any(
                row[field] != original_row.get(field)
                for field in fields
            )

            if not is_changed:
                continue

            res = update_branch_dist(
                token,
                branchdist,
                row["nama_branch_dist"],
                row["alamat"],
                updateby
            )

            if res and res.status_code == 200:
                success_count +=1
            else:
                st.error(f"Gagal update branch dist {branchdist}")
        
        if success_count > 0:
            st.success(f"Berhasil memperbarui {success_count} data branch dist")
            st.session_state["refresh_branch_dist"] = True
            st.rerun()
        else:
            st.info("Tidak ada data yang berubah atau tidak ada yang berhasil diperbarui")

    # DELETE BRANCH
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox")
        else:
            ids_to_delete = selected_rows["branch_dist"].tolist()
            res = delete_branch_dist(token, ids_to_delete)
            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus")
                st.session_state["refresh_branch_dist"] = True
                st.rerun()
            else:
                try:
                    err = res.json().get("error") or res.json().get("message") or "Gagal menghapus data"
                except Exception:
                    err = "Gagal menghapus data"
                st.error(err)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("🔄 Segarkan Data"):
            st.session_state["refresh_branch_dist"] = True
            st.rerun()
    with col2:
        st.markdown(
            f"### Menampilkan {len(st.session_state['branch_dist_data'])} / {total_rows} baris", 
                unsafe_allow_html=True
            )
    with col3:
        pass

if __name__ == "__main__":
    app()


