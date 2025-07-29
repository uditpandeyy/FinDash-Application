# filename: ma_strategy_app.py
import ta
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Page layout
st.set_page_config(layout="wide")
st.title("📈 Moving Average Crossover Strategy")

# User Inputs
ticker = st.text_input("Enter Stock Symbol", value="AAPL")
start_date = st.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("2023-01-01"))

# User-selected SMA periods
sma_short = st.slider("Short-Term SMA Period", min_value=5, max_value=50, value=20)
sma_long = st.slider("Long-Term SMA Period", min_value=10, max_value=200, value=50)

# Fetch Data
data = yf.download(ticker, start=start_date, end=end_date)
if data.empty:
    st.warning("No data found. Try a different symbol or date.")
    st.stop()

# Calculate Moving Averages
data["SMA_Short"] = data["Close"].rolling(window=sma_short).mean()
data["SMA_Long"] = data["Close"].rolling(window=sma_long).mean()
# Calculate Bollinger Bands
bb = ta.volatility.BollingerBands(close=data["Close"].squeeze(), window=20, window_dev=2)
data["BB_High"] = bb.bollinger_hband()
data["BB_Low"] = bb.bollinger_lband()

# Calculate RSI using 'ta' library
rsi_indicator = ta.momentum.RSIIndicator(close=data["Close"].squeeze(), window=14)
data["RSI"] = rsi_indicator.rsi()

# Calculate MACD
macd_indicator = ta.trend.MACD(close=data["Close"].squeeze())
data["MACD"] = macd_indicator.macd()
data["MACD_Signal"] = macd_indicator.macd_signal()

# Calculate Bollinger Bands using ta
bb = ta.volatility.BollingerBands(close=data["Close"].squeeze(), window=20, window_dev=2)
data["bb_bbm"] = bb.bollinger_mavg()
data["bb_bbh"] = bb.bollinger_hband()
data["bb_bbl"] = bb.bollinger_lband()

# Generate Buy/Sell Signals
data["Signal"] = 0
data.loc[data["SMA_Short"] > data["SMA_Long"], "Signal"] = 1
data.loc[data["SMA_Short"] < data["SMA_Long"], "Signal"] = -1

# Shift signals to simulate trade execution on next day
data["Position"] = data["Signal"].shift(1)

# Calculate daily returns
data["Daily Return"] = data["Close"].pct_change()

# Strategy return: position * daily return
data["Strategy Return"] = data["Position"] * data["Daily Return"]

# Cumulative returns
cumulative_strategy_return = (1 + data["Strategy Return"].fillna(0)).cumprod() - 1
cumulative_stock_return = (1 + data["Daily Return"].fillna(0)).cumprod() - 1

# Count trades
num_trades = (data["Position"].diff().abs() == 2).sum()


# Plotting
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(data["Close"], label="Close Price", alpha=0.5)
ax.plot(data["SMA_Short"], label=f"SMA{sma_short}", linestyle="--")
ax.plot(data["SMA_Long"], label=f"SMA{sma_long}", linestyle="--")


# Buy/Sell Markers
buy_signals = data[data["Signal"] == 1]
sell_signals = data[data["Signal"] == -1]
ax.scatter(buy_signals.index, buy_signals["Close"], label="Buy", marker="^", color="green")
ax.scatter(sell_signals.index, sell_signals["Close"], label="Sell", marker="v", color="red")

ax.plot(data["BB_High"], linestyle="--", color="gray", alpha=0.3, label="BB High")
ax.plot(data["BB_Low"], linestyle="--", color="gray", alpha=0.3, label="BB Low")
ax.set_title(f"{ticker} - MA Crossover Strategy")

# Display strategy performance
st.subheader("📊 Strategy Performance Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Strategy Return", f"{cumulative_strategy_return.iloc[-1]*100:.2f}%")
col2.metric("Buy & Hold Return", f"{cumulative_stock_return.iloc[-1]*100:.2f}%")
col3.metric("Trades Executed", f"{int(num_trades)}")
ax.legend()
st.pyplot(fig)

# Calculate Max Drawdown
cumulative_returns = (1 + data["Strategy Return"].fillna(0)).cumprod()
rolling_max = cumulative_returns.cummax()
drawdown = (cumulative_returns - rolling_max) / rolling_max
max_drawdown = drawdown.min()

