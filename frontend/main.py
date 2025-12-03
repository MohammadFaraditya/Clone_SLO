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

        # --- Dashboard ---
        if st.button("🏠 Dashboard Utama", use_container_width=True):
            st.session_state.page = "main"
            st.session_state.submenu = None
            st.rerun()

        st.markdown('<div class="sidebar-space"></div>', unsafe_allow_html=True)

        #     COLLAPSIBLE: AREA
        if st.button("Area", key="btn_area", use_container_width=True):
            st.session_state.collapse_area = not st.session_state.collapse_area

        if st.session_state.collapse_area:
            st.write("")
            if st.button("Area SPV", use_container_width=True):
                st.session_state.page = "area"; st.rerun()

            if st.button("Region", use_container_width=True):
                st.session_state.page = "region"; st.rerun()

            if st.button("Entity", use_container_width=True):
                st.session_state.page = "entity"; st.rerun()

            if st.button("Branch", use_container_width=True):
                st.session_state.page = "branch"; st.rerun()

            if st.button("Branch Dist", use_container_width=True):
                st.session_state.page = "branch_dist"; st.rerun()

            if st.button("Mapping Branch", use_container_width=True):
                st.session_state.page = "mapping_branch"; st.rerun()

        st.markdown('<div class="sidebar-space"></div>', unsafe_allow_html=True)

        #   COLLAPSIBLE: SALESMAN
        if st.button("Salesman", key="btn_salesman", use_container_width=True):
            st.session_state.collapse_salesman = not st.session_state.collapse_salesman

        if st.session_state.collapse_salesman:
            st.write("")
            if st.button("Salesman Team", use_container_width=True):
                st.session_state.page = "salesman_team"; st.rerun()
            
            if st.button("Salesman Master", use_container_width=True):
                st.session_state.page = "salesman_master"; st.rerun()

        st.markdown('<div class="sidebar-space"></div>', unsafe_allow_html=True)

        #  USER CARD
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
