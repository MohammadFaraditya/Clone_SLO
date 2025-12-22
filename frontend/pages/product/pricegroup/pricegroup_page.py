import streamlit as st
import pandas as pd
from utils.api.product.pricegroup_api import (
    get_data_pricegroup,
    update_pricegroup,
    delete_pricegroup
)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 1500


def to_float(val):
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# FETCH SEKALI + CACHE
@st.cache_data(ttl=120)
def fetch_pricegroup_once(token):
    res = get_data_pricegroup(token, offset=0, limit=PAGE_CHUNK)
    if not res or res.status_code != 200:
        return [], 0

    payload = res.json()
    data = payload.get("data", [])
    return data, len(data)


def refresh_pricegroup():
    fetch_pricegroup_once.clear()
    st.session_state["refresh_pricegroup"] = True


# GRID
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_column("No", header_name="No", width=80, pinned="left", editable=False)
    gb.configure_column("pricecode", header_name="PRICE CODE", width=100, editable=False)
    gb.configure_column("pricename", header_name="PRICE NAME", width=400, editable=False)
    gb.configure_column("pcode", header_name="PCODE", width=150, editable=False)
    gb.configure_column("pcodename", header_name="PCODE NAME", width=600, editable=False)

    gb.configure_column("sellprice1", header_name="SELLPRICE 1", width=200, editable=True,
                        cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice2", header_name="SELLPRICE 2", width=200, editable=True,
                        cellStyle={"backgroundColor": "#E2EAF4"})
    gb.configure_column("sellprice3", header_name="SELLPRICE 3", width=200, editable=True,
                        cellStyle={"backgroundColor": "#E2EAF4"})

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

    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        key="pricegroup_grid_all"
    )

    update_df = pd.DataFrame(grid_response["data"]).drop(columns=["No"], errors="ignore")
    selected_rows = pd.DataFrame(grid_response["selected_rows"]).drop(columns=["No"], errors="ignore")

    return update_df, selected_rows


# PAGE
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    st.title("📍 Data Pricegroup")

    token = st.session_state.token
    updateby = st.session_state.user["nama"]

    if st.button("⬆️ Upload Pricegroup"):
        st.session_state.page = "upload_pricegroup"
        st.rerun()
        return

    # LOAD DATA (CEPAT)
    if "pricegroup_data" not in st.session_state or st.session_state.get("refresh_pricegroup", True):
        with st.spinner("Memuat data pricegroup..."):
            data, total = fetch_pricegroup_once(token)
            st.session_state["pricegroup_data"] = data
            st.session_state["pricegroup_total"] = total
            st.session_state["refresh_pricegroup"] = False

    data = st.session_state.get("pricegroup_data", [])
    total_rows = st.session_state.get("pricegroup_total", len(data))

    if not data:
        st.info("Tidak ada data pricegroup yang ditemukan.")
        return

    st.markdown(f"**Total Data pricegroup: {total_rows}**")

    # DATAFRAME
    df_page = pd.DataFrame(data).reset_index(drop=True)
    df_page.insert(0, "No", range(1, len(df_page) + 1))

    ordered_cols = [
        "No", "pricecode", "pricename", "pcode", "pcodename",
        "sellprice1", "sellprice2", "sellprice3",
        "createdate", "createby", "updatedate", "updateby"
    ]
    df_page = df_page[[c for c in ordered_cols if c in df_page.columns]]

    # DOWNLOAD CSV
    csv = df_page.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download CSV (Semua Data)",
        data=csv,
        file_name="pricegroup_data_all.csv",
        mime="text/csv"
    )

    # GRID
    updated_df, selected_rows = render_grid(df_page)

    # SIMPAN PERUBAHAN
    if st.button("💾 Simpan Perubahan"):
        success_count = 0
        original_dict = {(r["pcode"], r["pricecode"]): r for r in data}

        for _, row in updated_df.iterrows():
            key = (row["pcode"], row["pricecode"])
            if key not in original_dict:
                continue

            original = original_dict[key]

            if (
                to_float(row["sellprice1"]) != to_float(original.get("sellprice1")) or
                to_float(row["sellprice2"]) != to_float(original.get("sellprice2")) or
                to_float(row["sellprice3"]) != to_float(original.get("sellprice3"))
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
            refresh_pricegroup()
            st.rerun()
        else:
            st.info("Tidak ada perubahan yang perlu disimpan.")

    # DELETE
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris yang ingin dihapus.")
        else:
            ids_to_delete = [
                {"pricecode": r["pricecode"], "pcode": r["pcode"]}
                for _, r in selected_rows.iterrows()
            ]
            res = delete_pricegroup(token, ids_to_delete)
            if res and res.status_code == 200:
                st.success(f"{len(ids_to_delete)} baris berhasil dihapus!")
                refresh_pricegroup()
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
            refresh_pricegroup()
            st.rerun()
    with col2:
        st.markdown(f"### Menampilkan {len(data)} / {total_rows} baris")
    with col3:
        pass


if __name__ == "__main__":
    app()
