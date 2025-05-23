import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="TSLA Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 TSLA Stock Analysis Dashboard")
st.write("Welcome to the TSLA Stock Analysis Dashboard. Please select a page from the sidebar.")
