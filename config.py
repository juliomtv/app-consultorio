import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-2024")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB upload limit

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DOCUMENTS_FOLDER = os.path.join(BASE_DIR, "uploads", "documents")
    LIBRARY_FOLDER = os.path.join(BASE_DIR, "uploads", "library")
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
    ALLOWED_LIBRARY_EXTENSIONS = {"pdf", "epub"}

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@consultorio.com")

    CLINIC_NAME = os.environ.get("CLINIC_NAME", "Consultório")
    CLINIC_PHONE = os.environ.get("CLINIC_PHONE", "")
    CLINIC_WHATSAPP = os.environ.get("CLINIC_WHATSAPP", "")

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@consultorio.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@2024!")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database', 'consultorio.db')}"
    )


class ProductionConfig(Config):
    DEBUG = False
    # PostgreSQL em produção:
    # DATABASE_URL=postgresql://user:pass@host/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
