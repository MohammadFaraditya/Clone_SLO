import streamlit as st
import pandas as pd
from utils.api.sellout.sellout_api import upload_sellout_data
from utils.api.sellout.sellout_api import get_region_entity_branch_mapping


# ================= MAIN =================
def app():
    # ================= AUTH =================
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        st.rerun()
        return

    token = st.session_state.token
    username = st.session_state.user["nama"]

    # ================= INIT STATE =================
    st.session_state.setdefault("upload_done", False)
    st.session_state.setdefault("upload_result", None)
    st.session_state.setdefault("mapping_sellout", None)

    st.title("⬆️ Upload Sellout")

    # ================= LOAD MAPPING =================
    if st.session_state["mapping_sellout"] is None:
        with st.spinner("Memuat data region / entity / branch..."):
            res = get_region_entity_branch_mapping(token)
            if res and res.status_code == 200:
                st.session_state["mapping_sellout"] = res.json().get("data", [])
            else:
                st.error("Gagal memuat data branch")
                return

    df = pd.DataFrame(st.session_state["mapping_sellout"])

    if df.empty:
        st.warning("Data mapping kosong")
        return

    # ================= NORMALISASI KOLOM =================
    rename_map = {}

    if "region_name" in df.columns:
        rename_map["region_name"] = "region"
    elif "nama_region" in df.columns:
        rename_map["nama_region"] = "region"

    if "entity_name" in df.columns:
        rename_map["entity_name"] = "entity"
    elif "nama_entity" in df.columns:
        rename_map["nama_entity"] = "entity"

    if "branch_code" in df.columns:
        rename_map["branch_code"] = "kodebranch"

    if "branch_name" in df.columns:
        rename_map["branch_name"] = "nama_branch"

    df = df.rename(columns=rename_map)

    required_cols = {"region", "entity", "kodebranch", "nama_branch"}
    missing = required_cols - set(df.columns)

    if missing:
        st.error(f"Kolom mapping tidak lengkap: {missing}")
        return

    # ================= FILTER REGION =================
    region_list = sorted(df["region"].dropna().unique().tolist())
    selected_region = st.selectbox(
        "Pilih Region",
        ["(Pilih Region)"] + region_list
    )

    if selected_region == "(Pilih Region)":
        st.info("Silakan pilih Region")
        return

    df_region = df[df["region"] == selected_region].copy()

    # ================= FILTER ENTITY =================
    entity_list = sorted(df_region["entity"].dropna().unique().tolist())
    selected_entity = st.selectbox(
        "Pilih Entity",
        ["(Pilih Entity)"] + entity_list
    )

    if selected_entity == "(Pilih Entity)":
        st.info("Silakan pilih Entity")
        return

    df_entity = df_region[df_region["entity"] == selected_entity].copy()

    # ================= FILTER BRANCH =================
    df_entity["branch_display"] = (
        df_entity["kodebranch"].astype(str)
        + " - "
        + df_entity["nama_branch"].astype(str)
    )

    branch_list = sorted(df_entity["branch_display"].unique().tolist())
    selected_branch = st.selectbox(
        "Pilih Branch",
        ["(Pilih Branch)"] + branch_list
    )

    # ================= FILE UPLOAD =================
    uploaded_file = st.file_uploader(
        "Pilih file sellout",
        type=["xlsx", "csv", "txt"]
    )

    # ================= UPLOAD =================
    if st.button("🚀 Upload Sellout"):
        if selected_branch == "(Pilih Branch)":
            st.warning("⚠ Branch wajib dipilih")
            return

        if not uploaded_file:
            st.warning("⚠ File belum dipilih")
            return

        branch_code = selected_branch.split(" - ")[0]

        with st.spinner("Mengunggah dan memproses data sellout..."):
            res = upload_sellout_data(
                branch=branch_code,
                file=uploaded_file,
                username=username,
                token=token
            )

        if not res:
            st.error("❌ Tidak ada respon dari server")
            return

        if res.status_code == 200:
            try:
                result = res.json()
            except Exception:
                result = {"message": "Upload sellout berhasil"}

            st.session_state.upload_done = True
            st.session_state.upload_result = result
            st.rerun()
        else:
            st.error(f"❌ Upload gagal: {res.text}")

    # ================= RESULT =================
    if st.session_state.upload_done:
        result = st.session_state.upload_result or {}

        st.success("✅ Upload Sellout Berhasil")

        if "message" in result:
            st.info(result["message"])

        if "total_row" in result:
            st.write(f"📦 Total data diproses: **{result['total_row']} baris**")

        st.markdown("---")
        st.warning(
            "ℹ️ Data sellout pada **invoice date yang sama** "
            "akan otomatis **direplace** sesuai file yang diupload."
        )

        if st.button("⬅️ Kembali ke Data Sellout"):
            st.cache_data.clear()
            st.session_state["refresh_sellout"] = True
            st.session_state.page = "sellout"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()


# ================= RUN =================
if __name__ == "__main__":
    app()
