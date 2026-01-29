import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Custom Trend Dashboard", layout="wide")
st.title("📈 Advanced Stock Analysis Dashboard")

# --- Sidebar - User Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

# Flexible SMA Sliders
sma_short_len = st.sidebar.slider("Short SMA Length", 5, 30, 18)
sma_long_len = st.sidebar.slider("Long SMA Length", 30, 200, 40) # Set to 40 as per your request

period = st.sidebar.selectbox("History (Period)", ["1d", "5d", "1mo", "6mo", "1y", "2y", "5y"], index=3)
interval = st.sidebar.selectbox("Candle Interval", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"], index=5)

if ticker:
    try:
        # 1. Fetch Data
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        
        if data.empty:
            st.warning(f"No data found for {ticker}.")
        else:
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA_S'] = df['Close'].rolling(window=sma_short_len).mean()
            df['SMA_L'] = df['Close'].rolling(window=sma_long_len).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Trend Alert
            last_s = df['SMA_S'].iloc[-1]
            last_l = df['SMA_L'].iloc[-1]
            if last_s > last_l:
                st.success(f"**BULLISH:** {sma_short_len} SMA is above {sma_long_len} SMA.")
            else:
                st.error(f"**BEARISH:** {sma_short_len} SMA is below {sma_long_len} SMA.")

            # --- 3. Plotting with Custom Hover ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.05, 
                subplot_titles=(f'{ticker} Price', 'Volume', 'RSI'), 
                row_width=[0.2, 0.2, 0.6]
            )

            # Row 1: Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], 
                low=df['Low'], close=df['Close'], name='Price'
            ), row=1, col=1)

            # Row 1: SMA Short with Price in Hover
            fig.add_trace(go.Scatter(
                x=df.index, y=df['SMA_S'], 
                line=dict(color='orange', width=2), 
                name=f'{sma_short_len} SMA',
                customdata=df['Close'], # Injecting stock price here
                hovertemplate="<b>Price: $%{customdata:.2f}</b><br>SMA: $%{y:.2f}<extra></extra>"
            ), row=1, col=1)

            # Row 1: SMA Long with Price in Hover
            fig.add_trace(go.Scatter(
                x=df.index, y=df['SMA_L'], 
                line=dict(color='cyan', width=2), 
                name=f'{sma_long_len} SMA',
                customdata=df['Close'], # Injecting stock price here
                hovertemplate="<b>Price: $%{customdata:.2f}</b><br>SMA: $%{y:.2f}<extra></extra>"
            ), row=1, col=1)

            # Row 2: Volume
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='gray', opacity=0.5), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            # Layout - We use 'x' hovermode to see everything at once
            fig.update_layout(
                template="plotly_dark", 
                height=800, 
                xaxis_rangeslider_visible=False,
                hovermode='x unified' # This shows a vertical line and combined hover data
            )
            
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
