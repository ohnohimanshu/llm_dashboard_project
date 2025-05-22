import streamlit as st

st.set_page_config(
    page_title="TSLA Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/ohnohimanshu/llm_dashboard_project',
        'Report a bug': "https://github.com/ohnohimanshu/llm_dashboard_project/issues",
        'About': "# TSLA Stock Analysis Dashboard\n This is a dashboard for analyzing Tesla stock data."
    }
)

st.title("📈 TSLA Stock Analysis Dashboard")
st.write("Welcome to the TSLA Stock Analysis Dashboard. Please select a page from the sidebar.")