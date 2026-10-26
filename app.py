"""Student Growth Planner browser entry point."""
import os
import streamlit as st
from growth_planner.database import DATABASE_FILE
from growth_planner.service import AccessError, Planner
from growth_planner.ui import faculty_home, login_screen, password_screen, student_home
from growth_planner.theme import apply_theme, brand, sidebar_profile


def main():
    st.set_page_config(page_title="Student Growth Planner", page_icon="🎓", layout="wide")
    apply_theme()
    planner = Planner(os.environ.get("GROWTH_PLANNER_DB", str(DATABASE_FILE)))
    brand()
    dataset_notice = planner.dataset_notice()
    if dataset_notice:
        st.caption("PRACTICE DATA · " + dataset_notice)
    if "notice" in st.session_state:
        st.success(st.session_state.pop("notice"))
    token = st.session_state.get("token")
    if not token:
        login_screen(planner)
        return
    try:
        user = planner.current_user(token)
    except AccessError as error:
        st.session_state.pop("token", None)
        st.warning(str(error))
        login_screen(planner)
        return
    sidebar_profile(user)
    if st.sidebar.button("Sign out", width="stretch"):
        planner.logout(token)
        st.session_state.clear()
        st.rerun()
    if user["must_change_password"]:
        st.info("Please change the initial password supplied by faculty.")
        password_screen(planner, token)
        return
    try:
        if user["role"] == "faculty":
            faculty_home(planner, token)
        else:
            student_home(planner, token)
    except ValueError as error:
        st.error(str(error))


if __name__ == "__main__":
    main()
