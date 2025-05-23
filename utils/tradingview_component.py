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
    if pd.isna(price_str) or not price_str:
        return []
    try:
        return [float(x.strip()) for x in str(price_str).split(',') if x.strip()]
    except:
        return []


def tradingview_chart(data, height=500, key=None, support_levels=None, resistance_levels=None):
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

    # Prepare direction markers
    direction_markers = []
    if 'Direction' in data.columns:
        for idx, row in data.iterrows():
            if pd.notna(row['Direction']):
                direction = row['Direction'].upper()
                if direction in ['LONG', 'SHORT', 'NONE']:
                    marker = {
                        "time": row['Date'],
                        "position": "belowBar" if direction == 'LONG' else "aboveBar" if direction == 'SHORT' else "inBar",
                        "color": "#26a69a" if direction == 'LONG' else "#ef5350" if direction == 'SHORT' else "#ffeb3b",
                        "shape": "arrowUp" if direction == 'LONG' else "arrowDown" if direction == 'SHORT' else "circle",
                        "text": direction
                    }
                    direction_markers.append(marker)

    # Prepare support and resistance bands
    support_bands = []
    resistance_bands = []
    
    if 'Support' in data.columns:
        for idx, row in data.iterrows():
            if pd.notna(row['Support']):
                prices = parse_price_list(row['Support'])
                if prices:
                    # Add lower bound of support band (green)
                    support_bands.append({
                        "time": row['Date'],
                        "value": min(prices),
                        "lineWidth": 2,
                        "lineColor": "#26a69a",  # Green color
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Support Lower"
                    })
                    # Add upper bound of support band (green)
                    support_bands.append({
                        "time": row['Date'],
                        "value": max(prices),
                        "lineWidth": 2,
                        "lineColor": "#26a69a",  # Green color
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Support Upper"
                    })
    
    if 'Resistance' in data.columns:
        for idx, row in data.iterrows():
            if pd.notna(row['Resistance']):
                prices = parse_price_list(row['Resistance'])
                if prices:
                    # Add lower bound of resistance band (red)
                    resistance_bands.append({
                        "time": row['Date'],
                        "value": min(prices),
                        "lineWidth": 2,
                        "lineColor": "#ef5350",  # Red color
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Resistance Lower"
                    })
                    # Add upper bound of resistance band (red)
                    resistance_bands.append({
                        "time": row['Date'],
                        "value": max(prices),
                        "lineWidth": 2,
                        "lineColor": "#ef5350",  # Red color
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Resistance Upper"
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
        const directionMarkers = {json.dumps(direction_markers)};
        directionMarkers.forEach(marker => {{
            candlestickSeries.setMarkers([marker]);
        }});

        // Add support and resistance bands
        const supportBands = {json.dumps(support_bands)};
        const resistanceBands = {json.dumps(resistance_bands)};

        // Create support band series (green)
        if (supportBands && supportBands.length > 0) {{
            const supportSeries = chart.addLineSeries({{
                color: '#26a69a',  // Green color
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                lastValueVisible: false,
                priceLineVisible: false,
                title: 'Support Band'
            }});
            supportSeries.setData(supportBands);
        }}

        // Create resistance band series (red)
        if (resistanceBands && resistanceBands.length > 0) {{
            const resistanceSeries = chart.addLineSeries({{
                color: '#ef5350',  // Red color
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                lastValueVisible: false,
                priceLineVisible: false,
                title: 'Resistance Band'
            }});
            resistanceSeries.setData(resistanceBands);
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
