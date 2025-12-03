import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.area.branch_dist_api import insert_branch_dist

# BUAT TEMPLATE XLSX
def generate_template():
    df = pd.DataFrame(columns=["branch_dist", "nama_branch_dist", "alamat"])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    buffer.seek(0)
    return buffer

# UPLOAD DAN INSERT DATANASE
def process_upload(file, username):
    try:
        df = pd.read_excel(file)
    except Exception as e:
        st.error(f"❌ File tidak valid. Error detail: {e}")
        return None
    
    # VALIDASI KOLOM
    required_cols = ["branch_dist", "nama_branch_dist", "alamat"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template")
        return None
    
    # ADD METADATA
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # INSERT DATA
    res = insert_branch_dist(df)
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
    
# UPLOAD BRANCH PAGE
def app():
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

    st.title("⬆️ Upload Branch Dist")

    # DOWNLOAD TEMPLATE
    st.subheader("📄 Download Template Branch Dist")
    template_file = generate_template()
    st.download_button(
        label="Download Template",
        data=template_file,
        file_name="template_branch_dist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # BELUM UPLOAD
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Branch Dist")
        uploaded_file = st.file_uploader("Pilih file", type=["xlsx"])

        if uploaded_file and st.button("🚀 Upload Data"):
            with st.spinner("Sedang memproses data..."):
                result_json = process_upload(uploaded_file, username)

            if result_json:
                st.session_state.upload_result = result_json
                st.session_state.upload_done = True
                st.rerun()
    # SELESAI UPLOAD
    else:
        result_json = st.session_state.upload_result
        message = result_json.get("message", "")
        duplicate_entities = result_json.get("duplicate_ids", [])

        st.success("✅ Upload selesai. Berikut hasil proses:")
        if message:
            st.info(message)

        rows = []

        # DUPLICATE
        for i in duplicate_entities:
            rows.append({
                "branch dist" : i,
                "Status" : "Duplicated(Skipped)"
            })
        
        if rows:
            df_display = pd.DataFrame(rows)
            st.warning("⚠️ Sebagian data tidak diproses. Lihat tabel di bawah.")
            st.dataframe(df_display)
        else:
            st.success("Semua data berhasil ditambahkan ke database")

        
        # BUTTON BACK
        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Branch Dist"):
            st.cache_data.clear()
            st.session_state["refresh_branch_dist"] = True
            st.session_state.page = "branch_dist"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()

if __name__ == "__main__":
    app()