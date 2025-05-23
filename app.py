import streamlit as st
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Configure page
st.set_page_config(
    page_title="TSLA Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #262730;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    .stApp {
        background-color: #f9f9f9;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    try:
        # Main header
        st.markdown('<h1 class="main-header">📈 TSLA Stock Analysis Dashboard</h1>', unsafe_allow_html=True)

        # Welcome message
        st.markdown("""
        <div class="info-box">
            <h2 class="sub-header">Welcome to the TSLA Stock Analysis Dashboard</h2>
            <p>This dashboard provides comprehensive analysis of Tesla (TSLA) stock data, including:</p>
            <ul>
                <li>Interactive candlestick charts with technical indicators</li>
                <li>Historical price analysis</li>
                <li>AI-powered market insights</li>
                <li>Support and resistance levels</li>
            </ul>
            <p>Please select a page from the sidebar to begin your analysis.</p>
        </div>
        """, unsafe_allow_html=True)

        # Sidebar information
        with st.sidebar:
            st.markdown("### Navigation")
            st.markdown("""
            - 📈 **Candlestick Dashboard**: View interactive price charts
            - 🤖 **AI Chatbot**: Get AI-powered market insights
            """)

            st.markdown("### About")
            st.markdown("""
            This dashboard is designed for educational and analytical purposes.
            Data is sourced from reliable financial APIs and is updated regularly.
            """)

            st.markdown("### Version")
            st.markdown("v1.0.0")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.markdown("""
        <div class="error-box">
            <p>Please try refreshing the page. If the error persists, contact support.</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
