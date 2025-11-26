import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.region_api import insert_region

# Fungsi buat template XLSX
def generate_template():
    df = pd.DataFrame(columns=["koderegion", "keterangan", "pin"])
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
    required_cols = ["koderegion", "keterangan", "pin"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template: koderegion, keterangan, pin")
        return None

    # Tambahkan metadata
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kirim ke API
    res = insert_region(df)
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

    st.title("⬆️ Upload Region")

    # Bagian Download Template 
    st.subheader("📄 Download Template Region")
    template_file = generate_template()
    st.download_button(
        label="Download Template XLSX",
        data=template_file,
        file_name="template_region.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Jika belum upload 
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Region")
        uploaded_file = st.file_uploader("Pilih file Excel (Template Region)", type=["xlsx"])

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
        duplicate_ids = result_json.get("duplicate_ids", [])

        st.success("✅ Upload selesai. Berikut hasil proses:")
        if message:
            st.info(message)

        # Tampilkan hasil jika ada duplikasi
        if duplicate_ids:
            st.warning("Beberapa data sudah ada di database dan dilewati.")
            df_display = pd.DataFrame(
                [{"koderegion": i, "Status": "Skipped"} for i in duplicate_ids]
            )

            def highlight_row(row):
                return ["" if row["Status"] == "Skipped" else ""] * len(row)

            st.dataframe(df_display.style.apply(highlight_row, axis=1))
        else:
            st.success("Semua data berhasil ditambahkan ke database.")

        # Tombol kembali
        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Region"):
            st.cache_data.clear()
            st.session_state["refresh_region"] = True
            st.session_state.page = "region"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()


# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()