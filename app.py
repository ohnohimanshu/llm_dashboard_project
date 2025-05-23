import streamlit as st
import subprocess
import sys

# 🔧 Dynamically install google-generativeai if not already present
try:
    import google.generativeai
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai==0.3.2"])
    import google.generativeai

# ✅ Must be the first Streamlit command
st.set_page_config(
    page_title="TSLA Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 TSLA Stock Analysis Dashboard")
st.write("Welcome to the TSLA Stock Analysis Dashboard. Please select a page from the sidebar.")
