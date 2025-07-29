#!/usr/bin/env python3
"""
Test script to verify yfinance connectivity
"""

import yfinance as yf
from datetime import datetime

# Import curl_cffi for yfinance sessions
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    import requests as curl_requests
    CURL_CFFI_AVAILABLE = False

def test_yfinance():
    print('🧪 Testing yfinance connection...')
    print(f'📦 curl_cffi available: {CURL_CFFI_AVAILABLE}')
    
    # Create session with proper headers
    if CURL_CFFI_AVAILABLE:
        session = curl_requests.Session(impersonate="chrome120")
        print('🔧 Using curl_cffi session')
    else:
        session = curl_requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        print('🔧 Using regular requests session')
    
    # Test with popular symbols
    symbols = ['MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN']
    successful_symbols = []
    
    for symbol in symbols:
        try:
            print(f'Testing {symbol}...', end=' ')
            stock = yf.Ticker(symbol, session=session)
            data = stock.history(period='5d', auto_adjust=True, prepost=False)
            
            if not data.empty and len(data) > 0:
                latest_price = data['Close'].iloc[-1]
                print(f'✅ Success! Got {len(data)} days of data')
                print(f'   Latest price: ${latest_price:.2f}')
                successful_symbols.append(symbol)
                break
            else:
                print('❌ No data')
        except Exception as e:
            print(f'❌ Error: {str(e)[:60]}...')
    
    if successful_symbols:
        print(f'\n🎉 yfinance is working! Successfully fetched data for: {", ".join(successful_symbols)}')
        print('✅ Ready to start the API server!')
        return True
    else:
        print('\n❌ Unable to fetch data from any symbols.')
        print('💡 Try: pip install --upgrade curl-cffi yfinance')
        return False

if __name__ == "__main__":
    test_yfinance() 