import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import uuid
import numpy as np
from datetime import datetime


def is_valid_number(value):
    """Check if value is a valid finite number"""
    try:
        val = float(value)
        return not (pd.isna(val) or np.isinf(val) or val <= 0)
    except (ValueError, TypeError):
        return False


def is_valid_date(date_val):
    """Check if date value can be converted to valid datetime"""
    try:
        if pd.isna(date_val):
            return False
        ts = pd.to_datetime(date_val, errors='coerce')
        return not pd.isna(ts)
    except:
        return False


def parse_price_list(price_str):
    """Parse a string of comma-separated prices into a list of floats"""
    if pd.isna(price_str) or not price_str or price_str == "[]":
        return []
    try:
        # Remove brackets and split by comma
        clean_str = str(price_str).strip('[]')
        return [float(x.strip()) for x in clean_str.split(',') if x.strip()]
    except:
        return []


def tradingview_chart(data, height=500, key=None):
    if key is None:
        key = str(uuid.uuid4()).replace('-', '')

    required_columns = ['Date', 'Open', 'High', 'Low', 'Close']
    
    # Validate input data
    if not all(col in data.columns for col in required_columns):
        st.error(f"Missing required columns. Required: {required_columns}")
        return

    # Convert date to string format
    data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
    
    # Prepare candlestick data
    candlestick_data = []
    for idx, row in data.iterrows():
        if all(pd.notna(row[col]) for col in ['Open', 'High', 'Low', 'Close']):
            candlestick_data.append({
                "time": row['Date'],
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close'])
            })

    # Prepare direction markers (arrow/circle without label)
    direction_markers = []
    if 'Direction' in data.columns:
        for idx, row in data.iterrows():
            if pd.notna(row['Direction']):
                direction = row['Direction'].upper()
                if direction == 'LONG':
                    marker = {
                        "time": row['Date'],
                        "position": "belowBar",
                        "color": "#26a69a",
                        "shape": "arrowUp"
                    }
                    direction_markers.append(marker)
                elif direction == 'SHORT':
                    marker = {
                        "time": row['Date'],
                        "position": "aboveBar",
                        "color": "#ef5350",
                        "shape": "arrowDown"
                    }
                    direction_markers.append(marker)
                elif direction == 'NONE':
                    marker = {
                        "time": row['Date'],
                        "position": "inBar",
                        "color": "#FFD600",
                        "shape": "circle"
                    }
                    direction_markers.append(marker)

    # Prepare support and resistance area bands (filled)
    support_band_data = []
    resistance_band_data = []
    if 'Support' in data.columns:
        for idx, row in data.iterrows():
            prices = parse_price_list(row['Support']) if pd.notna(row['Support']) else []
            if prices:
                support_band_data.append({
                    "time": row['Date'],
                    "min": min(prices),
                    "max": max(prices)
                })
    if 'Resistance' in data.columns:
        for idx, row in data.iterrows():
            prices = parse_price_list(row['Resistance']) if pd.notna(row['Resistance']) else []
            if prices:
                resistance_band_data.append({
                    "time": row['Date'],
                    "min": min(prices),
                    "max": max(prices)
                })

    # Create HTML with TradingView chart
    html = f'''
    <div id="{key}_container" style="width: 100%; height: {height}px; border: 1px solid #ddd; position: relative;"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <script>
    (function() {{
        const container = document.getElementById('{key}_container');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: {height},
            layout: {{
                background: {{ color: '#ffffff' }},
                textColor: '#333',
            }},
            grid: {{
                vertLines: {{ color: '#f0f0f0' }},
                horzLines: {{ color: '#f0f0f0' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '#ddd',
            }},
            timeScale: {{
                borderColor: '#ddd',
                timeVisible: true,
                secondsVisible: false,
            }},
        }});

        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350'
        }});
        candlestickSeries.setData({json.dumps(candlestick_data)});

        // Add direction markers
        candlestickSeries.setMarkers({json.dumps(direction_markers)});

        // Support band (filled area)
        const supportBandData = {json.dumps(support_band_data)};
        if (supportBandData.length > 0) {{
            const supportMin = supportBandData.map(d => ({{ time: d.time, value: d.min }}));
            const supportMax = supportBandData.map(d => ({{ time: d.time, value: d.max }}));
            const supportArea = chart.addAreaSeries({{
                topColor: 'rgba(38,166,154,0.2)',
                bottomColor: 'rgba(38,166,154,0.05)',
                lineColor: '#26a69a',
                lineWidth: 1,
                priceLineVisible: false,
                lastValueVisible: false,
            }});
            supportArea.setData(supportMax);
            // Optionally, you can overlay a second area for the min if you want a band effect
        }}

        // Resistance band (filled area)
        const resistanceBandData = {json.dumps(resistance_band_data)};
        if (resistanceBandData.length > 0) {{
            const resistanceMin = resistanceBandData.map(d => ({{ time: d.time, value: d.min }}));
            const resistanceMax = resistanceBandData.map(d => ({{ time: d.time, value: d.max }}));
            const resistanceArea = chart.addAreaSeries({{
                topColor: 'rgba(239,83,80,0.2)',
                bottomColor: 'rgba(239,83,80,0.05)',
                lineColor: '#ef5350',
                lineWidth: 1,
                priceLineVisible: false,
                lastValueVisible: false,
            }});
            resistanceArea.setData(resistanceMax);
        }}

        // Handle window resize
        window.addEventListener('resize', () => {{
            chart.applyOptions({{
                width: container.clientWidth
            }});
        }});
    }})();
    </script>
    '''
    
    components.html(html, height=height + 10)