import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
import time
import json

# Rate limiting configuration
RATE_LIMITS = {
    "requests_per_minute": 3,
    "requests_per_day": 50,
    "retry_delay": 60,
    "cooldown_period": 300  # 5 minutes in seconds
}

def create_data_summary(df):
    """Create a concise summary of the dataset to reduce token usage"""
    try:
        if df is None or df.empty:
            return "No data available"
        # Get column info
        columns = df.columns.tolist()
        st.info(f"📋 Data columns found: {', '.join(columns)}")
        # Flexible column detection
        date_col = None
        price_cols = []
        volume_col = None
        for col in columns:
            col_lower = col.lower()
            if 'date' in col_lower or 'time' in col_lower:
                date_col = col
            elif any(term in col_lower for term in ['price', 'close', 'open', 'high', 'low']):
                price_cols.append(col)
            elif 'volume' in col_lower:
                volume_col = col
        # Build summary
        summary = {
            "total_records": len(df),
            "columns": columns
        }
        # Date range
        if date_col and date_col in df.columns:
            try:
                summary["date_range"] = {
                    "start": str(df[date_col].min()),
                    "end": str(df[date_col].max())
                }
            except:
                summary["date_range"] = {"start": "Unknown", "end": "Unknown"}
        # Price statistics
        if price_cols:
            price_stats = {}
            for col in price_cols:
                try:
                    price_stats[col] = {
                        "latest": float(df[col].iloc[-1]) if len(df) > 0 else 0,
                        "max": float(df[col].max()),
                        "min": float(df[col].min()),
                        "mean": float(df[col].mean())
                    }
                except:
                    continue
            summary["price_stats"] = price_stats
        # Volume statistics
        if volume_col and volume_col in df.columns:
            try:
                summary["volume_stats"] = {
                    "avg_volume": int(df[volume_col].mean()),
                    "max_volume": int(df[volume_col].max()),
                    "min_volume": int(df[volume_col].min())
                }
            except:
                pass
        # Recent trend (if we have numeric data)
        if price_cols and len(df) >= 5:
            try:
                main_price_col = price_cols[0]  # Use first price column
                recent_data = df.tail(5)
                price_change = float(recent_data[main_price_col].iloc[-1] - recent_data[main_price_col].iloc[0])
                summary["recent_trend"] = {
                    "5day_change": price_change,
                    "trend_direction": "up" if price_change > 0 else "down" if price_change < 0 else "flat"
                }
            except:
                pass
        return summary
    except Exception as e:
        st.error(f"Error creating data summary: {str(e)}")
        return {"error": "Error processing data", "columns": df.columns.tolist() if df is not None else []}

# Load and process data from local CSV
try:
    with st.spinner("📊 Loading data from local CSV file..."):
        df = pd.read_csv('data/tsla_data.csv')
    if df is None or df.empty:
        st.error("❌ No data could be loaded from the CSV file.")
        st.info("Please check if the CSV file exists and contains data.")
        st.stop()
    # Display data info
    st.info(f"📊 Loaded {len(df)} rows and {len(df.columns)} columns")
    # Show first few rows to understand the data structure
    with st.expander("👀 Preview Data (First 5 rows)"):
        st.dataframe(df.head())
    # Create data summary for AI
    if 'data_summary' not in st.session_state or st.session_state.data_summary is None:
        st.session_state.data_summary = create_data_summary(df)
    # Dynamic data overview based on available columns
    col1, col2, col3 = st.columns(3)
    # Detect numeric columns for display
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    with col1:
        if numeric_cols:
            first_numeric = numeric_cols[0]
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>📊 {first_numeric}</h4>
                    <p class="info-text">Range: {df[first_numeric].min():.2f} - {df[first_numeric].max():.2f}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>📊 Total Records</h4>
                    <p class="info-text">{len(df)} rows</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    with col2:
        if len(numeric_cols) > 1:
            second_numeric = numeric_cols[1]
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>📈 {second_numeric}</h4>
                    <p class="info-text">Avg: {df[second_numeric].mean():.2f}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>📅 Columns</h4>
                    <p class="info-text">{len(df.columns)} fields</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    with col3:
        # Show date range if date column exists
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        if date_cols:
            date_col = date_cols[0]
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>📅 Date Range</h4>
                    <p class="info-text">{len(df)} records</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>🔢 Data Points</h4>
                    <p class="info-text">{len(df)} total</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    # API Configuration
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ GEMINI_API_KEY not found in Streamlit secrets.")
            st.info("Please add your Gemini API key to the secrets configuration.")
            st.stop()
        genai.configure(api_key=api_key)
        # Test API connection
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
    except Exception as e:
        st.error(f"❌ Error configuring Gemini API: {str(e)}")
        st.info("Please check your API key and internet connection.")
        st.stop()
    # Question input
    st.markdown("### 💬 Ask About Your Data")
    st.markdown(
        """
        <div class="question-box">
            Ask me anything about the data from your CSV file. Examples:
            • What are the key statistics in the data?
            • How do the values compare across records?
            • What trends can you identify?
            • Analyze patterns in the data
        </div>
        """,
        unsafe_allow_html=True
    )
    question = st.text_input(
        "Your Question:",
        placeholder="Type your question about the data...",
        key="question_input"
    )
    # Process question
    if question:
        try:
            summary = st.session_state.data_summary
            prompt_parts = [
                "You are a data analysis assistant. Answer the user's question based on this data summary:",
                "",
                "Data Summary:",
                json.dumps(summary, indent=2),
                "",
                f"User Question: {question}",
                "",
                "Provide a concise, data-driven answer in 2-3 sentences. Focus on specific numbers and patterns from the data."
            ]
            prompt = "\n".join(prompt_parts)
            with st.spinner("🤖 Analyzing your question..."):
                response = model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                st.success("🤖 **AI Response:**")
                st.markdown(response.text)
                # Optionally, add to chat history
                if 'chat_history' not in st.session_state:
                    st.session_state.chat_history = []
                st.session_state.chat_history.append({
                    "question": question,
                    "answer": response.text,
                    "timestamp": datetime.now()
                })
            else:
                st.error("❌ No response received from AI. Please try rephrasing your question.")
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg:
                st.error("❌ API rate limit exceeded. Please wait a minute and try again, or check your Gemini API quota and billing.")
                st.info("See: https://ai.google.dev/gemini-api/docs/rate-limits")
            else:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Try asking a more specific question about the stock data.")
except Exception as e:
    st.error(f"❌ An error occurred while loading the data: {str(e)}")
    st.info("Please check that the CSV file exists and is accessible.")
# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666;'>
        <p>🤖 Powered by Google Gemini Pro | Built with Streamlit</p>
        <p style='font-size: 0.8rem'>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    """,
    unsafe_allow_html=True
)