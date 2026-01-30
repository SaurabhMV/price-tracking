import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Intraday Trend Dashboard", layout="wide")
st.title("📈 18/50 SMA Multi-Timeframe Dashboard")

# --- Sidebar Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

# Period Selection
period_options = ["1d", "5d", "1mo", "6mo", "1y", "2y", "5y", "max"]
period = st.sidebar.selectbox("History (Period)", period_options, index=2)

# Interval Selection (New Options Added)
interval_mapping = {
    "1 Minute": "1m",
    "5 Minutes": "5m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "1 Day": "1d",
    "1 Week": "1wk"
}
interval_display = st.sidebar.selectbox("Candle Interval", list(interval_mapping.keys()), index=5)
selected_interval = interval_mapping[interval_display]

if ticker:
    try:
        # 1. Fetch Data
        df = yf.download(ticker, period=period, interval=selected_interval, auto_adjust=True)
        
        if df.empty:
            st.warning(f"⚠️ No data found. Yahoo Finance usually limits '{interval_display}' data to shorter periods (e.g., 60 days). Try reducing your 'History' setting.")
        else:
            # Flatten MultiIndex if necessary
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # Crossover Detection
            df['Signal'] = 0.0
            if len(df) > 50:
                df.loc[df.index[50:], 'Signal'] = np.where(df['SMA18'][50:] > df['SMA50'][50:], 1.0, 0.0)
                df['Position'] = df['Signal'].diff()
            else:
                df['Position'] = 0

            # --- 3. Plotting ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, 
                subplot_titles=(f'{ticker} Price & SMAs', 'Volume & 20-MA', 'RSI Momentum'), 
                row_width=[0.2, 0.2, 0.6] 
            )

            # Row 1: Candlestick & SMAs
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=2), name='50 SMA'), row=1, col=1)

            # Markers (BUY/SELL)
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-up', size=14, color='lime'),
                name='BUY', text=["BUY"] * len(buy_pts), textposition="bottom center"), row=1, col=1)

            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-down', size=14, color='red'),
                name='SELL', text=["SELL"] * len(sell_pts), textposition="top center"), row=1, col=1)

            # Row 2: Volume Bars + Volume Avg
            vol_colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=vol_colors, showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Vol_Avg'], line=dict(color='yellow', width=1.5), name='Vol 20-MA'), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
