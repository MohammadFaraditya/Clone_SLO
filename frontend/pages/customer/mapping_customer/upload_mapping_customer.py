import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.customer.mapping_customer_api import insert_mapping_customer

# ============================
# GENERATE TEMPLATE XLSX
# ============================
def generate_template():
    df = pd.DataFrame(columns=["kodebranch", "custno", "branch_dist", "custno_dist"])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    buffer.seek(0)
    return buffer

# ============================
# NORMALISASI VALUE
# ============================
def normalize_value(val):
    if isinstance(val, list):
        return ", ".join([str(v) for v in val])
    if val is None:
        return ""
    return str(val)

# ============================
# PROSES UPLOAD
# ============================
def process_upload(file, username):
    try:
        df = pd.read_excel(file, dtype=str)
    except Exception:
        st.error("❌ File tidak valid. Pastikan file Excel benar.")
        return None

    required_cols = ["kodebranch", "custno", "branch_dist", "custno_dist"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template")
        return None

    for col in required_cols:
        df[col] = df[col].apply(normalize_value)

    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    res = insert_mapping_customer(df)
    if not res:
        st.error("Gagal terhubung ke server")
        return None

    if res.status_code == 200:
        try:
            return res.json()
        except Exception:
            return {"message": f"Berhasil upload {len(df)} record ke database."}
    else:
        st.error(f"Gagal upload data: {res.text}")
        return None

# ============================
# MAIN PAGE
# ============================
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        st.rerun()
        return

    if "upload_done" not in st.session_state:
        st.session_state.upload_done = False
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None

    username = st.session_state.user["nama"]

    st.title("⬆️ Upload Mapping Customer")

    # Download template
    st.subheader("📄 Download Template Mapping Customer")
    st.download_button(
        label="Download Template",
        data=generate_template(),
        file_name="template_mapping_customer.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ============================
    # UPLOAD
    # ============================
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Mapping Customer")
        uploaded_file = st.file_uploader("Pilih file", type=["xlsx"])

        if uploaded_file and st.button("🚀 Upload Data"):
            with st.spinner("Sedang memproses data..."):
                result_json = process_upload(uploaded_file, username)
            if result_json:
                st.session_state.upload_result = result_json
                st.session_state.upload_done = True
                st.rerun()

    # ============================
    # HASIL UPLOAD
    # ============================
    else:
        result_json = st.session_state.upload_result
        message = result_json.get("message", "")
        duplicate_entities = result_json.get("skipped_duplicate", [])
        skipped_invalid_prc = result_json.get("skipped_invalid_prc", [])
        skipped_invalid_dist = result_json.get("skipped_invalid_dist", [])

        st.success("✅ Upload selesai. Berikut hasil proses:")

        if message:
            st.info(message)

        # Build tabel skip
        rows = []
        for i in duplicate_entities:
            rows.append({"custno": normalize_value(i), "custno_dist": "", "Status": "Duplicated (Skipped)"})
        for r in skipped_invalid_prc:
            rows.append({"custno": normalize_value(r), "custno_dist": "", "Status": "Customer PRC belum terdaftar (Skipped)"})
        for t in skipped_invalid_dist:
            rows.append({"custno": "", "custno_dist": normalize_value(t), "Status": "Customer DIST belum terdaftar (Skipped)"})

        if rows:
            df_display = pd.DataFrame(rows)
            st.warning("⚠️ Sebagian data tidak diproses. Lihat tabel di bawah.")
            st.dataframe(df_display, width="100%", hide_index=True)
        else:
            st.success("🔥 Semua data berhasil ditambahkan tanpa error.")

        st.markdown("---")

        # ============================
        # KEMBALI KE HALAMAN MAPPING CUSTOMER
        # ============================
        if st.button("⬅️ Kembali ke Data Mapping Customer"):
            st.session_state.refresh_mapping_customer = True
            st.session_state.page = "mapping_customer"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()


if __name__ == "__main__":
    app()
