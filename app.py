import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Pro SMA & Volume Dashboard", layout="wide")
st.title("📈 18 vs 50 SMA Strategy with Volume & RSI")

# --- Sidebar Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()
period = st.sidebar.selectbox("History", ["1mo", "6mo", "1y", "2y", "5y", "max"], index=2)
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

            # --- 3. Plotting ---
            # Define a 3-row layout: Price (60%), Volume (20%), RSI (20%)
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, 
                subplot_titles=(f'{ticker} Price & SMAs', 'Volume', 'RSI Momentum'), 
                row_width=[0.2, 0.2, 0.6] 
            )

            # Row 1: Candlestick chart
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), 
                                     name='18 SMA', customdata=df['Close'],
                                     hovertemplate="Price: $%{customdata:.2f}<br>18 SMA: %{y:.2f}"), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=2), 
                                     name='50 SMA', customdata=df['Close'],
                                     hovertemplate="Price: $%{customdata:.2f}<br>50 SMA: %{y:.2f}"), row=1, col=1)

            # Buy/Sell Markers
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-up', size=14, color='lime'),
                name='BUY', text=["BUY"] * len(buy_pts), textposition="bottom center"), row=1, col=1)

            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['SMA18'], mode='markers+text',
                marker=dict(symbol='triangle-down', size=14, color='red'),
                name='SELL', text=["SELL"] * len(sell_pts), textposition="top center"), row=1, col=1)

            # Row 2: Volume Bars
            # Color bars: Green if Close > Open, else Red
            vol_colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', 
                                 marker_color=vol_colors, showlegend=False), row=2, col=1)

            # Row 3: RSI Subplot
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            # Layout Styling
            fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False, hovermode='x unified')
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            fig.update_yaxes(title_text="RSI", row=3, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # Quick Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Price", f"${df['Close'].iloc[-1]:.2f}")
            m2.metric("SMA 18/50 Gap", f"${(df['SMA18'].iloc[-1] - df['SMA50'].iloc[-1]):.2f}")
            m3.metric("RSI Value", f"{df['RSI'].iloc[-1]:.1f}")

    except Exception as e:
        st.error(f"Error: {e}")
