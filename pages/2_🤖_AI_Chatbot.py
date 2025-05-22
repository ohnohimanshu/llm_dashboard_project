import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from utils.data_processing import load_data
import time
import socket
import requests
from datetime import datetime, timedelta

# Rate limiting and error handling configuration
RATE_LIMITS = {
    "requests_per_minute": 3,  # Maximum 3 requests per minute
    "requests_per_day": 50,    # Maximum 50 requests per day
    "retry_delay": 60,        # Seconds to wait between retries
    "token_limit": 8000,     # Conservative token limit for input context
    "network_retry_delay": 10, # Initial seconds to wait for network errors (increased from 5)
    "max_backoff": 120,       # Maximum backoff time in seconds (increased from 60)
    "backoff_factor": 2.5,    # Exponential backoff multiplier (increased from 2)
    "jitter_factor": 0.3,     # Random jitter factor to avoid thundering herd (increased from 0.25)
    "cooldown_period": 300,   # Cooldown period after hitting rate limit (seconds)
    "service_unavailable_backoff": 15,  # Special backoff for 503 errors (seconds)
    "max_network_retries": 5,  # Maximum number of retries for network errors
    "connectivity_check_timeout": 3  # Timeout for connectivity checks (seconds)
}

class RateLimiter:
    def __init__(self):
        self.last_request_time = datetime.now() - timedelta(minutes=1)
        self.requests_this_minute = 0
        self.requests_today = 0
        self.day_start = datetime.now().date()
        self.last_error_time = None
        self.network_errors = 0
        self.last_network_error_time = None
        self.consecutive_network_errors = 0
        self.rate_limit_errors = 0
        self.last_rate_limit_time = None
        self.in_cooldown = False
        self.cooldown_end_time = None
    
    def can_make_request(self):
        now = datetime.now()
        
        # Check if we're in a cooldown period after rate limit errors
        if self.in_cooldown and self.cooldown_end_time:
            if now < self.cooldown_end_time:
                # Still in cooldown period
                return False
            else:
                # Cooldown period ended
                self.in_cooldown = False
                self.cooldown_end_time = None
        
        # Reset daily counter if it's a new day
        if now.date() != self.day_start:
            self.requests_today = 0
            self.day_start = now.date()
        
        # Reset minute counter if a minute has passed
        if (now - self.last_request_time).seconds >= 60:
            self.requests_this_minute = 0
        
        return (self.requests_this_minute < RATE_LIMITS["requests_per_minute"] and 
                self.requests_today < RATE_LIMITS["requests_per_day"])
    
    def record_request(self):
        self.requests_this_minute += 1
        self.requests_today += 1
        self.last_request_time = datetime.now()
        
    def record_error(self, error_type="general"):
        now = datetime.now()
        self.last_error_time = now
        
        # Track network errors separately
        if error_type == "network":
            self.network_errors += 1
            self.last_network_error_time = now
            self.consecutive_network_errors += 1
        elif error_type == "rate_limit":
            self.rate_limit_errors += 1
            self.last_rate_limit_time = now
            
            # Implement cooldown period after rate limit errors
            # The more rate limit errors we get, the longer the cooldown
            cooldown_multiplier = min(self.rate_limit_errors, 5)  # Cap at 5x
            cooldown_time = RATE_LIMITS["cooldown_period"] * cooldown_multiplier
            
            self.in_cooldown = True
            self.cooldown_end_time = now + timedelta(seconds=cooldown_time)
        else:
            # Reset consecutive network errors if we get a different type of error
            self.consecutive_network_errors = 0
        
    def get_wait_time(self):
        """Calculate wait time based on rate limits and cooldown status"""
        now = datetime.now()
        
        # If in cooldown, return time until cooldown ends
        if self.in_cooldown and self.cooldown_end_time:
            wait_seconds = (self.cooldown_end_time - now).total_seconds()
            return max(wait_seconds, 0)
            
        # Check per-minute rate limit
        if self.requests_this_minute >= RATE_LIMITS["requests_per_minute"]:
            # Time until next minute starts
            seconds_since_last = (now - self.last_request_time).seconds
            base_wait_time = max(60 - seconds_since_last, 0)
            
            # Add jitter to prevent thundering herd problem
            import random
            jitter = random.uniform(0, RATE_LIMITS["jitter_factor"] * base_wait_time)
            return base_wait_time + jitter
            
        return 0
        
    def get_network_backoff_time(self, attempt=0, error_type=None):
        """Calculate exponential backoff time for network errors with jitter"""
        import random
        
        # Use both the attempt number and consecutive network errors to determine backoff
        factor = max(attempt, self.consecutive_network_errors)
        
        # Special handling for 503 Service Unavailable errors
        if error_type == "service_unavailable":
            # Start with a higher base delay for 503 errors
            base_delay = RATE_LIMITS.get("service_unavailable_backoff", 15)
            # More aggressive backoff for service unavailable
            base_backoff_time = min(
                base_delay * (RATE_LIMITS["backoff_factor"] ** (factor + 1)),
                RATE_LIMITS["max_backoff"]
            )
        else:
            # Standard backoff for other network errors
            base_backoff_time = min(
                RATE_LIMITS["network_retry_delay"] * (RATE_LIMITS["backoff_factor"] ** factor),
                RATE_LIMITS["max_backoff"]
            )
        
        # Add jitter to prevent thundering herd problem
        # More jitter for higher backoff times
        jitter_max = RATE_LIMITS["jitter_factor"] * base_backoff_time
        jitter = random.uniform(0, jitter_max)
        
        # For debugging
        # print(f"Backoff time: {base_backoff_time + jitter}s (base: {base_backoff_time}, jitter: {jitter})")
        
        return base_backoff_time + jitter
        
    def reset_network_errors(self):
        """Reset network error counters after successful request"""
        self.consecutive_network_errors = 0
        
    def reset_rate_limit_errors(self):
        """Reset rate limit error counters after successful request"""
        self.rate_limit_errors = 0
        self.in_cooldown = False
        self.cooldown_end_time = None
        
    def get_rate_limit_status(self):
        """Get current rate limit status for display to user"""
        now = datetime.now()
        status = {
            "requests_this_minute": self.requests_this_minute,
            "requests_today": self.requests_today,
            "minute_limit": RATE_LIMITS["requests_per_minute"],
            "daily_limit": RATE_LIMITS["requests_per_day"],
            "in_cooldown": self.in_cooldown,
            "rate_limit_errors": self.rate_limit_errors,
            "network_errors": self.network_errors
        }
        
        # Calculate time until next request allowed
        if self.in_cooldown and self.cooldown_end_time:
            status["cooldown_remaining"] = max(int((self.cooldown_end_time - now).total_seconds()), 0)
        else:
            status["cooldown_remaining"] = 0
            
        # Calculate time until minute reset if at minute limit
        if self.requests_this_minute >= RATE_LIMITS["requests_per_minute"]:
            seconds_since_last = (now - self.last_request_time).seconds
            status["minute_reset_in"] = max(60 - seconds_since_last, 0)
        else:
            status["minute_reset_in"] = 0
            
        return status

