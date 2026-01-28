import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Professional Trend Dashboard", layout="wide")
st.title("📊 Multi-Indicator Analysis Dashboard")

ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()
period = st.sidebar.selectbox("History", ["6mo", "1y", "2y"], index=0)

if ticker:
    try:
        # FIX: Use auto_adjust=True and handle the potential MultiIndex
        data = yf.download(ticker, period=period, auto_adjust=True)
        
        if data.empty:
            st.error("Invalid ticker or no data found.")
        else:
            # Create a copy to avoid SettingWithCopy warnings
            df = data.copy()

            # --- 1. Calculations ---
            # Moving Averages
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            
            # RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Signal Logic
            df['Prev_18'] = df['SMA18'].shift(1)
            df['Prev_50'] = df['SMA50'].shift(1)
            
            # Logic for Markers
            buy_signals = df[(df['SMA18'] > df['SMA50']) & (df['Prev_18'] <= df['Prev_50'])]
            sell_signals = df[(df['SMA18'] < df['SMA50']) & (df['Prev_18'] >= df['Prev_50'])]

            # --- 2. Create Subplots ---
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.05, 
                subplot_titles=(f'{ticker} Price', 'Volume', 'RSI'), 
                row_width=[0.2, 0.2, 0.6]
            )

            # Row 1: Price & SMAs
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange'), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan'), name='50 SMA'), row=1, col=1)
            
            # Markers
            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['SMA18'], mode='markers', 
                          marker=dict(symbol='triangle-up', size=12, color='lime'), name='Buy'), row=1, col=1)
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['SMA18'], mode='markers', 
                          marker=dict(symbol='triangle-down', size=12, color='red'), name='Sell'), row=1, col=1)

            # Row 2: Volume (using .squeeze() to ensure it's a 1D Series)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'].iloc[:,0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume'], 
                                 name='Volume', marker_color='gray'), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching data: {e}")
