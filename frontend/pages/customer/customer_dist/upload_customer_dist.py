import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.customer.customer_dist_api import insert_customer_dist

def generate_template():
    df = pd.DataFrame(columns=["custno_dist", "custname", "branch_dist"])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    buffer.seek(0)
    return buffer

# UPLOAD
def process_upload(file, username):
    try:
        df = pd.read_excel(file, dtype={"custno_dist": str, "branch_dist": str})
    except Exception:
        st.error("❌ File tidak valid. Pastikan file Excel benar.")
        return None
    
    # VALIDASI KOLOM
    required_cols = ["custno_dist", "custname", "branch_dist"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template")
        return None
    
    # ADD METADATA
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # KIRIM DATA KE API
    res = insert_customer_dist(df)
    if not res:
        st.error("Gagal terhubung ke server")
        return None
    
    if res.status_code == 200:
        try:
            result_json = res.json()
        except Exception:
            st.success(f"✅ Berhasil upload {len(df)} record ke database area.")
            return {"message": f"Berhasil upload {len(df)} record ke database."}
        return result_json
    else:
        st.error(f"Gagal upload data: {res.text}")
        return None

# HALAMAN UPLOAD BRANCH
def app():
    #VALIDASI LOGIN
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        st.rerun()
        return
    
    # INISIALISASI STATE
    if "upload_done" not in st.session_state:
        st.session_state.upload_done = False
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None

    username = st.session_state.user["nama"]

    st.title("⬆️ Upload Customer Dist")

    # DOWNLOAD TEMPLATE
    st.subheader("📄 Download Template Customer Dist")
    template_file = generate_template()
    st.download_button(
        label="Download Template",
        data=template_file,
        file_name="template_customer_dist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # BELUM UPLOAD
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Customer DIST")
        uploaded_file = st.file_uploader("Pilih file", type=["xlsx"])

        if uploaded_file and st.button("🚀 Upload Data"):
            with st.spinner("Sedang memproses data..."):
                result_json = process_upload(uploaded_file, username)

            if result_json:
                st.session_state.upload_result = result_json
                st.session_state.upload_done = True
                st.rerun()

    # JIKA SUDAH SELESAI
    else:
        result_json = st.session_state.upload_result
        message = result_json.get("message", "")
        duplicate_internal = result_json.get("duplicate_internal", [])
        duplicate_ids = result_json.get("duplicate_ids", [])
        invalid_kodebranch = result_json.get("invalid_kodebranch", [])

        st.success("✅ Upload selesai. Berikut hasil proses:")
        if message:
            st.info(message)

        rows = []

        # DUPLIKAT INTERNAL EXCEL
        for sid in duplicate_internal:
            rows.append({
                "custno_dist": sid,
                "branch_dist": "",
                "Status": "Duplikat internal pada file Excel (Skipped)"
            })

        # DUPLIKAT DI DATABASE
        for sid in duplicate_ids:
            rows.append({
                "custno_dist": sid,
                "branch_dist": "",
                "Status": "Duplikat di database (Skipped)"
            })

        # INVALID BRANCH DIST
        for sid in invalid_kodebranch:
            rows.append({
                "custno_dist": sid,
                "branch_dist": "",
                "Status": "Invalid Custno (Skipped)"
            })


        if rows:
            df_display = pd.DataFrame(rows)
            st.warning("⚠️ Sebagian data tidak diproses. Lihat tabel di bawah.")
            st.dataframe(df_display)
        else:
            st.success("Semua data berhasil ditambahkan ke database")


        # BUTTON BACK
        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Customer DIST"):
            st.cache_data.clear()
            st.session_state["refresh_customer_dist"] = True
            st.session_state.page = "customer_dist"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()

# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()