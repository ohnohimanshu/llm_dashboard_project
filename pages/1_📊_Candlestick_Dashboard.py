import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from utils.data_processing import load_data
from utils.tradingview_component import tradingview_chart
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure page
st.set_page_config(
    page_title="TSLA Candlestick Chart", 
    layout="wide",
    page_icon="📊"
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
    .chart-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def main():
    try:
        # Main header
        st.markdown('<h1 class="main-header">📊 TSLA Stock Candlestick Chart</h1>', unsafe_allow_html=True)
        
        # Add debug mode toggle in sidebar
        debug_mode = st.sidebar.checkbox("Enable Debug Mode", value=False)
        
        # Load data from local CSV only
        with st.spinner("Loading data..."):
            df = load_data()
            
            if debug_mode:
                st.sidebar.write("Debug Information:")
                st.sidebar.write(f"DataFrame Shape: {df.shape if df is not None else 'None'}")
                if df is not None:
                    st.sidebar.write("Columns:", df.columns.tolist())
                    st.sidebar.write("Data Types:", df.dtypes)
                    st.sidebar.write("Sample Data:", df.head())
        
        if df is not None and not df.empty:
            # Create columns for chart controls
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown("### Chart Settings")
                
                # Chart height control
                chart_height = st.slider(
                    "Chart Height",
                    min_value=300,
                    max_value=800,
                    value=500,
                    step=50
                )
                
                # Time range selection
                if 'Date' in df.columns:
                    date_range = pd.to_datetime(df['Date'])
                    min_date = date_range.min()
                    max_date = date_range.max()
                    
                    selected_range = st.date_input(
                        "Select Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
                    
                    if len(selected_range) == 2:
                        start_date, end_date = selected_range
                        df = df[
                            (pd.to_datetime(df['Date']) >= pd.to_datetime(start_date)) &
                            (pd.to_datetime(df['Date']) <= pd.to_datetime(end_date))
                        ]
                
                # Show data table option
                show_data = st.checkbox("Show Data Table", value=True)
                
                # Show legend
                st.markdown("### Chart Legend")
                st.markdown("""
                <span style='color:#26a69a;font-size:1.3em;'>&#8593;</span> Green up arrow (below candle): LONG position  
                <span style='color:#ef5350;font-size:1.3em;'>&#8595;</span> Red down arrow (above candle): SHORT position  
                <span style='color:#FFD600;font-size:1.3em;'>●</span> Yellow circle: No position  
                🟩 Green band: Support levels  
                🟥 Red band: Resistance levels 
                """, unsafe_allow_html=True)
            
            with col1:
                # Display TradingView chart
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                tradingview_chart(
                    data=df,
                    height=chart_height,
                    key="tsla_chart"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Show data table if requested
            if show_data:
                st.markdown("### TSLA Stock Data")
                st.dataframe(
                    df.sort_values('Date', ascending=False).reset_index(drop=True),
                    use_container_width=True
                )
            
        else:
            st.error("No data available. Please check the data source and try again.")
            if debug_mode:
                st.write("Debug: DataFrame is None or empty")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        if debug_mode:
            import traceback
            st.write("Full error traceback:")
            st.code(traceback.format_exc())
        st.stop()

if __name__ == "__main__":
    main()
