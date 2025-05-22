import pandas as pd
from pathlib import Path

def load_data(file_path: str) -> pd.DataFrame:
    """Load and process TSLA stock data"""
    try:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
            
        # Read CSV file with lowercase column names
        df = pd.read_csv(file_path)
        
        # Rename columns to match expected format
        column_mapping = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Convert date strings to datetime
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
        
        # Convert volume to numeric, removing commas
        df['Volume'] = df['Volume'].str.replace(',', '').astype(float)
        
        # Convert price columns to float
        price_columns = ['Open', 'High', 'Low', 'Close']
        for col in price_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by date
        df = df.sort_values('Date')
        
        # Remove any invalid rows
        df = df.dropna()
        
        return df
        
    except Exception as e:
        raise Exception(f"Error processing data: {str(e)}")
