import streamlit as st
import plotly.graph_objects as go
from utils.data_processing import load_data

# Must be the first Streamlit command
st.set_page_config(
    page_title="TSLA Candlestick Chart", 
    layout="wide",
    page_icon="📊"
)

try:
    # Load data
    df = load_data("data/tsla_data.csv")
    
    if df is not None and not df.empty:
        # Create candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close']
        )])
        
        # Update layout
        fig.update_layout(
            title='TSLA Stock Price',
            yaxis_title='Stock Price (USD)',
            xaxis_title='Date',
            template='plotly_white'
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("No data available")
        
except Exception as e:
    st.error(f"Error: {str(e)}")
    st.stop()