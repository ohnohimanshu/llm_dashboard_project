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
    if data is None or data.empty:
        st.warning("Chart cannot be displayed. No data provided.")
        return
    
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        st.warning(f"Chart cannot be displayed. Missing columns: {missing_columns}")
        return

    # Clean and prepare data with strict validation
    valid_data = []
    markers = []
    
    for idx, row in data.iterrows():
        try:
            # Validate date
            if not is_valid_date(row['Date']):
                continue
                
            # Validate OHLC values
            ohlc_values = {}
            skip_row = False
            
            for col in ['Open', 'High', 'Low', 'Close']:
                if not is_valid_number(row[col]):
                    skip_row = True
                    break
                ohlc_values[col.lower()] = round(float(row[col]), 2)
            
            if skip_row:
                continue
            
            # Additional validation: High >= Low, and OHLC values are logical
            if ohlc_values['high'] < ohlc_values['low']:
                continue
                
            # Convert date to proper format
            ts = pd.to_datetime(row['Date'])
            date_str = ts.strftime("%Y-%m-%d")
            
            candle_data = {
                "time": date_str,
                "open": ohlc_values['open'],
                "high": ohlc_values['high'],
                "low": ohlc_values['low'],
                "close": ohlc_values['close']
            }
            valid_data.append(candle_data)
            
            # Add direction marker if available
            if 'Direction' in row and not pd.isna(row['Direction']):
                direction = str(row['Direction']).upper()
                if direction in ['LONG', 'SHORT']:
                    marker = {
                        "time": date_str,
                        "position": "belowBar" if direction == 'LONG' else "aboveBar",
                        "color": "#26a69a" if direction == 'LONG' else "#ef5350",
                        "shape": "arrowUp" if direction == 'LONG' else "arrowDown",
                        "text": direction
                    }
                    markers.append(marker)
                elif direction == 'NONE':
                    marker = {
                        "time": date_str,
                        "position": "belowBar",
                        "color": "#ffd700",
                        "shape": "circle",
                        "text": "None"
                    }
                    markers.append(marker)
            
        except Exception as e:
            # Skip invalid rows silently
            continue

    if not valid_data:
        st.error("No valid candlestick data found. Please check your data format.")
        st.write("Data requirements:")
        st.write("- Date column with valid dates")
        st.write("- Open, High, Low, Close columns with positive numbers")
        st.write("- High >= Low for each row")
        return

    # Sort data by date to ensure proper ordering
    valid_data.sort(key=lambda x: x['time'])
    markers.sort(key=lambda x: x['time'])

    st.success(f"✅ Valid candles loaded: {len(valid_data)}")
    
    # Show sample data for debugging
    if st.checkbox("Show sample data", key=f"{key}_debug"):
        st.write("Sample candles:")
        for i, candle in enumerate(valid_data[:3]):
            st.write(f"Candle {i+1}: {candle}")
            
    # Additional debugging info
    if len(valid_data) > 0:
        st.write(f"📊 Date range: {valid_data[0]['time']} to {valid_data[-1]['time']}")
        price_values = [c['close'] for c in valid_data]
        st.write(f"💰 Price range: ${min(price_values):.2f} - ${max(price_values):.2f}")

    # Convert to JSON with error handling
    try:
        chart_data_json = json.dumps(valid_data)
        markers_json = json.dumps(markers)
    except Exception as e:
        st.error(f"Error serializing data: {str(e)}")
        return

    # Prepare support and resistance bands
    support_bands = []
    resistance_bands = []
    
    if 'Support' in data.columns:
        for idx, row in data.iterrows():
            if not pd.isna(row['Support']):
                prices = parse_price_list(row['Support'])
                if prices:
                    support_bands.append({
                        "time": pd.to_datetime(row['Date']).strftime("%Y-%m-%d"),
                        "value": min(prices),
                        "lineWidth": 2,
                        "lineColor": "#26a69a",
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Support Band"
                    })
                    support_bands.append({
                        "time": pd.to_datetime(row['Date']).strftime("%Y-%m-%d"),
                        "value": max(prices),
                        "lineWidth": 2,
                        "lineColor": "#26a69a",
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Support Band"
                    })
    
    if 'Resistance' in data.columns:
        for idx, row in data.iterrows():
            if not pd.isna(row['Resistance']):
                prices = parse_price_list(row['Resistance'])
                if prices:
                    resistance_bands.append({
                        "time": pd.to_datetime(row['Date']).strftime("%Y-%m-%d"),
                        "value": min(prices),
                        "lineWidth": 2,
                        "lineColor": "#ef5350",
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Resistance Band"
                    })
                    resistance_bands.append({
                        "time": pd.to_datetime(row['Date']).strftime("%Y-%m-%d"),
                        "value": max(prices),
                        "lineWidth": 2,
                        "lineColor": "#ef5350",
                        "lineStyle": 0,
                        "axisLabelVisible": True,
                        "title": "Resistance Band"
                    })

    html = f'''
    <div id="{key}_container" style="width: 100%; height: {height}px; border: 1px solid #ddd; position: relative;"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <script>
    (function() {{
        let chartInstance = null;
        let candlestickSeries = null;
        let initializationAttempts = 0;
        const MAX_ATTEMPTS = 50;  // Maximum number of initialization attempts
        const RETRY_DELAY = 100;  // Delay between attempts in milliseconds
        
        function waitForContainer() {{
            return new Promise((resolve, reject) => {{
                const container = document.getElementById("{key}_container");
                if (!container) {{
                    reject(new Error('Container not found'));
                    return;
                }}
                
                const checkDimensions = () => {{
                    if (container.clientWidth > 0 && container.clientHeight > 0) {{
                        resolve(container);
                    }} else {{
                        initializationAttempts++;
                        if (initializationAttempts >= MAX_ATTEMPTS) {{
                            reject(new Error('Container dimensions not available after maximum attempts'));
                            return;
                        }}
                        setTimeout(checkDimensions, RETRY_DELAY);
                    }}
                }};
                
                checkDimensions();
            }});
        }}
        
        async function initChart() {{
            try {{
                // Wait for container to be ready
                const container = await waitForContainer();
                
                // Clear any existing chart
                if (chartInstance) {{
                    chartInstance.remove();
                    chartInstance = null;
                }}
                
                container.innerHTML = '';

                // Create chart instance
                chartInstance = LightweightCharts.createChart(container, {{
                    width: container.clientWidth,
                    height: {height},
                    layout: {{
                        backgroundColor: '#ffffff',
                        textColor: '#333333',
                        fontSize: 12,
                        fontFamily: 'Arial, sans-serif'
                    }},
                    grid: {{
                        vertLines: {{ color: '#f0f0f0' }},
                        horzLines: {{ color: '#f0f0f0' }}
                    }},
                    crosshair: {{
                        mode: LightweightCharts.CrosshairMode.Normal,
                    }},
                    rightPriceScale: {{ 
                        borderColor: '#cccccc',
                        scaleMargins: {{
                            top: 0.1,
                            bottom: 0.1
                        }},
                        visible: true
                    }},
                    timeScale: {{ 
                        borderColor: '#cccccc',
                        timeVisible: true,
                        secondsVisible: false,
                        fixLeftEdge: true,
                        fixRightEdge: true
                    }},
                    handleScroll: {{
                        mouseWheel: true,
                        pressedMouseMove: true,
                        horzTouchDrag: true,
                        vertTouchDrag: true
                    }},
                    handleScale: {{
                        mouseWheel: true,
                        pinch: true,
                        axisPressedMouseMove: true,
                        axisDoubleClickReset: true
                    }}
                }});

                // Create candlestick series
                candlestickSeries = chartInstance.addCandlestickSeries({{
                    upColor: '#26a69a',
                    downColor: '#ef5350',
                    borderVisible: false,
                    wickUpColor: '#26a69a',
                    wickDownColor: '#ef5350'
                }});

                // Parse and validate chart data
                const chartData = JSON.parse('{chart_data_json}');
                if (!Array.isArray(chartData) || chartData.length === 0) {{
                    throw new Error('Invalid chart data format');
                }}

                // Set data to the series
                candlestickSeries.setData(chartData);

                // Add markers
                const markers = JSON.parse('{markers_json}');
                if (markers && markers.length > 0) {{
                    candlestickSeries.setMarkers(markers);
                }}

                // Add support and resistance bands
                const supportBands = JSON.parse('{json.dumps(support_bands)}');
                const resistanceBands = JSON.parse('{json.dumps(resistance_bands)}');

                // Create support band series
                if (supportBands && supportBands.length > 0) {{
                    const supportSeries = chartInstance.addLineSeries({{
                        color: '#26a69a',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Solid,
                        lastValueVisible: false,
                        priceLineVisible: false,
                    }});
                    supportSeries.setData(supportBands);
                }}

                // Create resistance band series
                if (resistanceBands && resistanceBands.length > 0) {{
                    const resistanceSeries = chartInstance.addLineSeries({{
                        color: '#ef5350',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Solid,
                        lastValueVisible: false,
                        priceLineVisible: false,
                    }});
                    resistanceSeries.setData(resistanceBands);
                }}

                // Fit content
                chartInstance.timeScale().fitContent();

                // Handle window resize
                const resizeObserver = new ResizeObserver(entries => {{
                    if (chartInstance) {{
                        chartInstance.applyOptions({{
                            width: container.clientWidth
                        }});
                    }}
                }});
                resizeObserver.observe(container);

            }} catch (error) {{
                console.error('Error initializing chart:', error);
                // Retry initialization if container wasn't ready
                if (initializationAttempts < MAX_ATTEMPTS) {{
                    setTimeout(initChart, RETRY_DELAY);
                }}
            }}
        }}

        // Start initialization process
        initChart();
    }})();
    </script>
    '''
    
    components.html(html, height=height + 10)