# Network connectivity check function
def check_network_connectivity(host="www.google.com", timeout=None):
    """Check if network is available by attempting to connect to a known host"""
    if timeout is None:
        timeout = RATE_LIMITS["connectivity_check_timeout"]
        
    # Try multiple hosts if the first one fails
    hosts = [host, "api.gemini.google.com", "8.8.8.8"]
    errors = []
    
    for current_host in hosts:
        try:
            # For IP addresses, skip DNS resolution
            if not current_host[0].isdigit():
                # Try DNS resolution first
                socket.gethostbyname(current_host)
            
            # Try HTTP request with timeout
            if current_host == "8.8.8.8":
                # For Google DNS, just try to establish a socket connection
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((current_host, 53))
                s.close()
                return True, None
            else:
                # For web hosts, make an HTTP request
                protocol = "https://" if not current_host.startswith("http") else ""
                response = requests.get(f"{protocol}{current_host}", 
                                      timeout=timeout, 
                                      headers={"User-Agent": "Streamlit-App-Connectivity-Check"})
                return True, None
        except socket.gaierror:
            errors.append(f"DNS resolution failed for {current_host}")
        except requests.exceptions.Timeout:
            errors.append(f"Connection to {current_host} timed out")
        except requests.exceptions.ConnectionError:
            errors.append(f"Connection error with {current_host}")
        except Exception as e:
            errors.append(f"Error with {current_host}: {str(e)}")
    
    # If we get here, all hosts failed
    error_summary = "\n- " + "\n- ".join(errors)
    return False, f"Network connectivity issues detected: {error_summary}\nCheck your internet connection."

