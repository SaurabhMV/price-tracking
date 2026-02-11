import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Pro SMA & Backtest Dashboard", layout="wide")
st.title("📈 18/50 SMA Dashboard + Performance Backtest")

# --- Sidebar Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()
period = st.sidebar.selectbox("History", ["6mo", "1y", "2y", "5y", "max"], index=1)

interval_mapping = {"1 Hour": "1h", "1 Day": "1d", "1 Week": "1wk"}
interval_display = st.sidebar.selectbox("Interval", list(interval_mapping.keys()), index=1)
selected_interval = interval_mapping[interval_display]

if ticker:
    try:
        # 1. Fetch Data
        df = yf.download(ticker, period=period, interval=selected_interval, auto_adjust=True)
        
        if df.empty:
            st.error(f"No data found for {ticker}.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 2. Calculations ---
            df['SMA18'] = df['Close'].rolling(window=18).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            # Wilder's RSI
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.ewm(com=13, adjust=False, min_periods=14).mean()
            avg_loss = loss.ewm(com=13, adjust=False, min_periods=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # S/R Levels
            df['Resistance'] = df['High'].rolling(window=20).max()
            df['Support'] = df['Low'].rolling(window=20).min()
            
            # Crossover Signals
            df['Signal'] = 0.0
            if len(df) > 50:
                df.loc[df.index[50:], 'Signal'] = np.where(df['SMA18'][50:] > df['SMA50'][50:], 1.0, 0.0)
                df['Position'] = df['Signal'].diff()
            else:
                df['Position'] = 0

            # --- 3. Backtesting Logic ---
            trades = []
            buy_price = 0
            buy_date = None
            in_position = False

            for date, row in df.iterrows():
                if row['Position'] == 1: # Buy Signal
                    buy_price = row['Close']
                    buy_date = date
                    in_position = True
                elif row['Position'] == -1 and in_position: # Sell Signal
                    sell_price = row['Close']
                    profit = (sell_price - buy_price) / buy_price
                    trades.append({
                        'Buy Date': buy_date,
                        'Sell Date': date,
                        'Buy Price': buy_price,
                        'Sell Price': sell_price,
                        'Profit %': profit * 100
                    })
                    in_position = False

            trades_df = pd.DataFrame(trades)

            # --- 4. Plotting ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, 
                subplot_titles=(f'{ticker} Price', 'Volume', "Wilder's RSI"), 
                row_width=[0.2, 0.2, 0.6] 
            )

            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange'), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan'), name='50 SMA'), row=1, col=1)

            # Markers
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['SMA18'], mode='markers',
                marker=dict(symbol='triangle-up', size=15, color='lime'), name='BUY'), row=1, col=1)
            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['SMA18'], mode='markers',
                marker=dict(symbol='triangle-down', size=15, color='red'), name='SELL'), row=1, col=1)

            # Volume & RSI (Simplified Trace calls)
            vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name='RSI'), row=3, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- 5. Performance Summary UI ---
            st.header("📊 Strategy Performance Summary")
            
            if not trades_df.empty:
                col1, col2, col3, col4 = st.columns(4)
                total_ret = trades_df['Profit %'].sum()
                win_rate = (trades_df['Profit %'] > 0).mean() * 100
                
                col1.metric("Total Strategy Return", f"{total_ret:.2f}%")
                col2.metric("Win Rate", f"{win_rate:.1f}%")
                col3.metric("Total Trades", len(trades_df))
                col4.metric("Avg Profit/Trade", f"{trades_df['Profit %'].mean():.2f}%")

                st.subheader("📝 Trade Log")
                st.dataframe(trades_df.style.format({'Buy Price': '{:.2f}', 'Sell Price': '{:.2f}', 'Profit %': '{:.2f}%'}))
            else:
                st.write("No completed trades found for this period. Try a longer 'History' setting.")

    except Exception as e:
        st.error(f"Error: {e}")
