import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    UPLOAD_FOLDER    = os.path.join(BASE_DIR, 'uploads')
    DOCUMENTS_FOLDER = os.path.join(BASE_DIR, 'uploads', 'documents')
    LIBRARY_FOLDER   = os.path.join(BASE_DIR, 'uploads', 'library')
    ALLOWED_EXTENSIONS         = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    ALLOWED_LIBRARY_EXTENSIONS = {'pdf', 'epub'}

    MAIL_SERVER         = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT           = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS        = True
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@saas.com')

    # Tenant padrão criado na primeira execução
    DEFAULT_TENANT_NAME = os.environ.get('DEFAULT_TENANT_NAME', 'Demo Clínica')
    DEFAULT_TENANT_SLUG = os.environ.get('DEFAULT_TENANT_SLUG', 'demo')
    ADMIN_EMAIL         = os.environ.get('ADMIN_EMAIL',  'admin@consultorio.com')
    ADMIN_PASSWORD      = os.environ.get('ADMIN_PASSWORD', 'Admin@2024!')

    DATA_DIR          = os.path.join(BASE_DIR, 'data')

    SAAS_DOMAIN       = os.environ.get('SAAS_DOMAIN', 'localhost')
    INTERNAL_API_KEY  = os.environ.get('INTERNAL_API_KEY', 'internal-dev-key-change-in-prod')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'database', 'consultorio.db')}"
    )


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '')
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
