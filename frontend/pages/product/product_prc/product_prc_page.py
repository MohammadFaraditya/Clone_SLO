import streamlit as st
import pandas as pd
from utils.api.product.product_prc_api import (
    get_product_prc,
    update_product_prc,
    delete_product_prc
)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 1500


# FETCH SEKALI + CACHE 
@st.cache_data(ttl=120)
def fetch_product_prc_once(token):
    res = get_product_prc(token, offset=0, limit=PAGE_CHUNK)
    if not res or res.status_code != 200:
        return [], 0

    payload = res.json()
    data = payload.get("data", [])
    return data, len(data)


def refresh_product_prc():
    fetch_product_prc_once.clear()
    st.session_state["refresh_product_prc"] = True


# GRID 
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_column("No", width=80, pinned="left", editable=False)
    gb.configure_column("prlin", width=150, editable=False)
    gb.configure_column("prlinname", width=300, editable=False)
    gb.configure_column("pcode", width=150, editable=False)

    editable_cols = [
        "pcodename", "unit1", "unit2", "unit3",
        "convunit2", "convunit3"
    ]
    for col in editable_cols:
        gb.configure_column(
            col,
            editable=True,
            cellStyle={"backgroundColor": "#E2EAF4"}
        )

    gb.configure_column("createdate", editable=False)
    gb.configure_column("createby", editable=False)
    gb.configure_column("updatedate", editable=False)
    gb.configure_column("updateby", editable=False)

    gb.configure_default_column(filter=True, sortable=True, resizable=True)

    gb.configure_selection(
        selection_mode="multiple",
        use_checkbox=True
    )

    gb.configure_grid_options(
        enableRangeSelection=False,
        suppressRowClickSelection=False,
        sideBar=False
    )

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        height=500,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        key="product_prc_grid_all"
    )

    updated_df = pd.DataFrame(grid["data"]).drop(columns=["No"], errors="ignore")
    selected_rows = pd.DataFrame(grid["selected_rows"]).drop(columns=["No"], errors="ignore")

    return updated_df, selected_rows


# PAGE

def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("🍘 PRODUCT PRC")

    token = st.session_state.token
    updateby = st.session_state.user["nama"]

    # LOAD DATA (CEPAT, CACHE)
    if "product_prc_data" not in st.session_state or st.session_state.get("refresh_product_prc", True):
        with st.spinner("Memuat data product PRC..."):
            data, total = fetch_product_prc_once(token)
            st.session_state["product_prc_data"] = data
            st.session_state["product_prc_total"] = total
            st.session_state["refresh_product_prc"] = False

    data = st.session_state.get("product_prc_data", [])
    total_rows = st.session_state.get("product_prc_total", len(data))

    if not data:
        st.info("Tidak ada data product PRC.")
        return

    st.markdown(f"**Total Data product PRC: {total_rows}**")

    # DATAFRAME
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))

    ordered_cols = [
        "No", "prlin", "prlinname", "pcode", "pcodename",
        "unit1", "unit2", "unit3",
        "convunit2", "convunit3",
        "createdate", "createby",
        "updatedate", "updateby"
    ]
    df_page = df_page[[c for c in ordered_cols if c in df_page.columns]]

    # DOWNLOAD CSV
    st.download_button(
        "⬇️ Download CSV (Semua Data)",
        df_page.to_csv(index=False).encode("utf-8"),
        "product_prc_data_all.csv",
        "text/csv"
    )

    # GRID
    updated_df, selected_rows = render_grid(df_page)

    # UPDATE (SAMA POLA)
    if st.button("💾 Simpan Perubahan"):
        success = 0
        original_map = {r["pcode"]: r for r in data}

        for _, row in updated_df.iterrows():
            pid = row["pcode"]
            orig = original_map.get(pid)
            if not orig:
                continue

            if any(
                str(row[c] or "") != str(orig.get(c) or "")
                for c in ["pcodename", "unit1", "unit2", "unit3", "convunit2", "convunit3"]
            ):
                res = update_product_prc(
                    token,
                    pid,
                    row["pcodename"],
                    row["unit1"],
                    row["unit2"],
                    row["unit3"],
                    row["convunit2"],
                    row["convunit3"],
                    row["prlin"],
                    row["prlinname"],
                    updateby
                )
                if res and res.status_code == 200:
                    success += 1

        if success > 0:
            st.success(f"{success} data berhasil diperbarui!")
            refresh_product_prc()
            st.rerun()
        else:
            st.info("Tidak ada perubahan yang disimpan.")

    # DELETE (SAMA POLA)
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus.")
        else:
            ids_to_delete = selected_rows["pcode"].tolist()

            res = delete_product_prc(token, ids_to_delete)

            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
                refresh_product_prc()
                st.rerun()
            else:
                try:
                    err = res.json().get("error") or res.json().get("message")
                except Exception:
                    err = "Gagal menghapus data."
                st.error(err)


    # FOOTER
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("🔄 Segarkan Data"):
            refresh_product_prc()
            st.rerun()
    with col2:
        st.markdown(f"### Menampilkan {len(data)} / {total_rows} baris")
    with col3:
        pass


if __name__ == "__main__":
    app()
