from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import ta
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import uvicorn
import time
import logging

# Import curl_cffi for yfinance sessions
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    import requests as curl_requests
    CURL_CFFI_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FinDash API", description="Financial Dashboard API", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a session with better headers for yfinance
def create_yf_session():
    if CURL_CFFI_AVAILABLE:
        session = curl_requests.Session(impersonate="chrome120")
        logger.info("Using curl_cffi session for yfinance")
    else:
        session = curl_requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        logger.info("Using regular requests session for yfinance")
    return session

# Pydantic models for request/response  
class StockDataRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    sma_short: int = 20
    sma_long: int = 50

class PriceDataPoint(BaseModel):
    date: str
    price: float
    smaShort: float
    smaLong: float
    volume: int
    signal: Optional[int] = None

class PerformanceMetrics(BaseModel):
    strategyReturn: float
    buyHoldReturn: float
    totalTrades: int
    maxDrawdown: float
    sharpeRatio: float
    winRate: float
    volatility: float
    alpha: float

class Trade(BaseModel):
    id: int
    date: str
    action: str
    price: float
    shares: int
    value: float
    pnl: Optional[float] = None

class TechnicalIndicator(BaseModel):
    date: str
    value: float

def fetch_stock_data_robust(ticker: str, start_date: str, end_date: str, max_retries: int = 3):
    """
    Robust stock data fetching with curl_cffi session handling
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to fetch {ticker} data (attempt {attempt + 1}/{max_retries})")
            
            # Create session and ticker object
            session = create_yf_session()
            stock = yf.Ticker(ticker, session=session)
            
            # Try different methods to fetch data
            methods = [
                # Method 1: Using ticker.history with session - most reliable in new version
                lambda: stock.history(start=start_date, end=end_date, auto_adjust=True, prepost=False),
                # Method 2: Try with different period format
                lambda: stock.history(period="1y", auto_adjust=True).loc[start_date:end_date] if start_date and end_date else stock.history(period="1y", auto_adjust=True),
                # Method 3: Simple period fallback
                lambda: stock.history(period="6mo", auto_adjust=True)
            ]
            
            for i, method in enumerate(methods):
                try:
                    logger.info(f"Trying method {i + 1} for {ticker}")
                    data = method()
                    
                    if data is not None and not data.empty and len(data) > 0:
                        # Ensure we have the required columns
                        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        if all(col in data.columns for col in required_columns):
                            # Filter to requested date range if possible
                            if start_date and end_date and not data.empty:
                                try:
                                    data = data.loc[start_date:end_date]
                                except Exception as filter_error:
                                    logger.warning(f"Date filtering failed: {filter_error}")
                                    # Keep all data if filtering fails
                                
                            if len(data) > 10:  # Ensure we have enough data points
                                logger.info(f"Successfully fetched {len(data)} records for {ticker}")
                                return data
                            else:
                                logger.warning(f"Insufficient data points ({len(data)}) for {ticker}")
                                continue
                        else:
                            logger.warning(f"Missing required columns in data for {ticker}")
                            continue
                    else:
                        logger.warning(f"Empty data returned for {ticker} using method {i + 1}")
                        continue
                        
                except Exception as method_error:
                    logger.warning(f"Method {i + 1} failed for {ticker}: {str(method_error)}")
                    continue
            
            # If all methods failed, wait before retry
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # Exponential backoff
                logger.info(f"All methods failed, waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(3)
            continue
    
    # If all retries failed, raise an exception with helpful suggestions
    popular_symbols = ["MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META", "BRK-B", "JNJ", "V", "PG"]
    suggestion = f"Try these popular symbols: {', '.join(popular_symbols)}"
    
    raise HTTPException(
        status_code=404, 
        detail=f"Unable to fetch data for ticker '{ticker}'. This could be due to: 1) Invalid symbol, 2) Market holiday, 3) Recently delisted stock, or 4) Yahoo Finance temporary issues. {suggestion}"
    )

def fetch_and_process_data(ticker: str, start_date: str, end_date: str, sma_short: int, sma_long: int):
    """Fetch stock data and calculate all indicators with robust error handling"""
    try:
        # Validate inputs
        if not ticker or len(ticker.strip()) == 0:
            raise HTTPException(status_code=400, detail="Ticker symbol is required")
        
        ticker = ticker.upper().strip()
        
        # Validate dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt >= end_dt:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Fetch data using robust method
        data = fetch_stock_data_robust(ticker, start_date, end_date)
        
        min_required_days = max(sma_short, sma_long) + 10
        if data.empty or len(data) < min_required_days:
            raise HTTPException(
                status_code=404, 
                detail=f"Insufficient data for {ticker}. Need at least {min_required_days} trading days for analysis. Try different dates or check if the symbol is correct."
            )
        
        # Calculate Moving Averages with sufficient periods
        data["SMA_Short"] = data["Close"].rolling(window=sma_short, min_periods=sma_short).mean()
        data["SMA_Long"] = data["Close"].rolling(window=sma_long, min_periods=sma_long).mean()
        
        # Calculate Bollinger Bands with error handling
        try:
            bb = ta.volatility.BollingerBands(close=data["Close"], window=20, window_dev=2)
            data["BB_High"] = bb.bollinger_hband()
            data["BB_Low"] = bb.bollinger_lband()  
            data["BB_Mid"] = bb.bollinger_mavg()
        except Exception as e:
            logger.warning(f"Failed to calculate Bollinger Bands: {e}")
            # Use simple moving average as fallback
            data["BB_Mid"] = data["Close"].rolling(window=20, min_periods=20).mean()
            std_dev = data["Close"].rolling(window=20, min_periods=20).std()
            data["BB_High"] = data["BB_Mid"] + (2 * std_dev)
            data["BB_Low"] = data["BB_Mid"] - (2 * std_dev)
        
        # Calculate RSI with error handling
        try:
            rsi_indicator = ta.momentum.RSIIndicator(close=data["Close"], window=14)
            data["RSI"] = rsi_indicator.rsi()
        except Exception as e:
            logger.warning(f"Failed to calculate RSI: {e}")
            data["RSI"] = 50.0  # Neutral RSI as fallback
        
        # Calculate MACD with error handling
        try:
            macd_indicator = ta.trend.MACD(close=data["Close"])
            data["MACD"] = macd_indicator.macd()
            data["MACD_Signal"] = macd_indicator.macd_signal()
            data["MACD_Histogram"] = macd_indicator.macd_diff()
        except Exception as e:
            logger.warning(f"Failed to calculate MACD: {e}")
            # Simple MACD calculation as fallback
            ema12 = data["Close"].ewm(span=12, min_periods=12).mean()
            ema26 = data["Close"].ewm(span=26, min_periods=26).mean()
            data["MACD"] = ema12 - ema26
            data["MACD_Signal"] = data["MACD"].ewm(span=9, min_periods=9).mean()
            data["MACD_Histogram"] = data["MACD"] - data["MACD_Signal"]
        
        # Generate Buy/Sell Signals
        data["Signal"] = 0
        valid_data = data.dropna(subset=["SMA_Short", "SMA_Long"])
        if not valid_data.empty:
            data.loc[data["SMA_Short"] > data["SMA_Long"], "Signal"] = 1
            data.loc[data["SMA_Short"] < data["SMA_Long"], "Signal"] = -1
        
        # Shift signals to simulate trade execution on next day
        data["Position"] = data["Signal"].shift(1)
        
        # Calculate daily returns
        data["Daily_Return"] = data["Close"].pct_change()
        
        # Strategy return: position * daily return
        data["Strategy_Return"] = data["Position"] * data["Daily_Return"]
        
        logger.info(f"Successfully processed {len(data)} records for {ticker}")
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing data for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "FinDash API is running", 
        "status": "healthy", 
        "version": "2.0.0",
        "curl_cffi_available": CURL_CFFI_AVAILABLE
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/stock/price-data", response_model=List[PriceDataPoint])
async def get_price_data(request: StockDataRequest):
    """Get stock price data with moving averages"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        price_data = []
        for index, row in data.iterrows():
            if pd.notna(row["SMA_Short"]) and pd.notna(row["SMA_Long"]):
                price_data.append(PriceDataPoint(
                    date=index.strftime("%Y-%m-%d"),
                    price=round(float(row["Close"]), 2),
                    smaShort=round(float(row["SMA_Short"]), 2),
                    smaLong=round(float(row["SMA_Long"]), 2),
                    volume=int(row["Volume"]) if pd.notna(row["Volume"]) and row["Volume"] > 0 else 0,
                    signal=int(row["Signal"]) if pd.notna(row["Signal"]) else None
                ))
        
        if not price_data:
            raise HTTPException(status_code=404, detail="No valid price data found after processing")
        
        return price_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_price_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/stock/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(request: StockDataRequest):
    """Get strategy performance metrics"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        # Calculate cumulative returns with safety checks
        strategy_returns = data["Strategy_Return"].fillna(0)
        daily_returns = data["Daily_Return"].fillna(0)
        
        cumulative_strategy_return = (1 + strategy_returns).cumprod() - 1
        cumulative_stock_return = (1 + daily_returns).cumprod() - 1
        
        # Count trades
        position_changes = data["Position"].diff().abs()
        num_trades = (position_changes == 2).sum()
        
        # Calculate Max Drawdown
        cumulative_returns = (1 + strategy_returns).cumprod()
        rolling_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min() if not drawdown.empty else 0
        
        # Calculate Sharpe Ratio with safety checks
        strategy_std = strategy_returns.std()
        sharpe_ratio = 0
        if strategy_std != 0 and not pd.isna(strategy_std):
            sharpe_ratio = (strategy_returns.mean() / strategy_std) * (252**0.5)
        
        # Calculate Win Rate
        profitable_trades = (strategy_returns > 0).sum()
        total_trades_for_winrate = (strategy_returns != 0).sum()
        win_rate = (profitable_trades / total_trades_for_winrate * 100) if total_trades_for_winrate > 0 else 0
        
        # Calculate volatility (annualized)
        volatility = strategy_std * (252**0.5) * 100 if not pd.isna(strategy_std) else 0
        
        # Calculate Alpha (simplified as excess return over benchmark)
        strategy_final_return = cumulative_strategy_return.iloc[-1] * 100 if not cumulative_strategy_return.empty else 0
        benchmark_final_return = cumulative_stock_return.iloc[-1] * 100 if not cumulative_stock_return.empty else 0
        alpha = strategy_final_return - benchmark_final_return
        
        return PerformanceMetrics(
            strategyReturn=round(float(strategy_final_return), 2),
            buyHoldReturn=round(float(benchmark_final_return), 2),
            totalTrades=int(num_trades),
            maxDrawdown=round(float(max_drawdown * 100), 2),
            sharpeRatio=round(float(sharpe_ratio), 2),
            winRate=round(float(win_rate), 2),
            volatility=round(float(volatility), 2),
            alpha=round(float(alpha), 2)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_performance_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/stock/trades", response_model=List[Trade])
async def get_trade_log(request: StockDataRequest):
    """Get trade log with buy/sell signals"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        # Create trade log DataFrame
        position_changes = data["Position"].diff().abs()
        trades_mask = position_changes == 2
        trades_data = data[trades_mask].copy()
        
        if trades_data.empty:
            return []
        
        trades = []
        for i, (index, row) in enumerate(trades_data.iterrows()):
            action = "Buy" if row["Position"] == 1 else "Sell"
            shares = 100  # Fixed shares for demo
            price = float(row["Close"])
            value = price * shares
            
            # Calculate P&L for sell orders (simplified)
            pnl = None
            if action == "Sell" and i > 0:
                # Find the last buy price
                prev_buys = trades_data.iloc[:i]
                prev_buys = prev_buys[prev_buys["Position"] == 1]
                if not prev_buys.empty:
                    last_buy_price = float(prev_buys.iloc[-1]["Close"])
                    pnl = (price - last_buy_price) * shares
            
            trades.append(Trade(
                id=i + 1,
                date=index.strftime("%Y-%m-%d"),
                action=action,
                price=round(price, 2),
                shares=shares,
                value=round(value, 2),
                pnl=round(pnl, 2) if pnl is not None else None
            ))
        
        return trades
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_trade_log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/stock/rsi", response_model=List[TechnicalIndicator])
async def get_rsi_data(request: StockDataRequest):
    """Get RSI indicator data"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        rsi_data = []
        for index, row in data.iterrows():
            if pd.notna(row["RSI"]):
                rsi_data.append(TechnicalIndicator(
                    date=index.strftime("%Y-%m-%d"),
                    value=round(float(row["RSI"]), 2)
                ))
        
        return rsi_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_rsi_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/stock/macd")
async def get_macd_data(request: StockDataRequest):
    """Get MACD indicator data"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        macd_data = []
        for index, row in data.iterrows():
            if pd.notna(row["MACD"]) and pd.notna(row["MACD_Signal"]):
                macd_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "macd": round(float(row["MACD"]), 4),
                    "signal": round(float(row["MACD_Signal"]), 4),
                    "histogram": round(float(row["MACD_Histogram"]), 4) if pd.notna(row["MACD_Histogram"]) else 0
                })
        
        return macd_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_macd_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/stock/bollinger")
async def get_bollinger_data(request: StockDataRequest):
    """Get Bollinger Bands data"""
    try:
        data = fetch_and_process_data(
            request.ticker, 
            request.start_date, 
            request.end_date, 
            request.sma_short, 
            request.sma_long
        )
        
        bollinger_data = []
        for index, row in data.iterrows():
            if pd.notna(row["BB_High"]) and pd.notna(row["BB_Low"]):
                bollinger_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "price": round(float(row["Close"]), 2),
                    "upper": round(float(row["BB_High"]), 2),
                    "middle": round(float(row["BB_Mid"]), 2),
                    "lower": round(float(row["BB_Low"]), 2)
                })
        
        return bollinger_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bollinger_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 