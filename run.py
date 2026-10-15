"""
SecureBank Connect - Master Gateway Server Entrypoint
"""
import sys
import os
import signal
from http.server import ThreadingHTTPServer
from server.config import HOST, PORT
from server.database import init_db
from server.gateway import OpenBankGatewayHandler
from server.anomaly_detector import detector

def print_banner():
    banner = f"""
======================================================================
  ____                             ____              _    
 / ___|  ___  ___ _   _ _ __ ___  | __ )  __ _ _ __ | | __
 \___ \ / _ \/ __| | | | '__/ _ \ |  _ \ / _` | '_ \| |/ /
  ___) |  __/ (__| |_| | | |  __/ | |_) | (_| | | | |   < 
 |____/ \___|\___|\__,_|_|  \___| |____/ \__,_|_| |_|_|\_\\
                                                           
  CONNECT · One Secure Gateway. Smarter Banking Integrations.
======================================================================
  [✓] Database:       SQLite initialized with synthetic data
  [✓] AI Engine:      Scikit-Learn IsolationForest model trained
  [✓] Consent Engine: Active & Scoped Access Governance enabled
  [✓] Gateway Server: Running at http://{HOST}:{PORT}
  
  Developer Portal & Dashboard: http://{HOST}:{PORT}
  Press Ctrl+C to terminate the server.
======================================================================
"""
    print(banner)

def main():
    print("Initializing SecureBank Connect...")
    # 1. Initialize SQLite Database & Synthetic Data
    init_db()

    # 2. Initialize and Train AI Anomaly Detection Engine
    detector.train_baseline_model()

    # 3. Start Multi-threaded Gateway HTTP Server
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, OpenBankGatewayHandler)

    print_banner()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down SecureBank Connect Gateway gracefully...")
        httpd.server_close()
        sys.exit(0)

if __name__ == "__main__":
    main()
