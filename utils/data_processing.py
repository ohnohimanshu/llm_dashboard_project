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

        # Try to find a date column
        possible_date_cols = ['date', 'timestamp', 'datetime', 'time']
        found_date_col = None
        for col in possible_date_cols:
            if col in df.columns:
                found_date_col = col
                break
        if not found_date_col:
            st.error(f"No date-like column found. Available columns: {list(df.columns)}")
            return None

        # Map columns to expected names
        col_map = {
            found_date_col: 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        st.write(f"Columns after renaming: {list(df.columns)}")

        # Remove rows where date is clearly invalid (empty, null, or not a date)
        df = df.dropna(subset=['Date'])
        df = df[df['Date'].astype(str).str.strip() != '']
        # Try to parse dates, skip rows that fail
        def try_parse_date(val):
            try:
                return pd.to_datetime(val, errors='raise')
            except Exception:
                return pd.NaT
        df['Date'] = df['Date'].apply(try_parse_date)
        invalid_dates = df['Date'].isna().sum()
        if invalid_dates > 0:
            st.warning(f"⚠️ Removed {invalid_dates} rows with invalid dates")
            df = df.dropna(subset=['Date'])
        if df.empty:
            raise ValueError("All date values are invalid")

        # Convert price and volume columns to numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('[$,]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Remove rows with any null values in OHLC columns
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close']
        null_counts = df[required_columns].isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls > 0:
            st.warning(f"⚠️ Found null values: {dict(null_counts[null_counts > 0])}")
        original_count = len(df)
        df = df.dropna(subset=required_columns)
        removed_count = original_count - len(df)
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count} rows with null values in OHLC columns")
        if len(df) == 0:
            raise ValueError("No valid data rows remain after cleaning")

        # Sort by date
        df = df.sort_values('Date')
        # Convert datetime to string format for Arrow compatibility
        df = convert_datetime_to_str(df)
        # Ensure all columns are Arrow-compatible (no object/list columns)
        for col in df.columns:
            if df[col].dtype == 'O':
                df[col] = df[col].apply(lambda x: ','.join(map(str, x)) if isinstance(x, (list, tuple)) else str(x) if not pd.isna(x) else '')
        # Apply list string to CSV conversion
        for col in ['Support', 'Resistance', 'direction']:
            if col in df.columns:
                df[col] = df[col].apply(list_str_to_csv)
        st.success(f"✅ Successfully loaded {len(df)} rows of data")
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def list_str_to_csv(val):
    # Converts '[840, 880]' or '[840]' to '840,880' or '840'
    if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, (list, tuple)):
                return ','.join(str(x) for x in parsed)
        except Exception:
            pass
    return val