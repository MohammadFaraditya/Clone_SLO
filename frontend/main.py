import streamlit as st
from utils.api.auth_api import login

st.set_page_config(page_title="SELLOUT", layout="wide")

#SESSION HANDLING 
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "main"
if "submenu" not in st.session_state:
    st.session_state.submenu = None
if "collapse_area" not in st.session_state:
    st.session_state.collapse_area = False
if "collapse_salesman" not in st.session_state:
    st.session_state.collapse_salesman = False
if "collapse_customer" not in st.session_state:
    st.session_state.collapse_customer = False

# SIDEBAR CSS FIX
st.markdown("""
<style>
    /* Hilangkan padding tombol sidebar */
    .stButton > button {
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        border-radius: 6px !important;
    }

    /* Hilangkan garis-garis separator */
    hr, [data-testid="stMarkdownContainer"] hr {
        display: none !important;
    }

    /* Kurangi jarak antar tombol */
    .sidebar-space {
        height: 6px;
    }
            
}

</style>
""", unsafe_allow_html=True)


#  LOGIN PAGE 
if not st.session_state.logged_in:
    st.markdown("<style>[data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)

    st.title("🔐 SELLOUT")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        res = login(username, password)
        if res.status_code == 200:
            data = res.json()
            st.session_state.logged_in = True
            st.session_state.user = data["user"]
            st.session_state.token = data["token"]
            st.success(f"Selamat datang, {data['user']['nama']}!")
            st.rerun()
        else:
            st.error(res.json().get("error", "Login gagal"))

#  MAIN PAGE 
else:

    user = st.session_state.user


    #   SIDEBAR
    with st.sidebar:

        # SIDEBAR STYLE
            st.markdown("""
            <style>
            .sidebar-section {
                background-color: #f0f2f6;
                padding: 6px 10px;
                border-radius: 8px;
                margin-bottom: 8px;
            }
            .menu-title {
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 10px;
            }
            .menu-item {
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                display: block;
            }
            .menu-item:hover {
                background-color: #e3e7ee;
            }
            .submenu-item {
                padding: 5px 25px;
                cursor: pointer;
                font-size: 14px;
                display: block;
                color: #333333;
            }
            .submenu-item:hover {
                background-color: #e3e7ee;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("<div class='menu-title'>📁 Menu</div>", unsafe_allow_html=True)

            # Dashboard
            if st.button("🏠 Dashboard Utama", use_container_width=True):
                st.session_state.page = "main"
                st.rerun()

            st.markdown("---")

            # AREA MENU
            if st.button("▶️ Area", key="area_menu", use_container_width=True):
                st.session_state.collapse_area = not st.session_state.collapse_area

            if st.session_state.get("collapse_area", False):
                if st.button("Area SPV", key="area1", use_container_width=True):
                    st.session_state.page = "area"; st.rerun()
                if st.button("Region", key="area2", use_container_width=True):
                    st.session_state.page = "region"; st.rerun()
                if st.button("Entity", key="area3", use_container_width=True):
                    st.session_state.page = "entity"; st.rerun()
                if st.button("Branch", key="area4", use_container_width=True):
                    st.session_state.page = "branch"; st.rerun()
                if st.button("Branch Dist", key="area5", use_container_width=True):
                    st.session_state.page = "branch_dist"; st.rerun()
                if st.button("Mapping Branch", key="area6", use_container_width=True):
                    st.session_state.page = "mapping_branch"; st.rerun()

            st.markdown("---")

            # SALESMAN MENU
            if st.button("▶️ Salesman", key="salesman_menu", use_container_width=True):
                st.session_state.collapse_salesman = not st.session_state.collapse_salesman

            if st.session_state.get("collapse_salesman", False):
                if st.button("Salesman Team", key="sales1", use_container_width=True):
                    st.session_state.page = "salesman_team"; st.rerun()

                if st.button("Salesman Master", key="sales2", use_container_width=True):
                    st.session_state.page = "salesman_master"; st.rerun()

                if st.button("Mapping Salesman", key="sales3", use_container_width=True):
                    st.session_state.page = "mapping_salesman"; st.rerun()

            st.markdown("---")

            # CUSTOMER MENU
            if st.button("▶️ Customer", key="customer_menu", use_container_width=True):
                st.session_state.collapse_customer = not st.session_state.collapse_customer

            if st.session_state.get("collapse_customer", False):
                if st.button("Customer PRC", key="cust1", use_container_width=True):
                    st.session_state.page = "customer_prc"; st.rerun()

                if st.button("Customer DIST", key="cust2", use_container_width=True):
                    st.session_state.page = "customer_dist"; st.rerun()

                if st.button("Mapping Customer", key="cust3", use_container_width=True):
                    st.session_state.page = "mapping_customer"; st.rerun()

            st.markdown("---")

            # USER CARD + LOGOUT
            st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem 0;">
                    <div style="font-size: 40px; color: #6c63ff;">👤</div>
                    <div style="font-size: 16px; font-weight: bold;">{user['nama']}</div>
                    <div style="color: gray; font-size: 14px;">{user['jabatan']}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()


    #  PAGE ROUTER
    if st.session_state.page == "main":
        st.title("📊 Dashboard Utama")


    #  AREA PAGES 
    elif st.session_state.page == "area":
        from pages.area.area_spv import area_page
        area_page.app()

    elif st.session_state.page == "upload_area":
        from pages.area.area_spv import upload_area_page
        upload_area_page.app()

    #  REGION 
    elif st.session_state.page == "region":
        from pages.area.region import region_page
        region_page.app()

    elif st.session_state.page == "upload_region":
        from pages.area.region import upload_region_page
        upload_region_page.app()

    # SALESMAN TEAM 
    elif st.session_state.page == "salesman_team":
        from pages.salesman.salesman_team import salesman_team_page
        salesman_team_page.app()

    elif st.session_state.page == "upload_salesman_team":
        from pages.salesman.salesman_team import upload_salesman_team_page
        upload_salesman_team_page.app()

    # ENTITY 
    elif st.session_state.page == "entity":
        from pages.area.entity import entity_page
        entity_page.app()

    elif st.session_state.page == "upload_entity":
        from pages.area.entity import upload_entity_page
        upload_entity_page.app()

    #  BRANCH 
    elif st.session_state.page == "branch":
        from pages.area.branch import branch_page
        branch_page.app()

    elif st.session_state.page == "upload_branch":
        from pages.area.branch import upload_branch_page
        upload_branch_page.app()

    #  BRANCH DIST 
    elif st.session_state.page == "branch_dist":
        from pages.area.branch_dist import branch_dist_page
        branch_dist_page.app()

    elif st.session_state.page == "upload_branch_dist":
        from pages.area.branch_dist import upload_branch_dist_page
        upload_branch_dist_page.app()

    #  MAPPING BRANCH 
    elif st.session_state.page == "mapping_branch":
        from pages.area.mapping_branch import mapping_branch_page
        mapping_branch_page.app()

    elif st.session_state.page == "upload_mapping_branch":
        from pages.area.mapping_branch import upload_mapping_branch_page
        upload_mapping_branch_page.app()

    #  SALESMAN MASTER
    elif st.session_state.page == "salesman_master":
        from pages.salesman.salesman_master import salesman_master_page
        salesman_master_page.app()

    elif st.session_state.page == "upload_salesman_master":
        from pages.salesman.salesman_master import upload_salesman_master_page
        upload_salesman_master_page.app()

    #  MAPPING SALESMAN
    elif st.session_state.page == "mapping_salesman":
        from pages.salesman.mapping_salesman import mapping_salesman_page
        mapping_salesman_page.app()

    elif st.session_state.page == "upload_mapping_salesman":
        from pages.salesman.mapping_salesman import upload_mapping_salesman_page
        upload_mapping_salesman_page.app()

    # CUSTOMER PRC
    elif st.session_state.page == "customer_prc":
        from pages.customer.customer_prc import customer_prc_page
        customer_prc_page.app()

    elif st.session_state.page == "upload_customer_prc":
        from pages.customer.customer_prc import upload_customer_prc
        upload_customer_prc.app()

    # CUSTOMER DIST
    elif st.session_state.page == "customer_dist":
        from pages.customer.customer_dist import customer_dist_page
        customer_dist_page.app()

    elif st.session_state.page == "upload_customer_dist":
        from pages.customer.customer_dist import upload_customer_dist
        upload_customer_dist.app()
    
    # MAPPING CUSTOMER
    elif st.session_state.page == "mapping_customer":
        from pages.customer.mapping_customer import mapping_customer_page
        mapping_customer_page.app()

    elif st.session_state.page == "upload_mapping_customer":
        from pages.customer.mapping_customer import upload_mapping_customer
        upload_mapping_customer.app()