# Initialize rate limiter
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = RateLimiter()

st.set_page_config(page_title="TSLA AI Chatbot", layout="wide")
st.title("🤖 Ask Me Anything About TSLA")

# Load and preview data
try:
    df = load_data("data/tsla_data.csv")
    if df is not None and not df.empty:
        # Create data summary for more efficient token usage
        data_summary = {
            "total_records": len(df),
            "date_range": f"{df['Date'].min().date()} to {df['Date'].max().date()}",
            "avg_close": round(df['Close'].mean(), 2),
            "max_price": round(df['High'].max(), 2),
            "min_price": round(df['Low'].min(), 2),
            "avg_volume": f"{int(df['Volume'].mean()):,}"
        }
        
        # Add simple trend indicators
        df['Price_Change'] = df['Close'].diff()
        df['Signal'] = np.where(df['Price_Change'] > 0, 'LONG', 'SHORT')
        data_summary['long_signals'] = (df['Signal'] == 'LONG').sum()
        data_summary['short_signals'] = (df['Signal'] == 'SHORT').sum()
        
        # Store data summary in session state for later use in prompts
        if 'data_summary' not in st.session_state:
            st.session_state.data_summary = data_summary
        
        # Display data preview
        st.write("### Preview of TSLA Data")
        st.dataframe(df.head(), use_container_width=True)
        
        # Show data summary
        st.write("### Data Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Total records:** {data_summary['total_records']}")
            st.write(f"**Date range:** {data_summary['date_range']}")
            st.write(f"**Average close price:** ${data_summary['avg_close']}")
        with col2:
            st.write(f"**Price range:** ${data_summary['min_price']} - ${data_summary['max_price']}")
            st.write(f"**Average volume:** {data_summary['avg_volume']}")
            st.write(f"**LONG/SHORT signals:** {data_summary['long_signals']}/{data_summary['short_signals']}")
    else:
        st.error("No data available or empty dataset")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Display rate limit status in sidebar
with st.sidebar:
    st.write("### API Rate Limit Status")
    if 'rate_limiter' in st.session_state:
        status = st.session_state.rate_limiter.get_rate_limit_status()
        
        # Create a progress bar for minute limit
        minute_usage = status["requests_this_minute"] / status["minute_limit"]
        st.write(f"Minute usage: {status['requests_this_minute']}/{status['minute_limit']} requests")
        st.progress(min(minute_usage, 1.0))
        
        # Create a progress bar for daily limit
        daily_usage = status["requests_today"] / status["daily_limit"]
        st.write(f"Daily usage: {status['requests_today']}/{status['daily_limit']} requests")
        st.progress(min(daily_usage, 1.0))
        
        # Show cooldown status if in cooldown
        if status["in_cooldown"]:
            st.warning(f"⚠️ In cooldown period: {status['cooldown_remaining']} seconds remaining")
        elif status["minute_reset_in"] > 0:
            st.info(f"⏱️ Rate limit reset in: {status['minute_reset_in']} seconds")
        else:
            st.success("✅ API ready for requests")
            
        # Show error counts
        if status["rate_limit_errors"] > 0 or status["network_errors"] > 0:
            with st.expander("Error History"):
                st.write(f"Rate limit errors: {status['rate_limit_errors']}")
                st.write(f"Network errors: {status['network_errors']}")

