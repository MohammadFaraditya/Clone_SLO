import streamlit as st
from utils.api.auth_api import login

st.set_page_config(page_title="SELLOUT", layout="wide")

# ====== SESSION SETUP ======
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "main"

# ====== LOGIN PAGE ======
if not st.session_state.logged_in:
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    st.title("🔐 SELLOUT")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", width="stretch"):
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

# ====== DASHBOARD ======
else:
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    user = st.session_state.user

    # ========== SIDEBAR ==========
    with st.sidebar:
        if st.session_state.page != "main":
            if st.button("🏠 Dashboard Utama", width="stretch"):
                st.session_state.page = "main"
                st.rerun()
            if st.button("📍 Area", width="stretch"):
                st.session_state.page = "area"
                st.rerun()
            if st.button("📍 Region", width="stretch"):
                st.session_state.page = "region"
                st.rerun()
            if st.button("👥 Salesman Team", width="stretch"):
                st.session_state.page = "salesman_team"
                st.rerun()
            if st.button("📍 Entity", width="stretch"):
                st.session_state.page = "entity"
                st.rerun()
            if st.button("🏚️ Branch", width="stretch"):
                st.session_state.page = "branch"
                st.rerun()
            if st.button("🏚️ Branch Dist", width="stretch"):
                st.session_state.page = "branch_dist"
                st.rerun()
            if st.button("🏚️ Mapping Branch", width="stretch"):
                st.session_state.page = "mapping_branch"
                st.rerun()
            st.markdown("---")

        st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem 0;">
                <div style="font-size: 40px; color: #6c63ff;">👤</div>
                <div style="font-size: 16px; font-weight: bold;">{user['nama']}</div>
                <div style="color: gray; font-size: 14px;">{user['jabatan']}</div>
            </div>
            <hr style="margin: 0.8rem 0;">
        """, unsafe_allow_html=True)

        if st.button("Logout", key="logout_sidebar", width="stretch"):
            st.session_state.clear()
            st.rerun()

    if st.session_state.page == "main":
        st.title("📊 Dashboard Utama")
        st.markdown("---")

        # Daftar menu
        menu_items = [
            {"title": "📍 Area", "desc": "Area", "page": "area"},
            {"title": "📍 Region", "desc": "Region", "page": "region"},
            {"title": "👥 Salesman Team", "desc": "Salesman Team", "page": "salesman_team"},
            {"title": "📍 Entity", "desc": "", "page": "entity"},
            {"title": "🏚️ Branch", "desc": "", "page": "branch"},
            {"title": "🏚️ Branch Dist", "desc": "", "page": "branch_dist"},
            {"title": "🏚️ Mapping Branch", "desc": "", "page": "mapping_branch"}
        ]

        cols = st.columns(3)
        for i, menu in enumerate(menu_items):
            with cols[i % 3]:
                st.markdown(f"""
                    <div style="
                        background-color: #f8f9fa;
                        border-radius: 15px;
                        padding: 1.5rem;
                        margin-bottom: 1rem;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        text-align: center;
                        transition: transform 0.2s ease-in-out;
                    " onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                        <div style="font-size: 40px;">{menu['title'].split()[0]}</div>
                        <div style="font-size: 18px; font-weight: bold;">{' '.join(menu['title'].split()[1:])}</div>
                        <p style="color: gray; font-size: 14px;">{menu['desc']}</p>
                    </div>
                """, unsafe_allow_html=True)

                if st.button(f" {menu['title']}", key=f"btn_{menu['page']}", width="stretch"):
                    st.session_state.page = menu["page"]
                    st.rerun()

    # start area page
    elif st.session_state.page == "area":
        from pages.area import area_page
        area_page.app()

    elif st.session_state.page == "upload_area":
        from pages.area import upload_area_page
        upload_area_page.app()
    # end area page

    # start region page   
    elif st.session_state.page == "region":
        from pages.region import region_page
        region_page.app()

    elif st.session_state.page == "upload_region":
        from pages.region import upload_region_page
        upload_region_page.app()
    #end region page

    #start salesman team page
    elif st.session_state.page == "salesman_team":
        from pages.salesman_team import salesman_team_page
        salesman_team_page.app()

    elif st.session_state.page == "upload_salesman_team":
        from pages.salesman_team import upload_salesman_team_page
        upload_salesman_team_page.app()        
    #end salesman team page

    #start entity page
    elif st.session_state.page == "entity":
        from pages.entity import entity_page
        entity_page.app()

    elif st.session_state.page == "upload_entity":
        from pages.entity import upload_entity_page
        upload_entity_page.app()
    #end entity page

    #start branch page
    elif st.session_state.page == "branch":
        from pages.branch import branch_page
        branch_page.app()

    elif st.session_state.page == "upload_branch":
        from pages.branch import upload_branch_page
        upload_branch_page.app()
    #end branch page

    #start branch_dist page
    elif st.session_state.page == "branch_dist":
        from pages.branch_dist import branch_dist_page
        branch_dist_page.app()

    elif st.session_state.page == "upload_branch_dist":
        from pages.branch_dist import upload_branch_dist_page
        upload_branch_dist_page.app()
    #end branch_dist page

     #start mapping_branch page
    elif st.session_state.page == "mapping_branch":
        from pages.mapping_branch import mapping_branch_page
        mapping_branch_page.app()

    elif st.session_state.page == "upload_mapping_branch":
        from pages.mapping_branch import upload_mapping_branch_page
        upload_mapping_branch_page.app()
    #end mapping branch page
