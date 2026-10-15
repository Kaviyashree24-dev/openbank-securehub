"""
SecureBank Connect - Global Configuration
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "openbank.db"
STATIC_DIR = BASE_DIR / "static"

# Server configuration
HOST = "127.0.0.1"
PORT = 8000
DEBUG = True

# Security & Gateway
SECRET_KEY = os.environ.get("OPENBANK_SECRET_KEY", "securebank-open-api-secret-key-2026-xyz987")
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
DEFAULT_RATE_LIMIT = 60      # requests per minute

# Standard Open Banking Scopes
AVAILABLE_SCOPES = [
    "accounts:read",
    "balances:read",
    "transactions:read",
    "payments:create"
]

# AI Anomaly Detection Settings
ANOMALY_CONTAMINATION = 0.08  # Expected ~8% anomaly rate in training
ANOMALY_WINDOW_SECONDS = 60
BURST_THRESHOLD_RPS = 10      # requests per second from single client
ERROR_RATIO_ALERT = 0.35      # 35% error rate trigger
