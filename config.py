import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "trading-tracker-v5-topstep")
    SQLALCHEMY_DATABASE_URI = os.environ.get("TRACKER_DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'trades.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
