#!/usr/bin/env python3
"""
FinDash API Server Startup Script
"""

import uvicorn
import sys
import os

if __name__ == "__main__":
    print("🚀 Starting FinDash API Server...")
    print("📊 API will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔄 Interactive API: http://localhost:8000/redoc")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "api_backend:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down FinDash API Server...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1) 