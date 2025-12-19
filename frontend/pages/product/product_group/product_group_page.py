import streamlit as st
import pandas as pd
from utils.api.product.product_group_api import (
    get_product_group,
    update_product_group,
    delete_product_group
)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

PAGE_CHUNK = 100

# =========================
# FETCH SEMUA DATA (HANYA 1x)
# =========================
def fetch_all_product_group(token):
    all_data = []
    offset = 0

    while True:
        res = get_product_group(token, offset=offset, limit=PAGE_CHUNK)
        if not res or res.status_code != 200:
            st.error("Gagal memuat data product group.")
            break

        payload = res.json()
        chunk = payload.get("data", [])
        total = payload.get("total", 0)

        all_data.extend(chunk)
        offset += len(chunk)

        if not chunk or offset >= total:
            break

    return all_data, len(all_data)


# =========================
# AGGRID
# =========================
def render_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_column("No", pinned="left", editable=False, width=60)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)

    for col in [
        "product_group_1", "product_group_2",
        "product_group_3", "category_item", "vtkp", "npd"
    ]:
        if col in df.columns:
            gb.configure_column(col, editable=True, cellStyle={"backgroundColor": "#E2EAF4"})

    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_grid_options(enableRangeSelection=True)

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        height=500,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        key=f"product_group_grid_{len(df)}"  # 🔑 KEY DINAMIS
    )

    updated_df = pd.DataFrame(grid["data"]).drop(columns=["No"], errors="ignore")
    selected_df = pd.DataFrame(grid["selected_rows"]).drop(columns=["No"], errors="ignore")

    return updated_df, selected_df


# =========================
# PAGE
# =========================
def app():
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        return

    st.title("🍱 PRODUCT GROUP")
    token = st.session_state.token
    updateby = st.session_state.user["nama"]

    # =========================
    # UPLOAD BUTTON (TIDAK DIHILANGKAN)
    # =========================
    if st.button("⬆️ Upload product group"):
        st.session_state["refresh_after_upload"] = True
        st.session_state.page = "upload_product_group"
        st.rerun()

    # =========================
    # LOAD DATA (FULL FETCH HANYA DI SINI)
    # =========================
    if (
        "product_group_data" not in st.session_state
        or st.session_state.pop("refresh_after_upload", False)
    ):
        with st.spinner("Memuat semua data product group..."):
            data, total = fetch_all_product_group(token)
            st.session_state["product_group_data"] = data
            st.session_state["product_group_total"] = total

    data = st.session_state["product_group_data"]
    st.markdown(f"**Total Data: {len(data)}**")

    df = pd.DataFrame(data).reset_index(drop=True)
    df.insert(0, "No", range(1, len(df) + 1))
    df["No"] = df["No"].astype(str)

    updated_df, selected_rows = render_grid(df)

    original_map = {str(r["pcode"]): r for r in data}

    # =========================
    # SIMPAN PERUBAHAN (NO REFETCH)
    # =========================
    if st.button("💾 Simpan Perubahan"):
        changed = []

        for _, row in updated_df.iterrows():
            pcode = str(row["pcode"])
            orig = original_map.get(pcode)

            if not orig:
                continue

            if any(str(row[k] or "") != str(orig.get(k) or "") for k in [
                "product_group_1", "product_group_2",
                "product_group_3", "category_item", "vtkp", "npd"
            ]):
                payload = row.to_dict()
                payload["updateby"] = updateby
                changed.append(payload)

        if not changed:
            st.info("Tidak ada perubahan.")
        else:
            for r in changed:
                res = update_product_group(
                    token,
                    r["pcode"],
                    r["product_group_1"],
                    r["product_group_2"],
                    r["product_group_3"],
                    r["category_item"],
                    r["vtkp"],
                    r["npd"],
                    updateby
                )
                if res and res.status_code == 200:
                    original_map[r["pcode"]].update(r)

            st.success("Perubahan berhasil disimpan.")
            st.rerun()

    # =========================
    # DELETE (NO REFETCH)
    # =========================
    if st.button("🗑️ Hapus Data Terpilih"):
        if selected_rows.empty:
            st.warning("Pilih minimal 1 baris.")
        else:
            ids = selected_rows["pcode"].tolist()
            res = delete_product_group(token, ids)

            if res and res.status_code == 200:
                st.session_state["product_group_data"] = [
                    r for r in data if r["pcode"] not in ids
                ]
                st.success(f"{len(ids)} data dihapus.")
                st.rerun()
            else:
                st.error("Gagal menghapus data.")
