from waitress import serve
from app import app
import os

if __name__ == '__main__':
    print("🚀 Starting Production Server on Intel 120U Multi-Core Engine...")
    print("🌐 Running on http://127.0.0.1:5000 and accessible across local network")
    # threads=16 aapke 120U ke threads ke according peak performance dega
    serve(app, host='0.0.0.0', port=5000, threads=16, connection_limit=1000)