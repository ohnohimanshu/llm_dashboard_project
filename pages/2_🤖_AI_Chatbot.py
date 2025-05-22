import streamlit as st
import pandas as pd
import google.generativeai as genai
from utils.data_processing import load_data
from datetime import datetime, timedelta
import socket
import time

# Rate limiting configuration
RATE_LIMITS = {
    "requests_per_minute": 3,
    "requests_per_day": 50,
    "retry_delay": 60,
    "cooldown_period": 300  # 5 minutes in seconds
}

def check_network_connectivity():
    """Check if the application can connect to Google's API"""
    try:
        # Try to connect to Google's DNS
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True, "Connection successful"
    except OSError as e:
        return False, f"Connection failed: {str(e)}"

# Must be the first Streamlit command
st.set_page_config(
    page_title="TSLA AI Analysis Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">🤖 TSLA Stock Analysis Assistant</h1>', unsafe_allow_html=True)

# Sidebar enhancements
with st.sidebar:
    st.markdown("### 📊 System Status")
    
    if 'rate_limiter' in st.session_state:
        status = st.session_state.rate_limiter.get_rate_limit_status()
        
        # Calculate usage percentages
        minute_usage = status["requests_this_minute"] / status["minute_limit"]
        daily_usage = status["requests_today"] / status["daily_limit"]
        
        # API Status indicator with better styling
        st.markdown(
            f"""
            <div style='padding: 10px; border-radius: 5px; margin-bottom: 10px; 
                background-color: {"#FFA726" if status["minute_reset_in"] > 0 else "#4CAF50" if not status["in_cooldown"] else "#F44336"}'>
                <strong>API Status:</strong> {
                    "🔴 Cooling Down" if status["in_cooldown"] else
                    "🟡 Rate Limited" if status["minute_reset_in"] > 0 else
                    "🟢 Ready"
                }
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Usage metrics with visual indicators
        st.markdown("#### Usage Metrics")
        cols = st.columns(2)
        
        # Minute usage
        with cols[0]:
            st.metric(
                "Per Minute",
                f"{status['requests_this_minute']}/{status['minute_limit']}",
                delta=f"{status['minute_limit'] - status['requests_this_minute']} remaining",
                delta_color="inverse"
            )
            
        # Daily usage
        with cols[1]:
            st.metric(
                "Per Day",
                f"{status['requests_today']}/{status['daily_limit']}",
                delta=f"{status['daily_limit'] - status['requests_today']} remaining",
                delta_color="inverse"
            )
        
        # Progress bars with dynamic colors
        st.markdown("#### Request Limits")
        
        # Minute progress
        st.markdown(f"**Per Minute** ({status['requests_this_minute']}/{status['minute_limit']})")
        minute_color = "#00f2c3" if minute_usage < 0.7 else "#ffa726" if minute_usage < 0.9 else "#f44336"
        st.progress(minute_usage, text="")
        
        # Daily progress
        st.markdown(f"**Per Day** ({status['requests_today']}/{status['daily_limit']})")
        daily_color = "#00f2c3" if daily_usage < 0.7 else "#ffa726" if daily_usage < 0.9 else "#f44336"
        st.progress(daily_usage, text="")
        
        # Reset countdown if needed
        if status["minute_reset_in"] > 0:
            st.info(f"⏱️ Rate limit resets in: {int(status['minute_reset_in'])} seconds")

# Rate limiter class definition
class RateLimiter:
    def __init__(self, config):
        self.minute_limit = config.get("requests_per_minute", 3)
        self.daily_limit = config.get("requests_per_day", 50)
        self.retry_delay = config.get("retry_delay", 60)
        self.cooldown_period = config.get("cooldown_period", 300)
        self.token_limit = config.get("token_limit", 4000)
        self.requests_this_minute = 0
        self.requests_today = 0
        self.last_minute = datetime.now()
        self.last_day = datetime.now().date()
        self.in_cooldown = False
        self.cooldown_start = None
        self.consecutive_network_errors = 0
        self.consecutive_rate_limit_errors = 0

    def can_make_request(self):
        now = datetime.now()
        if self.in_cooldown:
            if (now - self.cooldown_start).total_seconds() > self.cooldown_period:
                self.in_cooldown = False
                self.requests_this_minute = 0
                self.requests_today = 0
            else:
                return False
        if now.date() != self.last_day:
            self.requests_today = 0
            self.last_day = now.date()
        if (now - self.last_minute).total_seconds() > 60:
            self.requests_this_minute = 0
            self.last_minute = now
        if self.requests_this_minute < self.minute_limit and self.requests_today < self.daily_limit:
            return True
        else:
            if self.requests_this_minute >= self.minute_limit or self.requests_today >= self.daily_limit:
                self.in_cooldown = True
                self.cooldown_start = now
            return False

    def record_request(self):
        now = datetime.now()
        if now.date() != self.last_day:
            self.requests_today = 0
            self.last_day = now.date()
        if (now - self.last_minute).total_seconds() > 60:
            self.requests_this_minute = 0
            self.last_minute = now
        self.requests_this_minute += 1
        self.requests_today += 1

    def get_wait_time(self):
        now = datetime.now()
        if self.in_cooldown:
            return max(0, self.cooldown_period - (now - self.cooldown_start).total_seconds())
        if self.requests_this_minute >= self.minute_limit:
            return max(0, 60 - (now - self.last_minute).total_seconds())
        if self.requests_today >= self.daily_limit:
            return max(0, self.cooldown_period - (now - self.cooldown_start).total_seconds())
        return 0

    def get_rate_limit_status(self):
        now = datetime.now()
        minute_reset_in = max(0, 60 - (now - self.last_minute).total_seconds())
        return {
            "minute_limit": self.minute_limit,
            "daily_limit": self.daily_limit,
            "requests_this_minute": self.requests_this_minute,
            "requests_today": self.requests_today,
            "minute_reset_in": minute_reset_in,
            "in_cooldown": self.in_cooldown
        }

    def record_error(self, error_type="network"):
        if error_type == "network":
            self.consecutive_network_errors += 1
        elif error_type == "rate_limit":
            self.consecutive_rate_limit_errors += 1

    def reset_network_errors(self):
        self.consecutive_network_errors = 0

    def reset_rate_limit_errors(self):
        self.consecutive_rate_limit_errors = 0

    def get_network_backoff_time(self, attempt, error_type=None):
        # Exponential backoff: 2, 4, 8, ... seconds, max 60
        return min(60, 2 ** (attempt + 1))

# Initialize session state variables
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = RateLimiter(RATE_LIMITS)
if 'data_summary' not in st.session_state:
    st.session_state.data_summary = None

# Main content area

try:
    df = load_data("data/tsla_data.csv")
    if df is not None and not df.empty:
        # Display network status
        if not check_network_connectivity():
            st.error("⚠️ Network Error: Please check your internet connection")
            st.stop()
            
        # Data overview in cards
        st.markdown("### 📈 Market Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>Price Range</h4>
                    <p class="info-text">💲{df['Low'].min():.2f} - {df['High'].max():.2f}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>Average Volume</h4>
                    <p class="info-text">🔄 {int(df['Volume'].mean()):,}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown(
                f"""
                <div class="stat-card">
                    <h4>Date Range</h4>
                    <p class="info-text">📅 {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )

        # Question input with better styling
        st.markdown("### 💬 Ask Your Question")
        st.markdown(
            """
            <div class="question-box">
            Ask me anything about the TSLA stock data. For example:
            - What's the highest price in the dataset?
            - How has the volume changed over time?
            - What's the price trend analysis?
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        question = st.text_input(
            "",
            placeholder="Type your question here...",
            key="question_input"
        )

        # Add a clear button
        if question:
            if st.button("🗑️ Clear Question"):
                st.session_state.question_input = ""
                st.experimental_rerun()

        # API key configuration
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                st.error("Please set the GEMINI_API_KEY in your Streamlit secrets")
                st.stop()
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"Error configuring API: {e}")
            st.stop()

        # Update Gemini model configuration with specific model versions
        GEMINI_MODELS = {
            "chat": "models/gemini-1.5-pro-latest",  # Using the latest stable 1.5 Pro model
            "vision": "models/gemini-pro-vision"      # Keeping vision model as backup
        }

        @st.cache_resource
        def get_ai_response_model():
            """Initialize and return the AI response model."""
            try:
                model = genai.GenerativeModel(GEMINI_MODELS["chat"])
                return model
            except Exception as e:
                st.error(f"Error initializing model: {e}")
                return None

        model = get_ai_response_model()

        # Update the get_ai_response function
        def get_ai_response(model, prompt, max_retries=3):
            """Get AI response with optimized token handling"""
            for attempt in range(max_retries):
                if st.session_state.rate_limiter.can_make_request():
                    try:
                        # Create a more concise prompt
                        optimized_prompt = f"""Question about TSLA stock: {prompt}
                
                Key Data Points:
                - Latest close: ${df['Close'].iloc[-1]:.2f}
                - Highest price: ${df['High'].max():.2f}
                - Average volume: {df['Volume'].mean():,.0f}
                - Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}

                Provide a brief, data-based answer."""

                        st.session_state.rate_limiter.record_request()
                        response = model.generate_content(optimized_prompt)
                        return response
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "token_limit" in error_msg:
                            st.error("The question requires too much data. Please try a more specific question.")
                            return None
                        # ...rest of error handling...

        # AI response
        if question and model:
            with st.spinner("Thinking..."):
                try:
                    # Process the question to make it more specific
                    specific_question = question.strip()
                    if "dataset" in specific_question.lower():
                        specific_question = specific_question.replace("in the dataset", "")
                    
                    # Get response with optimized prompt
                    response = get_ai_response(model, specific_question)
                    
                    if response and response.text:
                        st.success("Answer:")
                        st.markdown(response.text)
                    else:
                        st.warning("Please try asking a more specific question.")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Please try a more focused question about specific aspects of the data.")
except Exception as e:
    st.error(f"An error occurred while loading or processing the data: {str(e)}")

# ...existing code...

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Powered by Gemini Pro | Built with Streamlit</p>
        <p style='font-size: 0.8rem'>Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d")),
    unsafe_allow_html=True
)