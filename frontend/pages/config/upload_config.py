import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from utils.api.config.config_api import insert_config


# TEMPLATE XLSX
def generate_template():
    cols = [
        "branch", "kodebranch", "id_salesman", "id_customer", "id_product",
        "qty1", "qty2", "qty3", "price", "grossamount",
        "discount1", "discount2", "discount3", "discount4",
        "discount5", "discount6", "discount7", "discount8",
        "total_discount", "dpp", "tax", "nett",
        "order_no", "order_date",
        "invoice_no", "invoice_date",
        "invoice_type",
        "sfa_order_no", "sfa_order_date",
        "file_extension", "separator_file",
        "first_row", "flag_bonus"
    ]

    df = pd.DataFrame(columns=cols)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    buffer.seek(0)
    return buffer


# PROCESS UPLOAD
def process_upload(file, username):
    try:
        df = pd.read_excel(file)
    except Exception:
        st.error("❌ File tidak valid. Pastikan file Excel benar.")
        return None

    required_cols = [
        "branch", "kodebranch", "id_salesman", "id_customer", "id_product",
        "qty1", "qty2", "qty3", "price", "grossamount",
        "discount1", "discount2", "discount3", "discount4",
        "discount5", "discount6", "discount7", "discount8",
        "total_discount", "dpp", "tax", "nett",
        "order_no", "order_date",
        "invoice_no", "invoice_date",
        "invoice_type",
        "sfa_order_no", "sfa_order_date",
        "file_extension", "separator_file",
        "first_row", "flag_bonus"
    ]

    if not all(col in df.columns for col in required_cols):
        st.error("❌ Kolom file tidak sesuai template.")
        return None

    # metadata
    df["createby"] = username
    df["createdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = df.astype(object)

    df = df.where(pd.notnull(df), None)

    res = insert_config(df)

    if not res:
        st.error("❌ Gagal terhubung ke server.")
        return None

    if res.status_code == 200:
        try:
            return res.json()
        except Exception:
            return {
                "message": f"Berhasil upload {len(df)} record."
            }
    else:
        st.error(f"❌ Gagal upload data: {res.text}")
        return None


# PAGE
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

    st.title("⬆️ Upload Config")

    # DOWNLOAD TEMPLATE
    st.subheader("📄 Download Template Config")
    template_file = generate_template()
    st.download_button(
        "Download Template XLSX",
        data=template_file,
        file_name="template_Config.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

  
    # UPLOAD
    
    if not st.session_state.upload_done:
        st.subheader("📤 Upload Data Config")
        uploaded_file = st.file_uploader(
            "Pilih file Excel (Template Config)",
            type=["xlsx"]
        )

        if uploaded_file and st.button("🚀 Upload Data"):
            with st.spinner("Memproses data..."):
                result_json = process_upload(uploaded_file, username)

            if result_json:
                st.session_state.upload_result = result_json
                st.session_state.upload_done = True
                st.rerun()


    # RESULT
    else:
        result = st.session_state.upload_result

        message = result.get("message", "")
        skipped_duplicate = result.get("skipped_duplicate", [])
        skipped_invalid = result.get("skipped_invalid", [])

        st.success("✅ Upload selesai")

        if message:
            st.info(message)

        rows = []

        for d in skipped_duplicate:
            rows.append({
                "Key": d,
                "Status": "Duplicate (Skipped)"
            })

        for i in skipped_invalid:
            rows.append({
                "Key": i,
                "Status": "Invalid Data (Skipped)"
            })

        if rows:
            df_display = pd.DataFrame(rows)
            st.warning("⚠️ Sebagian data tidak diproses")
            st.dataframe(df_display)
        else:
            st.success("🎉 Semua data berhasil dimasukkan ke database")

        st.markdown("---")
        if st.button("⬅️ Kembali ke Data Config"):
            st.cache_data.clear()
            st.session_state["refresh_config"] = True
            st.session_state.page = "config"
            st.session_state.upload_done = False
            st.session_state.upload_result = None
            st.rerun()


if __name__ == "__main__":
    app()
