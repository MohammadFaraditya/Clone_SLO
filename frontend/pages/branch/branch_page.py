import streamlit as st
import pandas as pd
from utils.api.branch_api import get_all_branch
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

# FETCH SEMUA DATA BRANCH
def fetch_all_branch(token):
    all_data = []
    offset = 0
    limit = PAGE_CHUNK

    while True:
        res = get_all_branch(token, offset=offset, limit=limit)
        if not res:
            break
        if res.status_code != 200:
            try:
                err = res.json().get("error") or res.json().get("message") or "Gagal memuat data branch."
            except Exception:
                err = "Gagal memuat data branch"
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

#RENDER GRID
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("No", header_name="No", width=60, pinned="left", editable=False)
    gb.configure_column("koderegion", header_name="Kode Region", width=100, pinned="left", editable=False)
    gb.configure_column("nama_region", header_name="Nama Region", width=150, pinned="left", editable=False)
    gb.configure_column("entity", header_name="Entity", width=100, pinned="left", editable=False)
    gb.configure_column("nama_entity", header_name="Nama Entity", width=150, pinned="left", editable=False)
    gb.configure_column("kodebranch", header_name="Kode Branch", width=100, pinned="left", editable=False)
    gb.configure_column("nama_branch", header_name="Nama Branch", width=200, pinned="left", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("alamat", header_name="Alamat", width=250, pinned="left", editable=False)
    gb.configure_column("id_area", header_name="ID Area", width=100, pinned="left", editable=False)
    gb.configure_column("createdate", header_name="Create Date", width=100, pinned="left", editable=False)
    gb.configure_column("createby", header_name="Create By", width=100, pinned="left", editable=False)
    gb.configure_column("updatedate", header_name="Update Date", width=100, pinned="left", editable=False)
    gb.configure_column("updateby", header_name="Update By", width=100, pinned="left", editable=False)
    gb.configure_column("host", header_name="Host", width=100, pinned="left", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("ftp_user", header_name="FTP User", width=100, pinned="left", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("ftp_password", header_name="FTP Password", width=100, pinned="left", editable=True, cellStyle={"backgroundColor": "#E2EAF4"})
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
        key="branch_grid_all"
    )

    update_df = pd.DataFrame(grid_response['data'].drop(columns=["No"], errors='ignore'))
    selected_rows = pd.DataFrame(grid_response['selected_rows']).drop(columns=["No"], errors='ignore')
    return update_df, selected_rows

    #HALAMAN ENTITY PAGE
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return
        
    st.title("🏚️Data Branch")

    token = st.session_state.token
    updateby = st.session_state.user['nama']

    if st.button("⬆️ Upload Branch"):
        st.session_state.page = "upload_entity"
        st.rerun()
        return
    
    if "branch_data" not in st.session_state or st.session_state.get("refresh_branch", True):
        with st.spinner("Memuat semua data branch..."):
            all_data, total_count = fetch_all_branch(token)
            st.session_state["branch_data"] = all_data
            st.session_state["branch_total"] = total_count
            st.session_state["refresh_branch"] = False

    data = st.session_state.get("branch_data", [])
    total_rows = st.session_state.get("branch_total", len(data))

    if not data:
        st.info("Tidak ada data branch yang ditemukan")
        return
        
    st.markdown(f"**Total Data Branch: {total_rows}**")

    #DATA FRAME
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))
    df_page["No"] = df_page["No"].astype(str)

    ordered_cols = [
        "No", "koderegion","nama_branch","entity","nama_entity","kodebranch",
        "nama_branch","alamat","id_area","createdate","createby","updatedate",
        "updateby","host","ftp_user","ftp_password"
    ]

    df_page = df_page[[col for col in ordered_cols if col in df_page.columns]]

    csv = df_page.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="branch_all_data.csv",
        mime="text/csv"
    )

    #TAMPILKAN GRID
    update_df, selected_rows = render_grid(df_page)

    #SIMPAN PERUBAHAN
    if st.button("💾 Simpan Perubahan"):
        success_count = 0
        original_dict = {r["branch"]: r for r in data}

        for _, row in update_df.iterrows():
            kodebranch = row["kodebranch"]
            if kodebranch not in original_dict:
                continue
                
            original_row = original_dict[kodebranch]

    #DELETE         
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus dengan centang checkbox.")

    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("🔄 Segarkan Data"):
            st.session_state["refresh_branch"] = True
            st.rerun()
    with col2:
        st.markdwon(
            f"### Menampilkan {len(st.session_state['branch_data'])} / {total_rows} baris", 
                unsafe_allow_html=True
            )
    with col3:
        pass

if __name__ == "__main__":
    app()