# Calculate Sharpe Ratio
sharpe_ratio = (data["Strategy Return"].mean() / data["Strategy Return"].std()) * (252**0.5)  # Annualized

st.subheader("📋 Strategy Summary")
st.markdown(f"""
- **Ticker**: {ticker}  
- **Period**: {start_date} to {end_date}  
- **SMA Periods**: {sma_short} & {sma_long}  
- **Total Trades**: {int(num_trades)}  
- **Max Drawdown**: {max_drawdown * 100:.2f}%  
- **Sharpe Ratio**: {sharpe_ratio:.2f}
""")

# Plot RSI
fig2, ax2 = plt.subplots(figsize=(12, 3))
ax2.plot(data["RSI"], label="RSI", color="purple")
ax2.axhline(70, color="red", linestyle="--", alpha=0.5)
ax2.axhline(30, color="green", linestyle="--", alpha=0.5)
ax2.set_title("RSI (14)")
ax2.legend()
st.pyplot(fig2)


st.subheader("Performance Metrics")

col1, col2, col3 = st.columns(3)
col1.metric("Total Strategy Return", f"{cumulative_strategy_return.iloc[-1]*100:.2f}%")
col2.metric("Buy & Hold Return", f"{cumulative_stock_return.iloc[-1]*100:.2f}%")
col3.metric("Total Trades", int(num_trades))


# Display additional metrics
st.subheader("📌 Risk Metrics")
col4, col5 = st.columns(2)
col4.metric("Max Drawdown", f"{max_drawdown * 100:.2f}%")
col5.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

# Create trade log DataFrame
trades = data[data["Position"].diff().abs() == 2].copy()
trades["Action"] = trades["Position"].apply(lambda x: "Buy" if x == 1 else "Sell")
trade_log = trades[["Action", "Close"]]
trade_log["Date"] = trades.index
trade_log = trade_log[["Date", "Action", "Close"]].reset_index(drop=True)

# MACD Plot
st.subheader("📉 MACD Indicator")
fig2, ax2 = plt.subplots(figsize=(12, 4))
ax2.plot(data["MACD"], label="MACD", color="blue")
ax2.plot(data["MACD_Signal"], label="Signal Line", color="orange")
ax2.axhline(0, linestyle="--", color="gray", linewidth=1)
ax2.legend()
st.pyplot(fig2)

# RSI Plot
st.subheader("📉 RSI Indicator")
fig3, ax3 = plt.subplots(figsize=(12, 3))
ax3.plot(data["RSI"], label="RSI", color="purple")
ax3.axhline(70, color="red", linestyle="--", label="Overbought (70)")
ax3.axhline(30, color="green", linestyle="--", label="Oversold (30)")
ax3.set_ylim(0, 100)
ax3.legend()
st.pyplot(fig3)

# Bollinger Bands
st.subheader("📉 Bollinger Bands")
fig_bb, ax_bb = plt.subplots(figsize=(12, 4))
ax_bb.plot(data["Close"], label="Close Price", alpha=0.5)
ax_bb.plot(data["bb_bbm"], label="Middle Band", linestyle="--")
ax_bb.plot(data["bb_bbh"], label="Upper Band", linestyle="--")
ax_bb.plot(data["bb_bbl"], label="Lower Band", linestyle="--")
ax_bb.set_title("Bollinger Bands (20, 2)")
ax_bb.legend()
st.pyplot(fig_bb)


st.subheader("🧾 Trade Log")

action_filter = st.selectbox("Filter Trade Log by Action", ["All", "Buy", "Sell"])
filtered_log = trade_log if action_filter == "All" else trade_log[trade_log["Action"] == action_filter]

st.dataframe(filtered_log, use_container_width=True)


# Download trade log
csv = trade_log.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Trade Log as CSV",
    data=csv,
    file_name=f"{ticker}_trade_log.csv",
    mime='text/csv'
)
# Plot cumulative returns
st.subheader("📈 Cumulative Returns Comparison")
fig2, ax2 = plt.subplots(figsize=(12, 4))
ax2.plot(cumulative_strategy_return, label="Strategy Return", color="blue")
ax2.plot(cumulative_stock_return, label="Buy & Hold Return", color="orange")
ax2.set_title("Cumulative Returns Over Time")
ax2.set_ylabel("Cumulative Return")
ax2.legend()
st.pyplot(fig2)
