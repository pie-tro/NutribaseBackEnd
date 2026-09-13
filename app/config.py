import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Configuração base, lida a partir de variáveis de ambiente (.env)."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://nutribase:nutribase@localhost:5432/nutribase_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60))
    )
    # Guarda tokens revogados (logoff) em memória/tabela — ver app/extensions.py
    JWT_BLACKLIST_ENABLED = True

    # Upload de fotos de perfil
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads/profile_photos"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", 5)) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # E-mail (simulado por enquanto — RF03)
    MAIL_SIMULATION = os.getenv("MAIL_SIMULATION", "true").lower() == "true"
    PASSWORD_RESET_CODE_EXPIRES_MINUTES = int(
        os.getenv("PASSWORD_RESET_CODE_EXPIRES_MINUTES", 15)
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", "postgresql://nutribase:nutribase@localhost:5432/nutribase_test_db"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
