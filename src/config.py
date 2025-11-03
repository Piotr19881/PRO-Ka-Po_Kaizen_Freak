"""
Configuration file for PRO-Ka-Po Application
Environment variables and settings
"""
import os
from pathlib import Path

# ==================== API ENDPOINTS ====================

# Pomodoro API Base URL
# Development: http://127.0.0.1:8000
# Production: https://pro-ka-po-backend.onrender.com
POMODORO_API_BASE_URL = os.getenv(
    'POMODORO_API_URL',
    'http://127.0.0.1:8000'  # Default: localhost dla developmentu
)

# ==================== DATABASE PATHS ====================

# Local SQLite databases directory
LOCAL_DB_DIR = Path.home() / '.pro_ka_po'
LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)

# Pomodoro local database
POMODORO_LOCAL_DB_PATH = LOCAL_DB_DIR / 'pomodoro.db'

# ==================== SYNC SETTINGS ====================

# Auto-sync interval (seconds)
POMODORO_AUTO_SYNC_INTERVAL = int(os.getenv('POMODORO_SYNC_INTERVAL', '300'))  # 5 minutes

# ==================== LOGGING ====================

# Log level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Log file path
LOG_FILE_PATH = LOCAL_DB_DIR / 'app.log'
