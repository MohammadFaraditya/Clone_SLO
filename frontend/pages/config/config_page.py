import streamlit as st
from utils.api.config.config_api import (
    get_data_config,
    update_config,
    delete_config
)

PAGE_CHUNK = 1500


# HELPER
def to_int_or_none(val):
    if val in ("", None):
        return None
    try:
        return int(val)
    except:
        return None


# CSS BORDER TABLE
st.markdown("""
<style>
.table-row {
    border-bottom: 1px solid #e0e0e0;
    padding: 6px 0;
}
.table-header {
    font-weight: 600;
    border-bottom: 2px solid #b0b0b0;
    padding-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)


# FETCH + CACHE
@st.cache_data(ttl=120)
def fetch_config_once(token):
    res = get_data_config(token, offset=0, limit=PAGE_CHUNK)
    if not res or res.status_code != 200:
        return []
    return res.json().get("data", [])


def refresh_config():
    fetch_config_once.clear()
    st.session_state["refresh_config"] = True


# PAGE
def app():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Anda harus login terlebih dahulu.")
        st.session_state.page = "main"
        st.rerun()
        return

    st.title("⚙️ Data Config")

    token = st.session_state.token
    updateby = st.session_state.user["nama"]

    # Upload tetap ada
    if st.button("⬆️ Upload Config"):
        st.session_state.page = "upload_config"
        st.rerun()
        return

    # Load data
    if "config_data" not in st.session_state or st.session_state.get("refresh_config", True):
        with st.spinner("Memuat data config..."):
            st.session_state["config_data"] = fetch_config_once(token)
            st.session_state["refresh_config"] = False

    data = st.session_state.get("config_data", [])
    if not data:
        st.info("Tidak ada data config.")
        return

    st.markdown(f"**Total Data Config: {len(data)}**")

    # TABLE HEADER
    header = st.columns([1, 2, 5, 1, 1])
    for col, title in zip(header, ["No", "Branch", "Nama Branch", "Detail", "Delete"]):
        col.markdown(f"<div class='table-header'>{title}</div>", unsafe_allow_html=True)

    # TABLE ROW
    for i, row in enumerate(data, start=1):
        cols = st.columns([1, 2, 5, 1, 1])

        cols[0].markdown(f"<div class='table-row'>{i}</div>", unsafe_allow_html=True)
        cols[1].markdown(f"<div class='table-row'>{row['branch']}</div>", unsafe_allow_html=True)
        cols[2].markdown(f"<div class='table-row'>{row.get('nama_branch','-')}</div>", unsafe_allow_html=True)

        if cols[3].button("🔍", key=f"detail_{row['branch']}"):
            st.session_state["selected_config"] = row

        if cols[4].button("🗑️", key=f"delete_{row['branch']}"):
            res = delete_config(token, [row["branch"]])
            if res and res.status_code == 200:
                st.success(f"{row['branch']} berhasil dihapus")
                refresh_config()
                st.rerun()
            else:
                st.error("Gagal menghapus data")

    st.markdown("---")

    # DETAIL FORM
    selected = st.session_state.get("selected_config")
    if selected:
        st.subheader("🔍 Detail & Edit Config")

        with st.form("edit_config_form"):
            kodebranch = st.text_input("Kode Branch", value=str(selected.get("kodebranch") or ""))
            id_salesman = st.text_input("ID Salesman", value=str(selected.get("id_salesman") or ""))
            id_customer = st.text_input("ID Customer", value=str(selected.get("id_customer") or ""))
            id_product = st.text_input("ID Product", value=str(selected.get("id_product") or ""))

            qty1 = st.text_input("Qty 1", value=str(selected.get("qty1") or ""))
            qty2 = st.text_input("Qty 2", value=str(selected.get("qty2") or ""))
            qty3 = st.text_input("Qty 3", value=str(selected.get("qty3") or ""))
            price = st.text_input("Price", value=str(selected.get("price") or ""))
            grossamount = st.text_input("Gross Amount", value=str(selected.get("grossamount") or ""))

            discount1 = st.text_input("Discount 1", value=str(selected.get("discount1") or ""))
            discount2 = st.text_input("Discount 2", value=str(selected.get("discount2") or ""))
            discount3 = st.text_input("Discount 3", value=str(selected.get("discount3") or ""))
            discount4 = st.text_input("Discount 4", value=str(selected.get("discount4") or ""))
            discount5 = st.text_input("Discount 5", value=str(selected.get("discount5") or ""))
            discount6 = st.text_input("Discount 6", value=str(selected.get("discount6") or ""))
            discount7 = st.text_input("Discount 7", value=str(selected.get("discount7") or ""))
            discount8 = st.text_input("Discount 8", value=str(selected.get("discount8") or ""))

            total_discount = st.text_input("Total Discount", value=str(selected.get("total_discount") or ""))
            dpp = st.text_input("DPP", value=str(selected.get("dpp") or ""))
            tax = st.text_input("Tax", value=str(selected.get("tax") or ""))
            nett = st.text_input("Nett", value=str(selected.get("nett") or ""))

            order_no = st.text_input("Order No", value=str(selected.get("order_no") or ""))
            order_date = st.text_input("Order Date", value=str(selected.get("order_date") or ""))

            invoice_no = st.text_input("Invoice No", value=str(selected.get("invoice_no") or ""))
            invoice_date = st.text_input("Invoice Date", value=str(selected.get("invoice_date") or ""))
            invoice_type = st.text_input("Invoice Type", value=str(selected.get("invoice_type") or ""))

            sfa_order_no = st.text_input("SFA Order No", value=str(selected.get("sfa_order_no") or ""))
            sfa_order_date = st.text_input("SFA Order Date", value=str(selected.get("sfa_order_date") or ""))

            file_extension = st.text_input("File Extension", selected["file_extension"])
            separator_file = st.text_input("Separator File", selected.get("separator_file") or ",")
            first_row = st.text_input("First Row", value=str(selected.get("first_row") or ""))
            flag_bonus = st.text_input("Flag Bonus (0 / 1)", value=str(selected.get("flag_bonus") or "0"))

            submit = st.form_submit_button("💾 Simpan Perubahan")

        if submit:
            payload = {
                "kodebranch": kodebranch,
                "id_salesman": id_salesman,
                "id_customer": id_customer,
                "id_product": id_product,

                "qty1": to_int_or_none(qty1),
                "qty2": to_int_or_none(qty2),
                "qty3": to_int_or_none(qty3),
                "price": to_int_or_none(price),
                "grossamount": to_int_or_none(grossamount),

                "discount1": to_int_or_none(discount1),
                "discount2": to_int_or_none(discount2),
                "discount3": to_int_or_none(discount3),
                "discount4": to_int_or_none(discount4),
                "discount5": to_int_or_none(discount5),
                "discount6": to_int_or_none(discount6),
                "discount7": to_int_or_none(discount7),
                "discount8": to_int_or_none(discount8),

                "total_discount": to_int_or_none(total_discount),
                "dpp": to_int_or_none(dpp),
                "tax": to_int_or_none(tax),
                "nett": to_int_or_none(nett),

                "order_no": to_int_or_none(order_no),
                "order_date": to_int_or_none(order_date),
                "invoice_no": to_int_or_none(invoice_no),
                "invoice_date": to_int_or_none(invoice_date),
                "invoice_type": to_int_or_none(invoice_type),

                "sfa_order_no": to_int_or_none(sfa_order_no),
                "sfa_order_date": to_int_or_none(sfa_order_date),

                "file_extension": file_extension,
                "separator_file": separator_file,
                "first_row": first_row,
                "flag_bonus": flag_bonus,
                "updateby": updateby
            }

            res = update_config(token, selected["branch"], **payload)
            if res and res.status_code == 200:
                st.success("✅ Data berhasil diupdate")
                st.session_state.pop("selected_config")
                refresh_config()
                st.rerun()
            else:
                st.error("❌ Gagal update data")

        if st.button("❌ Tutup Detail"):
            st.session_state.pop("selected_config")
            st.rerun()

    if st.button("🔄 Segarkan Data"):
        refresh_config()
        st.rerun()


if __name__ == "__main__":
    app()
