import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit import cache_data
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from utils.api.sellout.sellout_api import (
    get_region_entity_branch_mapping,
    get_sellout_data
)

PAGE_CHUNK = 2000


# ================= CACHE =================
@cache_data(ttl=600)
def fetch_all_sellout_cached(token, kodebranch, date_from, date_to, chunk_limit=PAGE_CHUNK):
    all_data = []
    offset = 0
    limit = chunk_limit

    while True:
        res = get_sellout_data(
            kodebranch=kodebranch,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            token=token
        )

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
    res = get_region_entity_branch_mapping(token)
    if res and res.status_code == 200:
        return res.json().get("data", [])
    return []


# ================= GRID =================
def render_grid(df, grid_key):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True
    )
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_grid_options(
        suppressMovableColumns=True,
        animateRows=True
    )

    grid_response = AgGrid(
        df,
        gridOptions=gb.build(),
        height=520,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.NO_UPDATE,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=False,
        key=grid_key
    )

    return pd.DataFrame(grid_response["data"])


# ================= MAIN =================
def app():
    # ================= AUTH =================
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        return

    token = st.session_state.token

    # ================= INIT STATE =================
    st.session_state.setdefault("sellout_full", None)
    st.session_state.setdefault("last_kodebranch", None)
    st.session_state.setdefault("last_date_from", None)
    st.session_state.setdefault("last_date_to", None)
    st.session_state.setdefault("mapping_sellout", None)
    st.session_state.setdefault("grid_version", 1)

    st.title("📊 Sellout Data")

    # ================= UPLOAD BUTTON =================
    if st.button("⬆️ Upload Sellout"):
        st.session_state.page = "upload_sellout"
        st.rerun()
        return

    # ================= MAPPING =================
    if st.session_state["mapping_sellout"] is None:
        with st.spinner("Memuat mapping region / entity / branch..."):
            st.session_state["mapping_sellout"] = get_mapping_cached(token)

    mapping_df = pd.DataFrame(st.session_state["mapping_sellout"])

    # ================= FILTER =================
    with st.expander("🔍 Filter Data", expanded=True):

        # ---------- REGION ----------
        mapping_df["region_display"] = (
            mapping_df["koderegion"].fillna("") + " - " +
            mapping_df["region_name"].fillna("")
        )
        region_list = sorted(mapping_df["region_display"].unique().tolist())
        selected_region = st.selectbox(
            "Pilih Region",
            ["(Pilih Region)"] + region_list
        )

        # ---------- ENTITY ----------
        entity_list = []
        if selected_region != "(Pilih Region)":
            koderegion = selected_region.split(" - ")[0]
            entity_df = mapping_df[mapping_df["koderegion"] == koderegion]
            entity_df["entity_display"] = (
                entity_df["id_entity"].fillna("") + " - " +
                entity_df["entity_name"].fillna("")
            )
            entity_list = sorted(entity_df["entity_display"].unique().tolist())

        selected_entity = st.selectbox(
            "Pilih Entity",
            ["(Pilih Entity)"] + entity_list
        )

        # ---------- BRANCH ----------
        branch_list = []
        if selected_entity != "(Pilih Entity)":
            id_entity = selected_entity.split(" - ")[0]
            branch_df = mapping_df[mapping_df["id_entity"] == id_entity]
            branch_df["branch_display"] = (
                branch_df["kodebranch"].fillna("") + " - " +
                branch_df["nama_branch"].fillna("")
            )
            branch_list = sorted(branch_df["branch_display"].unique().tolist())

        selected_branch = st.selectbox(
            "Pilih Branch",
            ["(Pilih Branch)"] + branch_list
        )

        # ---------- DATE RANGE (WAJIB) ----------
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input(
                "Invoice Date From",
                value=None,
                format="YYYY-MM-DD"
            )
        with col2:
            date_to = st.date_input(
                "Invoice Date To",
                value=None,
                format="YYYY-MM-DD"
            )

        # ---------- APPLY FILTER ----------
        if st.button("▶ Terapkan Filter"):
            if selected_branch == "(Pilih Branch)":
                st.warning("⚠ Pilih branch terlebih dahulu")

            elif not date_from or not date_to:
                st.warning("⚠ Invoice Date From dan To wajib diisi")

            elif date_from > date_to:
                st.warning("⚠ Invoice Date From tidak boleh lebih besar dari To")

            else:
                kodebranch = selected_branch.split(" - ")[0]

                st.session_state["last_kodebranch"] = kodebranch
                st.session_state["last_date_from"] = str(date_from)
                st.session_state["last_date_to"] = str(date_to)

                with st.spinner("Mengambil seluruh data sellout..."):
                    data = fetch_all_sellout_cached(
                        token,
                        kodebranch,
                        str(date_from),
                        str(date_to)
                    )

                st.session_state["sellout_full"] = data
                st.session_state["grid_version"] += 1
                st.success(f"Berhasil memuat {len(data)} data sellout")

    # ================= ACTION BUTTON =================
    cols = st.columns([1, 6, 1])

    # ---------- FORCE RELOAD ----------
    with cols[0]:
        if st.button("🔄 Force Reload"):
            fetch_all_sellout_cached.clear()
            get_mapping_cached.clear()

            kodebranch = st.session_state.get("last_kodebranch")
            date_from = st.session_state.get("last_date_from")
            date_to = st.session_state.get("last_date_to")

            if kodebranch and date_from and date_to:
                with st.spinner("Reload data terbaru..."):
                    data = fetch_all_sellout_cached(
                        token,
                        kodebranch,
                        date_from,
                        date_to
                    )

                st.session_state["sellout_full"] = data
                st.session_state["grid_version"] += 1
                st.success(f"Reload selesai ({len(data)} data)")
            else:
                st.warning("Filter belum lengkap")

    # ---------- CLEAR DATA ----------
    with cols[2]:
        if st.button("🧹 Clear Data"):
            st.session_state["sellout_full"] = None
            st.session_state["last_kodebranch"] = None
            st.session_state["last_date_from"] = None
            st.session_state["last_date_to"] = None
            st.session_state["grid_version"] += 1
            st.info("Data lokal dibersihkan")

    # ================= GRID =================
    if st.session_state.get("sellout_full"):
        df = pd.DataFrame(st.session_state["sellout_full"])
        df.insert(0, "No", range(1, len(df) + 1))

        df_view = render_grid(
            df,
            grid_key=f"sellout_grid_{st.session_state.grid_version}"
        )

        st.markdown("---")
        st.info(
            f"Total Data: **{len(df_view)}** | "
            f"Branch: {st.session_state.get('last_kodebranch')} | "
            f"Invoice Date: {st.session_state.get('last_date_from')} "
            f"s/d {st.session_state.get('last_date_to')}"
        )
    else:
        st.info("Silakan pilih branch, invoice date, lalu klik **Terapkan Filter**")


if __name__ == "__main__":
    app()
