import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DATA_DIR = r"D:\TradingTrackerData" if getattr(sys, "frozen", False) else BASE_DIR
DATA_DIR = os.path.abspath(os.environ.get("TRACKER_DATA_DIR", DEFAULT_DATA_DIR))
os.makedirs(DATA_DIR, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "trading-tracker-v5-topstep")
    SQLALCHEMY_DATABASE_URI = os.environ.get("TRACKER_DATABASE_URL") or f"sqlite:///{os.path.join(DATA_DIR, 'trades.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    DATA_DIR = DATA_DIR
    UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
