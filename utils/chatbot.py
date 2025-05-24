import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

def setup_gemini_api(api_key):
    """Setup Gemini API with the provided key"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    return model

def analyze_tsla_data(data):
    """Analyze TSLA data and return key insights"""
    analysis = {
        'total_days': len(data),
        'bullish_days': len(data[data['Direction'] == 'LONG']),
        'bearish_days': len(data[data['Direction'] == 'SHORT']),
        'neutral_days': len(data[data['Direction'] == 'NONE']),
        'avg_volume': data['Volume'].mean(),
        'highest_price': data['High'].max(),
        'lowest_price': data['Low'].min(),
        'price_range': data['High'].max() - data['Low'].min(),
        'most_common_support': data['Support'].mode().iloc[0] if not data['Support'].mode().empty else None,
        'most_common_resistance': data['Resistance'].mode().iloc[0] if not data['Resistance'].mode().empty else None
    }
    return analysis

def get_chatbot_response(model, question, data, analysis):
    """Get response from Gemini model based on the question and data"""
    context = f"""
    You are a financial analyst assistant. Here are some key insights about the TSLA data:
    - Total trading days: {analysis['total_days']}
    - Bullish (LONG) days: {analysis['bullish_days']}
    - Bearish (SHORT) days: {analysis['bearish_days']}
    - Neutral days: {analysis['neutral_days']}
    - Average daily volume: {analysis['avg_volume']:,.0f}
    - Highest price: ${analysis['highest_price']:.2f}
    - Lowest price: ${analysis['lowest_price']:.2f}
    - Price range: ${analysis['price_range']:.2f}
    - Most common support level: {analysis['most_common_support']}
    - Most common resistance level: {analysis['most_common_resistance']}
    
    The data includes daily OHLCV (Open, High, Low, Close, Volume) prices, trading direction (LONG/SHORT/NONE),
    and support/resistance levels for TSLA stock.
    """
    
    prompt = f"{context}\n\nQuestion: {question}\n\nPlease provide a detailed and accurate response based on the data."
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

def display_chatbot(data):
    """Display the chatbot interface"""
    st.subheader("💬 TSLA Data Analysis Chatbot")
    
    # Initialize session state for chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Get Gemini API key
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.warning("Please set your Gemini API key in the secrets.toml file")
        return
    
    # Setup Gemini model
    model = setup_gemini_api(api_key)
    
    # Analyze data
    analysis = analyze_tsla_data(data)
    
    # Display sample questions
    st.write("Here are some example questions you can ask:")
    sample_questions = [
        "How many days was TSLA bullish in the dataset?",
        "What was the highest price reached by TSLA?",
        "What is the average daily trading volume?",
        "What is the most common support level?",
        "How many days had a SHORT direction?",
        "What is the price range (highest - lowest) in the dataset?",
        "What percentage of days were neutral (NONE direction)?",
        "What was the most volatile day based on the price range?",
        "How many days had both support and resistance levels?",
        "What is the trend of TSLA based on the direction markers?",
        # New creative questions
        "What is the average price difference between support and resistance levels?",
        "On which days did TSLA show the strongest bullish momentum?",
        "What is the correlation between trading volume and price direction?",
        "How often does TSLA break through its resistance levels?",
        "What is the average duration between support and resistance level changes?",
        "Which days had the most significant price gaps between open and close?",
        "What is the success rate of LONG vs SHORT signals?",
        "How does the price behave after breaking support or resistance levels?",
        "What is the average price movement on days with NONE direction?",
        "Which price levels have been the most reliable support/resistance points?"
    ]
    
    for question in sample_questions:
        if st.button(question):
            response = get_chatbot_response(model, question, data, analysis)
            st.session_state.chat_history.append({"question": question, "answer": response})
    
    # Custom question input
    user_question = st.text_input("Or ask your own question about the TSLA data:")
    if user_question:
        response = get_chatbot_response(model, user_question, data, analysis)
        st.session_state.chat_history.append({"question": user_question, "answer": response})
    
    # Display chat history
    st.subheader("Chat History")
    for chat in st.session_state.chat_history:
        st.write(f"Q: {chat['question']}")
        st.write(f"A: {chat['answer']}")
        st.write("---") 