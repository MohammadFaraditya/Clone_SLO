import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.entity_api import insert_entity

# Fungsi buat template XLSX
def generate_template():
    df = pd.DataFrame(columns=["id_entity", "keterangan", "koderegion"])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    buffer.seek(0)
    return buffer

# Fungsi upload dan insert ke database 
def process_upload(file, username):
    try:
        df = pd.read_excel(file)
    except Exception:
        st.error("❌ File tidak valid. Pastikan file Excel benar.")
        return None

    # Validasi kolom
    required_cols = ["id_entity", "keterangan", "koderegion"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template: entity, keterangan, koderegion")
        return None

    # Tambahkan metadata
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kirim ke API
    res = insert_entity(df)
    if not res:
        st.error("Gagal terhubung ke server.")
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
    
# Halaman Upload Region
def app():
    # Validasi login
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        st.rerun()
        return

    # Inisialisasi state
    if "upload_done" not in st.session_state:
        st.session_state.upload_done = False
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None

    username = st.session_state.user["nama"]

    st.title("⬆️ Upload Entity")

    # Bagian Download Template 
    st.subheader("📄 Download Template Entity")
    template_file = generate_template()
    st.download_button(
        label="Download Template XLSX",
        data=template_file,
        file_name="template_entity.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Jika belum upload 
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Entity")
        uploaded_file = st.file_uploader("Pilih file Excel (Template Entity)", type=["xlsx"])

        if uploaded_file and st.button("🚀 Upload Data"):
            with st.spinner("Sedang memproses data..."):
                result_json = process_upload(uploaded_file, username)

            if result_json:
                st.session_state.upload_result = result_json
                st.session_state.upload_done = True
                st.rerun() 

    # Jika upload sudah selesai 
    else:
        result_json = st.session_state.upload_result
        message = result_json.get("message", "")
        duplicate_entities = result_json.get("duplicate_ids", [])
        invalid_regions = result_json.get("invalid_koderegion", [])

        st.success("✅ Upload selesai. Berikut hasil proses:")
        if message:
            st.info(message)

        rows = []

        # Duplicate
        for i in duplicate_entities:
            rows.append({
                "id_entity": i,
                "koderegion": "",
                "Status": "Duplicate (Skipped)"
            })

        # Invalid region
        for r in invalid_regions:
            rows.append({
                "id_entity": "",
                "koderegion": r,
                "Status": "Invalid Region (Skipped)"
            })

        if rows:
            df_display = pd.DataFrame(rows)
            st.warning("⚠️ Sebagian data tidak diproses. Lihat tabel di bawah.")
            st.dataframe(df_display)
        else:
            st.success("Semua data berhasil ditambahkan ke database")


          # Tombol kembali
        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Entity"):
            st.cache_data.clear()
            st.session_state["refresh_entity"] = True
            st.session_state.page = "entity"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()


# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()