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

# Habit Tracker API Base URL (używa tego samego backendu co Pomodoro)
HABIT_API_BASE_URL = os.getenv(
    'HABIT_API_URL',
    'http://127.0.0.1:8000'  # Default: localhost dla developmentu
)

# TeamWork API Base URL (używa tego samego backendu)
TEAMWORK_API_BASE_URL = os.getenv(
    'TEAMWORK_API_URL',
    'http://127.0.0.1:8000'  # Default: localhost dla developmentu
)

# General API Base URL (fallback dla innych modułów)
API_BASE_URL = os.getenv(
    'API_BASE_URL',
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

# ==================== AI SETTINGS ====================

# AI Provider API Keys (stored securely, preferably in environment variables)
AI_API_KEYS = {
    'gemini': os.getenv('GEMINI_API_KEY', ''),
    'openai': os.getenv('OPENAI_API_KEY', ''),
    'grok': os.getenv('GROK_API_KEY', ''),
    'claude': os.getenv('CLAUDE_API_KEY', ''),
    'deepseek': os.getenv('DEEPSEEK_API_KEY', '')
}

# Default AI Provider ('gemini', 'openai', 'grok', 'claude', 'deepseek')
AI_DEFAULT_PROVIDER = os.getenv('AI_DEFAULT_PROVIDER', 'gemini')

# Default AI Model (provider-specific)
AI_DEFAULT_MODEL = os.getenv('AI_DEFAULT_MODEL', '')  # Empty = provider default

# AI Response Cache Directory
AI_CACHE_DIR = LOCAL_DB_DIR / 'ai_cache'
AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# AI Settings File (stores user preferences)
AI_SETTINGS_FILE = LOCAL_DB_DIR / 'ai_settings.json'

# AI Temperature (0.0 - 1.0, controls randomness)
AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.7'))

# AI Max Tokens (max response length, None = provider default)
AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '2048')) if os.getenv('AI_MAX_TOKENS') else None

# AI Request Timeout (seconds)
AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '30'))
