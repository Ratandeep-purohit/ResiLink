import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-fallback-key')
    
    # Database selection
    USE_SQLITE = os.getenv('USE_SQLITE', 'True').lower() == 'true'
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'society.db')

    # MySQL Settings (for client/production)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'society_mgmt')
