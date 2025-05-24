import pandas as pd
import numpy as np
from pathlib import Path
import re
import streamlit as st
import requests
from io import StringIO
from datetime import datetime
import ast


def convert_datetime_to_str(df, date_column='Date'):
    """Convert datetime column to string format for Arrow compatibility"""
    if date_column in df.columns and pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df[date_column] = df[date_column].dt.strftime('%Y-%m-%d')
    return df


def parse_price_list(val):
    """Parse price list string into list of floats"""
    if pd.isna(val):
        return "[]"
    if isinstance(val, str):
        # Remove brackets and split by comma
        clean_str = val.strip('[]')
        try:
            prices = [float(x.strip()) for x in clean_str.split(',') if x.strip()]
            return str(prices)  # Return as string representation of list
        except:
            return "[]"
    return "[]"


def load_data(file_path: str = 'data/tsla_data.csv') -> pd.DataFrame:
    """Load and process TSLA stock data from a local CSV file only."""
    try:
        # Always use the local CSV file
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        # Read CSV file with proper parsing
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(file_path, encoding='latin-1')
            except:
                df = pd.read_csv(file_path, encoding='cp1252')

        st.write(f"📋 Original columns: {list(df.columns)}")
        st.write(f"📊 Data shape: {df.shape}")

        # Clean column names - remove extra spaces and convert to lowercase for mapping
        df.columns = df.columns.str.strip().str.lower()
        st.write(f"Columns after lowercasing: {list(df.columns)}")

        # Map columns to expected names
        col_map = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'direction': 'Direction',
            'support': 'Support',
            'resistance': 'Resistance'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        st.write(f"Columns after renaming: {list(df.columns)}")

        # Process date column
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # Convert price columns to numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('[$,]', '', regex=True), errors='coerce')

        # Process direction column
        if 'Direction' in df.columns:
            df['Direction'] = df['Direction'].str.upper()
            df['Direction'] = df['Direction'].apply(lambda x: x if x in ['LONG', 'SHORT', 'NONE'] else 'NONE')

        # Process support and resistance columns - keep as strings for Arrow compatibility
        if 'Support' in df.columns:
            df['Support'] = df['Support'].apply(parse_price_list)
        if 'Resistance' in df.columns:
            df['Resistance'] = df['Resistance'].apply(parse_price_list)

        # Remove rows with invalid OHLC data
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        # Sort by date
        df = df.sort_values('Date')
        
        # Convert datetime to string format for Arrow compatibility
        df = convert_datetime_to_str(df)
        
        # Ensure all columns have proper dtypes for Arrow serialization
        df = df.astype({
            'Date': 'string',
            'Open': 'float64',
            'High': 'float64',
            'Low': 'float64',
            'Close': 'float64',
            'Volume': 'float64',
            'Direction': 'string',
            'Support': 'string',
            'Resistance': 'string'
        })
        
        st.success(f"✅ Successfully loaded {len(df)} rows of data")
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None