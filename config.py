from dotenv import load_dotenv
from pathlib import Path
import os

dotenv_path = Path(__file__).parent / ".env"

load_dotenv(dotenv_path=dotenv_path)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

API_URL = os.getenv("API_URL")
USERNAME = os.getenv("PANEL_USERNAME")
PASSWORD = os.getenv("PASSWORD")
YOOKASSA_ACCOUNT_ID = os.getenv("YOOKASSA_ACCOUNT_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
