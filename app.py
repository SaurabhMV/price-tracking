import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="SMA Crossover Signals", layout="wide")
st.title("📈 18 vs 40 SMA Strategy Dashboard")

# --- Sidebar Inputs ---
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()
period = st.sidebar.selectbox("History", ["1mo", "6mo", "1y", "2y", "5y"], index=2)
interval = st.sidebar.selectbox("Interval", ["1h", "1d", "1wk"], index=1)

if ticker:
    try:
        # 1. Fetch and Clean Data
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        if df.empty:
            st.error("No data found.")
        else:
            # Flatten MultiIndex if necessary
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA40'] = df['Close'].rolling(window=40).mean()
            
            # Identify Crossover Points
            # 1 when 18 > 40, else 0
            df['Signal'] = 0.0
            df.loc[df.index[18:], 'Signal'] = np.where(df['SMA18'][18:] > df['SMA40'][18:], 1.0, 0.0)
            
            # Create 'Position' to find where Signal changes
            # 1.0 is Buy (cross up), -1.0 is Sell (cross down)
            df['Position'] = df['Signal'].diff()

            # RSI for extra context
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # --- 3. UI Indicators ---
            last_pos = df['Position'].iloc[-1]
            current_trend = "Bullish" if df['SMA18'].iloc[-1] > df['SMA40'].iloc[-1] else "Bearish"
            
            col1, col2 = st.columns(2)
            with col1:
                if current_trend == "Bullish":
                    st.success(f"Current Trend: **BULLISH** (18 SMA > 40 SMA)")
                else:
                    st.error(f"Current Trend: **BEARISH** (18 SMA < 40 SMA)")
            
            # --- 4. Plotting ---
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, 
                vertical_spacing=0.08, 
                subplot_titles=(f'{ticker} Price Action & Signals', 'RSI Momentum'), 
                row_width=[0.3, 0.7]
            )

            # Price and SMAs
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), 
                                     name='18 SMA', hovertemplate="Price: $%{customdata:.2f}<br>18 SMA: %{y:.2f}",
                                     customdata=df['Close']), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA40'], line=dict(color='cyan', width=2), 
                                     name='40 SMA', hovertemplate="Price: $%{customdata:.2f}<br>40 SMA: %{y:.2f}",
                                     customdata=df['Close']), row=1, col=1)

            # Add BUY Markers (Where 18 crosses above 40)
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-up', size=15, color='lime'),
                name='BUY SIGNAL', text=["BUY"] * len(buy_pts), textposition="bottom center"
            ), row=1, col=1)

            # Add SELL Markers (Where 18 crosses below 40)
            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-down', size=15, color='red'),
                name='SELL SIGNAL', text=["SELL"] * len(sell_pts), textposition="top center"
            ), row=1, col=1)

            # RSI Row
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # Signal History Table
            st.subheader("Recent Trade Signals")
            signals_only = df[df['Position'] != 0][['Close', 'SMA18', 'SMA40', 'Position']].tail(10)
            if not signals_only.empty:
                signals_only['Action'] = signals_only['Position'].apply(lambda x: "BUY" if x > 0 else "SELL")
                st.table(signals_only[['Close', 'Action']])
            else:
                st.info("No crossover signals detected in this time period.")

    except Exception as e:
        st.error(f"Error: {e}")
