import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.product.product_group_api import insert_product_group

# Fungsi buat template XLSX
def generate_template():
    df = pd.DataFrame(columns=[
        "group_code","brand", "pcode", "product_group_1", "product_group_2",
        "product_group_3", "category_item", "vtkp", "npd"
    ])
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
    required_cols = ["group_code","brand", "pcode", "product_group_1", "product_group_2", "product_group_3", "category_item", "vtkp", "npd"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom harus sesuai template")
        return None

    # Tambahkan metadata
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kirim ke API
    res = insert_product_group(df)
    if not res:
        st.error("Gagal terhubung ke server.")
        return None

    if res.status_code == 200:
        try:
            return res.json()
        except Exception:
            st.success(f"✅ Berhasil upload {len(df)} record ke database.")
            return {"message": f"Berhasil upload {len(df)} record ke database."}
    else:
        st.error(f"Gagal upload data: {res.text}")
        return None

# Halaman Upload 
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

    st.title("⬆️ Upload Product Group")

    # Bagian Download Template 
    st.subheader("📄 Download Template Product Group")
    template_file = generate_template()
    st.download_button(
        label="Download Template XLSX",
        data=template_file,
        file_name="template_product_group.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Jika belum upload 
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Product Group")
        uploaded_file = st.file_uploader("Pilih file Excel (Template Product Group)", type=["xlsx"])

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
        inserted_count = result_json.get("inserted", 0)
        duplicate_ids = result_json.get("duplicate_in_product_group", [])
        invalid_ids = result_json.get("not_registered_in_product_prc", [])
        message = result_json.get("message", "")

        st.success(f"✅ Upload selesai. {inserted_count} record berhasil ditambahkan.")
        if message:
            st.info(message)

        # Tampilkan hasil duplikat
        if duplicate_ids:
            st.warning(f"Beberapa data sudah ada di database dan dilewati: {', '.join(duplicate_ids)}")

        # Tampilkan hasil pcode tidak terdaftar
        if invalid_ids:
            st.error(f"Beberapa pcode tidak terdaftar di product_prc dan dilewati: {', '.join(invalid_ids)}")

        # Tombol kembali
        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Product Group"):

            st.session_state["refresh_product_group"] = False
            st.session_state.page = "product_group"

            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()

# Jalankan langsung (opsional)
if __name__ == "__main__":
    app()
