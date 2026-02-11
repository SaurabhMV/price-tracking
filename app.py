import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Pro SMA & S/R Dashboard", layout="wide")
st.title("📈 18/50 SMA Strategy + S/R Levels + Wilder's RSI")

# --- Sidebar Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

# Period options
period = st.sidebar.selectbox("History", ["1d", "5d", "1mo", "6mo", "1y", "2y", "5y", "max"], index=4)

# Interval options
interval_mapping = {
    "5 Minutes": "5m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "1 Day": "1d",
    "1 Week": "1wk"
}
interval_display = st.sidebar.selectbox("Interval", list(interval_mapping.keys()), index=4)
selected_interval = interval_mapping[interval_display]

if ticker:
    try:
        # 1. Fetch Data
        df = yf.download(ticker, period=period, interval=selected_interval, auto_adjust=True)
        
        if df.empty:
            st.error(f"No data found for {ticker}. Try a shorter history for minute intervals.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            # Moving Averages
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            
            # Volume Moving Average
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            # --- Wilder's RSI ---
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.ewm(com=13, adjust=False, min_periods=14).mean()
            avg_loss = loss.ewm(com=13, adjust=False, min_periods=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # --- Support & Resistance (Recent Window) ---
            # We look at the last 20 periods to find local peaks/valleys
            df['Resistance'] = df['High'].rolling(window=20).max()
            df['Support'] = df['Low'].rolling(window=20).min()
            
            current_res = df['Resistance'].iloc[-1]
            current_sup = df['Support'].iloc[-1]

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
                subplot_titles=(f'{ticker} Price Action', 'Volume & 20-MA', "Wilder's RSI"), 
                row_width=[0.2, 0.2, 0.6] 
            )

            # Row 1: Candlesticks & SMAs
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], 
                low=df['Low'], close=df['Close'], name='Market'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=2), name='50 SMA'), row=1, col=1)

            # Support & Resistance Lines (Dashed)
            fig.add_hline(y=current_res, line_dash="dot", line_color="red", line_width=1, 
                          annotation_text=f"Resistance: ${current_res:.2f}", row=1, col=1)
            fig.add_hline(y=current_sup, line_dash="dot", line_color="green", line_width=1, 
                          annotation_text=f"Support: ${current_sup:.2f}", row=1, col=1)

            # Buy/Sell Markers
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-up', size=15, color='lime'),
                name='BUY', text=["BUY"] * len(buy_pts), textposition="bottom center"), row=1, col=1)

            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-down', size=15, color='red'),
                name='SELL', text=["SELL"] * len(sell_pts), textposition="top center"), row=1, col=1)

            # Row 2: Volume
            vol_colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=vol_colors, showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Vol_Avg'], line=dict(color='yellow', width=1.5), name='Vol 20-MA'), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(template="plotly_dark", height=950, xaxis_rangeslider_visible=False, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # Sidebar Live Metrics
            st.sidebar.divider()
            st.sidebar.metric("Last Close", f"${df['Close'].iloc[-1]:.2f}")
            st.sidebar.metric("Immediate Resistance", f"${current_res:.2f}")
            st.sidebar.metric("Immediate Support", f"${current_sup:.2f}")
            st.sidebar.metric("RSI (Wilder)", f"{df['RSI'].iloc[-1]:.1f}")

    except Exception as e:
        st.error(f"Error: {e}")
