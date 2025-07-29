# FinDash 📉 | Stock Strategy Analysis & Backtesting Dashboard

> A lightweight, interactive trading strategy dashboard powered by Python 🐍, Streamlit 🚀, and TA-Lib 📊. Visualize moving averages, RSI, MACD, Bollinger Bands, and more — all in one sleek UI.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.47.1-FF4B4B?logo=streamlit&logoColor=white)
![yFinance](https://img.shields.io/badge/yFinance-live%20data-green)
![TA-Lib](https://img.shields.io/badge/Technical%20Indicators-TA%20Lib-blueviolet)

---

## 🚀 Overview

**FinDash** is a fintech-focused web dashboard designed to test and visualize stock trading strategies based on technical indicators.

It enables users to:

- Analyze stock data using custom date ranges & MA periods  
- View crossover signals (Buy/Sell) with clear chart markers  
- Explore performance metrics like Sharpe Ratio & Max Drawdown  
- Visualize RSI, MACD, and Bollinger Bands interactively  
- Download trade logs directly from the dashboard

---



## 🔧 Features Overview

### 📌 App Interface and Inputs
![App title and inputs](./screenshots/App%20title%20and%20inputs.png)

- Select a stock (via Yahoo Finance)
- Choose the date range
- Adjust short/long SMA periods interactively

### 📈 Stock Price with SMA Crossover
![Input graph](./screenshots/Input%20graph.png)

- Closing price plot
- Buy/sell signals
- SMA overlays

### 📊 Strategy Metrics Summary
![Metrics](./screenshots/Metrics.png)

- Strategy vs. Buy & Hold return
- Trade count
- Sharpe Ratio & Max Drawdown

### 📉 Strategy Summary with RSI
![Strategy summary and RSI](./screenshots/Strategy%20summary%20and%20RSI.png)

- RSI (14) with overbought/oversold zones
- Helps fine-tune entry/exit points

### 📑 Trade Log Table
![Trade Log](./screenshots/Trade%20Log.png)

- Chronological buy/sell trades
- Downloadable CSV for further analysis

### 🔁 Cumulative Returns Comparison
![Cumulative Returns Comparison](./screenshots/Cumulative%20Returns%20Comparison.png)

- Strategy performance vs. holding the stock
- Helps visualize long-term efficiency

---

💡 What I Learned
This project helped me dive deep into:

Financial data manipulation using Pandas

Strategy logic using moving averages

Visual analysis via Matplotlib & Streamlit

Indicator overlays using the ta technical analysis library

Building real-world fintech dashboards from scratch

🤝 Connect
Made with ❤️ by Udit Pandey  
[Connect on LinkedIn](https://www.linkedin.com/in/uditpandeyy) ・ [Raise an Issue](https://github.com/uditpandeyy/Fintech-proj/issues)

