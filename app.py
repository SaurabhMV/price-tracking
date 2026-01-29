import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="SMA 18/50 Trend Dashboard", layout="wide")
st.title("📈 18 vs 50 SMA Strategy Dashboard")

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
            st.error("No data found for this ticker.")
        else:
            # Flatten MultiIndex if yfinance returns it
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            
            # Crossover Detection (18 crossing 50)
            df['Signal'] = 0.0
            # Ensure we have enough data points before calculating crossover
            if len(df) > 50:
                df.loc[df.index[50:], 'Signal'] = np.where(df['SMA18'][50:] > df['SMA50'][50:], 1.0, 0.0)
                df['Position'] = df['Signal'].diff()
            else:
                df['Position'] = 0

            # RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # --- 3. Trend Status Alerts ---
            last_18 = df['SMA18'].iloc[-1]
            last_50 = df['SMA50'].iloc[-1]
            
            if not np.isnan(last_50):
                if last_18 > last_50:
                    st.success(f"**BULLISH TREND:** 18 SMA (${last_18:.2f}) is above 50 SMA (${last_50:.2f})")
                else:
                    st.error(f"**BEARISH TREND:** 18 SMA (${last_18:.2f}) is below 50 SMA (${last_50:.2f})")
            else:
                st.info("Insufficient data for 50 SMA calculation. Try a longer 'History' period.")

            # --- 4. Plotting ---
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, 
                vertical_spacing=0.08, 
                subplot_titles=(f'{ticker} Price Action & 18/50 Crossovers', 'RSI Momentum'), 
                row_width=[0.3, 0.7]
            )

            # Candlestick chart
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            
            # SMA 18 (Short Term)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), 
                                     name='18 SMA', customdata=df['Close'],
                                     hovertemplate="Price: $%{customdata:.2f}<br>18 SMA: %{y:.2f}"), row=1, col=1)
            
            # SMA 50 (Long Term)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=2), 
                                     name='50 SMA', customdata=df['Close'],
                                     hovertemplate="Price: $%{customdata:.2f}<br>50 SMA: %{y:.2f}"), row=1, col=1)

            # Buy/Sell Markers at Crossover
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-up', size=14, color='lime'),
                name='BUY', text=["BUY"] * len(buy_pts), textposition="bottom center"
            ), row=1, col=1)

            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-down', size=14, color='red'),
                name='SELL', text=["SELL"] * len(sell_pts), textposition="top center"
            ), row=1, col=1)

            # RSI Subplot
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # Signal Log
            with st.expander("View Recent Signal History"):
                history = df[df['Position'] != 0][['Close', 'SMA18', 'SMA50', 'Position']].tail(10)
                if not history.empty:
                    history['Action'] = history['Position'].apply(lambda x: "BUY" if x > 0 else "SELL")
                    st.dataframe(history[['Close', 'Action']], use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
