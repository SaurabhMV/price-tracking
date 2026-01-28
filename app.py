import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Pro Trading Dashboard", layout="wide")
st.title("📊 Multi-Timeframe Trend Dashboard")

# Sidebar - User Inputs
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

# Period = How far back?
period_options = ["1d", "5d", "1mo", "6mo", "1y", "2y", "5y", "max"]
period = st.sidebar.selectbox("History (Period)", period_options, index=3)

# Interval = How big is one candle?
interval_options = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"]
interval = st.sidebar.selectbox("Candle Interval", interval_options, index=5)

if ticker:
    try:
        # 1. Fetch Data
        # We use group_by='ticker' and auto_adjust to keep columns clean
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        
        if data.empty:
            st.warning(f"No data found for {ticker} with Period: {period} and Interval: {interval}. Try a shorter period for intraday intervals.")
        else:
            df = data.copy()
            
            # FIX: If yfinance returns a MultiIndex (Price, Ticker), flatten it
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            
            # RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Signals
            df['Prev_18'] = df['SMA18'].shift(1)
            df['Prev_50'] = df['SMA50'].shift(1)
            buy_signals = df[(df['SMA18'] > df['SMA50']) & (df['Prev_18'] <= df['Prev_50'])]
            sell_signals = df[(df['SMA18'] < df['SMA50']) & (df['Prev_18'] >= df['Prev_50'])]

            # --- 3. Plotting ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.05, 
                subplot_titles=(f'{ticker} Price ({interval})', 'Volume', 'RSI'), 
                row_width=[0.2, 0.2, 0.6]
            )

            # Price & SMAs
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=1.5), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=1.5), name='50 SMA'), row=1, col=1)
            
            # Buy/Sell Markers
            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['SMA18'], mode='markers', 
                          marker=dict(symbol='triangle-up', size=12, color='lime'), name='Buy Signal'), row=1, col=1)
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['SMA18'], mode='markers', 
                          marker=dict(symbol='triangle-down', size=12, color='red'), name='Sell Signal'), row=1, col=1)

            # Volume
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='gray', opacity=0.5), row=2, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Last Close", f"{df['Close'].iloc[-1]:.2f}")
            c2.metric("RSI", f"{df['RSI'].iloc[-1]:.1f}")
            c3.metric("Signals Found", len(buy_signals) + len(sell_signals))

    except Exception as e:
        st.error(f"Error: {e}")
