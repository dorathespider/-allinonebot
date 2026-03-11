import os
from dotenv import load_dotenv

if os.path.exists("config.env"):
    load_dotenv("config.env")
else:
    load_dotenv()

class Config:
    BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
    API_ID     = int(os.environ.get("API_ID", 0))
    API_HASH   = os.environ.get("API_HASH", "")
    OWNER_ID   = int(os.environ.get("OWNER_ID", 0))
    
    # Channel se forward krne pe auto add
    AUTH_CHANNEL = int(os.environ.get("AUTH_CHANNEL", 0))
    
    CREDIT        = os.environ.get("CREDIT", "AllInOneBot")
    THUMB_URL     = os.environ.get("THUMB_URL", "")
    MAX_VIDEO_SIZE_MB = int(os.environ.get("MAX_VIDEO_SIZE_MB", 1900))
    WORKERS       = int(os.environ.get("WORKERS", 1000))
    DOWNLOAD_PATH = os.environ.get("DOWNLOAD_PATH", "./downloads")
    
    # Platform tokens
    PW_TOKEN = os.environ.get("PW_TOKEN", "")
    CP_TOKEN = os.environ.get("CP_TOKEN", "")
    
    # AES for helper:// encrypted URLs
    AES_KEY = b'^#^#&@*HDU@&@*()'
    AES_IV  = b'^@%#&*NSHUE&$*#)'
    
    # Simple JSON file for users (no MongoDB)
    USERS_FILE = "users.json"