# User input and response generation
question = st.text_input("Type your question about TSLA data...")

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
    """Get AI response with rate limiting and retries with exponential backoff for network errors"""
    for attempt in range(max_retries):
        # Check network connectivity before attempting API call
        network_ok, network_error_msg = check_network_connectivity()
        if not network_ok:
            st.warning(f"Network connectivity issue detected before API call: {network_error_msg}")
            st.info("Attempting to proceed despite network issues...")
            
        if st.session_state.rate_limiter.can_make_request():
            try:
                st.session_state.rate_limiter.record_request()
                response = model.generate_content(prompt)
                # Reset error counters on successful request
                st.session_state.rate_limiter.reset_network_errors()
                st.session_state.rate_limiter.reset_rate_limit_errors()
                return response
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle rate limit errors (HTTP 429)
                if "429" in error_msg:  # Rate limit error
                    st.session_state.rate_limiter.record_error(error_type="rate_limit")
                    wait_time = st.session_state.rate_limiter.get_wait_time()
                    if attempt < max_retries - 1:
                        st.warning(f"Rate limit exceeded. Entering cooldown period. Retrying in {int(wait_time)} seconds (Attempt {attempt+1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        st.error("Maximum retry attempts reached. Please try again later.")
                        with st.expander("Rate Limit Information"):
                            st.write("The API has rate limits that restrict how many requests you can make in a given time period.")
                            st.write(f"Current limits: {RATE_LIMITS['requests_per_minute']} requests per minute, {RATE_LIMITS['requests_per_day']} requests per day")
                            st.write("The application will automatically enter a cooldown period after hitting rate limits.")
                
                # Handle network connectivity errors with more specific categorization
                elif any(err in error_msg for err in ["timeout", "connect", "connection", "network", "handshake"]):
                    # Record general network error
                    st.session_state.rate_limiter.record_error(error_type="network")
                    backoff_time = st.session_state.rate_limiter.get_network_backoff_time(attempt)
                    
                    if attempt < max_retries - 1:
                        st.warning(f"Network connectivity issue detected. Retrying in {int(backoff_time)} seconds (Attempt {attempt+1}/{max_retries})")
                        time.sleep(backoff_time)
                        continue
                    else:
                        st.error("Unable to connect to AI service after multiple attempts. Please check your internet connection and try again later.")
                        st.info("The error suggests a network connectivity issue between your application and Google's servers.")
                        # Show more detailed error information
                        with st.expander("Technical Error Details"):
                            st.code(error_msg, language="text")
                            st.write("This appears to be a network connectivity issue. This can happen when:")
                            st.write("- Your network connection is unstable")
                            st.write("- A firewall or proxy is blocking the connection")
                            st.write("- You're using a VPN that's incompatible with the service")
                            st.write("- Your DNS settings are incorrect")
                
                # Special handling for 503 Service Unavailable errors
                elif "503" in error_msg or "service unavailable" in error_msg:
                    # Record network error with specific type
                    st.session_state.rate_limiter.record_error(error_type="network")
                    # Use special backoff strategy for 503 errors
                    backoff_time = st.session_state.rate_limiter.get_network_backoff_time(attempt, error_type="service_unavailable")
                    
                    # For 503 errors, we can retry more times since it's likely a temporary server issue
                    max_503_retries = RATE_LIMITS.get("max_network_retries", 5)
                    
                    if attempt < min(max_retries - 1, max_503_retries - 1):
                        st.warning(f"Google API service temporarily unavailable (HTTP 503). Retrying with increased backoff in {int(backoff_time)} seconds (Attempt {attempt+1}/{max_503_retries})")
                        # Check network connectivity before retrying
                        network_ok, _ = check_network_connectivity()
                        if not network_ok:
                            st.info("Network connectivity issues detected. Waiting for connection to stabilize...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        st.error("Google API service is currently unavailable (HTTP 503). This is likely a temporary issue with Google's servers.")
                        st.info("Please try again later. The service should be restored shortly.")
                        # Show more detailed error information
                        with st.expander("Technical Error Details"):
                            st.code(error_msg, language="text")
                            st.write("HTTP 503 Service Unavailable indicates:")
                            st.write("- Google's servers are temporarily overloaded")
                            st.write("- The service is under maintenance")
                            st.write("- There's a temporary outage in Google's infrastructure")
                            st.write("This is almost always a temporary condition that will be resolved by Google's team.")
                
                # Handle token limit errors
                elif "too many tokens" in error_msg or "token limit" in error_msg:
                    st.error("The request contains too many tokens. Simplifying your query may help.")
                
                # Handle all other errors
                else:
                    st.error(f"Error: {error_msg}")
                
                return None
        else:
            wait_time = st.session_state.rate_limiter.get_wait_time()
            st.warning(f"Rate limit reached. Please wait {wait_time} seconds before trying again.")
            if attempt < max_retries - 1:
                time.sleep(min(wait_time, RATE_LIMITS["retry_delay"]))
                continue
            else:
                return None
    
    return None

# AI response
if question and model:
    with st.spinner("Thinking..."):
        try:
            # Check network connectivity before making API call
            network_ok, network_error_msg = check_network_connectivity()
            if not network_ok:
                st.error(f"Network connectivity issue detected: {network_error_msg}")
                st.warning("Please check your internet connection before proceeding.")
                with st.expander("Network Troubleshooting Tips"):
                    st.write("1. Check if you can access other websites")
                    st.write("2. Restart your router or modem")
                    st.write("3. Try disabling VPN or proxy services if you're using them")
                    st.write("4. Check if your firewall is blocking outgoing connections")
                # Continue anyway, but warn the user
                st.info("Attempting to proceed despite network issues...")
            
            # Get data summary from session state
            data_summary = st.session_state.data_summary
            
            # Create a sample of data (limited rows to reduce tokens)
            sample_size = min(5, len(df))
            data_sample = df.sample(sample_size) if len(df) > sample_size else df
            sample_csv = data_sample.to_csv(index=False)
            
            # Calculate approximate token count (rough estimate)
            prompt_tokens = len(question) + len(str(data_summary)) + len(sample_csv)
            
            # Check if we're likely to exceed token limits
            if prompt_tokens > RATE_LIMITS["token_limit"]:
                # If too large, reduce sample size further or use summary only
                sample_csv = ""
                st.info("Using data summary only due to token limitations.")
            
            # Create an optimized prompt with data summary and limited sample
            prompt = f"""Answer this question about Tesla stock data: {question}
            
            Data Summary:
            - Total records: {data_summary['total_records']}
            - Date range: {data_summary['date_range']}
            - Average close price: ${data_summary['avg_close']}
            - Price range: ${data_summary['min_price']} - ${data_summary['max_price']}
            - Average volume: {data_summary['avg_volume']}
            - LONG signals: {data_summary['long_signals']}
            - SHORT signals: {data_summary['short_signals']}
            
            Sample data (limited rows):
            {sample_csv if sample_csv else 'Not included due to token limitations'}
            
            Give a concise, data-driven answer based on the information provided.
            """
            
            # Display a progress message
            progress_msg = st.empty()
            progress_msg.info("Sending request to AI model...")
            
            # Get AI response with rate limiting and retries
            response = get_ai_response(model, prompt)
            progress_msg.empty()
            
            if response and response.text:
                st.success("Answer:")
                st.markdown(response.text)
            else:
                st.warning("Unable to get a response. Please try again later or simplify your question.")
                
                # If we have consecutive network errors, provide more detailed help
                if st.session_state.rate_limiter.consecutive_network_errors > 0:
                    st.error(f"Network connectivity issues detected. {st.session_state.rate_limiter.consecutive_network_errors} consecutive network errors.")
                    with st.expander("Network Troubleshooting"):
                        st.write("The error suggests connectivity issues between your application and Google's servers:")
                        st.write("1. Check if your internet connection is stable")
                        st.write("2. Try disabling any VPN or proxy services")
                        st.write("3. Check if your firewall is blocking the connection")
                        st.write("4. If on a corporate network, check with your IT department about outbound connection policies")
                        st.write("5. Try again later as this could be a temporary issue with Google's servers")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please wait a few minutes before trying again.")
            
            # Show troubleshooting info in an expander
            with st.expander("Troubleshooting Information"):
                st.write("If you're experiencing issues, try:")
                st.write("1. Asking a simpler question")
                st.write("2. Waiting a few minutes before trying again")
                st.write("3. Refreshing the page")
                st.write("4. Check your internet connection")
                st.write("5. If you're using a VPN, try disabling it temporarily")
                st.write(f"Current rate limits: {RATE_LIMITS['requests_per_minute']} per minute, {RATE_LIMITS['requests_per_day']} per day")