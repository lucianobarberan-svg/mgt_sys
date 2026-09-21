import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "mgt-presentes-chave-de-desenvolvimento")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'mgt.sqlite3')}"
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    # Em produção (nuvem), a URL do banco (ex.: PostgreSQL) vem de uma
    # variável de ambiente configurada no serviço de hospedagem.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'mgt.sqlite3')}"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
