import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# App Configuration
st.set_page_config(page_title="Pro SMA & Sentiment Dashboard", layout="wide")
st.title("📈 18/50 SMA + S/R + Trend Sentiment + Backtest")

# --- Sidebar Inputs ---
st.sidebar.header("Chart Settings")
ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()
period = st.sidebar.selectbox("History", ["1mo", "6mo", "1y", "2y", "5y", "max"], index=2)

interval_mapping = {
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "1 Day": "1d",
    "1 Week": "1wk"
}
interval_display = st.sidebar.selectbox("Interval", list(interval_mapping.keys()), index=2)
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
            # SMAs
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

            # Support & Resistance (Last 20 candles)
            df['Resistance'] = df['High'].rolling(window=20).max()
            df['Support'] = df['Low'].rolling(window=20).min()
            
            # Crossover Detection
            df['Signal'] = 0.0
            if len(df) > 50:
                df.loc[df.index[50:], 'Signal'] = np.where(df['SMA18'][50:] > df['SMA50'][50:], 1.0, 0.0)
                df['Position'] = df['Signal'].diff()
            else:
                df['Position'] = 0

            # --- 3. Trend Sentiment Logic ---
            curr_price = df['Close'].iloc[-1]
            curr_res = df['Resistance'].iloc[-1]
            curr_sup = df['Support'].iloc[-1]
            curr_18 = df['SMA18'].iloc[-1]
            curr_50 = df['SMA50'].iloc[-1]
            curr_rsi = df['RSI'].iloc[-1]

            # Logic Engine for Sentiment
            sentiment = ""
            if curr_18 > curr_50:
                if curr_price >= curr_res * 0.99:
                    sentiment = "🚀 BULLISH TREND - Approaching Resistance. (Wait for Breakout above ${:.2f})".format(curr_res)
                    st.info(sentiment)
                elif curr_price > curr_res:
                    sentiment = "🔥 BULLISH BREAKOUT - Clear Path Ahead!"
                    st.success(sentiment)
                else:
                    sentiment = "✅ BULLISH TREND - Price is healthy."
                    st.success(sentiment)
            else:
                if curr_price <= curr_sup * 1.01:
                    sentiment = "⚠️ BEARISH TREND - Near Support. (Watch for Bounce at ${:.2f})".format(curr_sup)
                    st.warning(sentiment)
                else:
                    sentiment = "📉 BEARISH TREND - Downward momentum is dominant."
                    st.error(sentiment)

            # --- 4. Backtesting Engine ---
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

            # --- 5. Plotting ---
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, 
                subplot_titles=(f'{ticker} Price Action', 'Volume', "Wilder's RSI"), 
                row_width=[0.2, 0.2, 0.6] 
            )

            # Row 1: Candlesticks & SMAs
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                          low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA18'], line=dict(color='orange', width=2), name='18 SMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='cyan', width=2), name='50 SMA'), row=1, col=1)

            # S/R Lines on Chart
            fig.add_hline(y=curr_res, line_dash="dot", line_color="red", row=1, col=1, annotation_text="Res")
            fig.add_hline(y=curr_sup, line_dash="dot", line_color="green", row=1, col=1, annotation_text="Sup")

            # Buy/Sell Markers
            buy_pts = df[df['Position'] == 1]
            fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['SMA18'], mode='markers',
                marker=dict(symbol='triangle-up', size=15, color='lime'), name='BUY'), row=1, col=1)
            sell_pts = df[df['Position'] == -1]
            fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['SMA18'], mode='markers',
                marker=dict(symbol='triangle-down', size=15, color='red'), name='SELL'), row=1, col=1)

            # Row 2: Volume
            vol_colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Vol_Avg'], line=dict(color='yellow', width=1.5), name='Vol 20-MA'), row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=2), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(template="plotly_dark", height=950, xaxis_rangeslider_visible=False, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # --- 6. Backtest Results Display ---
            st.divider()
            st.header("📊 Backtest Performance (Strategy vs History)")
            
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
                st.warning("No completed trades found. Try increasing 'History' to find more crossover events.")

            # --- 7. Sidebar Analytics ---
            st.sidebar.divider()
            st.sidebar.subheader("Live Metrics")
            st.sidebar.metric("Current Price", f"${curr_price:.2f}")
            st.sidebar.metric("Resistance (Ceiling)", f"${curr_res:.2f}")
            st.sidebar.metric("Support (Floor)", f"${curr_sup:.2f}")
            st.sidebar.metric("RSI Level", f"{curr_rsi:.1f}")
            st.sidebar.write(f"**Market Status:** {sentiment}")

    except Exception as e:
        st.error(f"Error: {e}")
