import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "mgt-presentes-chave-de-desenvolvimento")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Senha única para entrar no sistema (protege o site quando ele está
    # publicado na internet). Vem de uma variável de ambiente — nunca fica
    # escrita no código, porque o repositório é público no GitHub. Se essa
    # variável não estiver configurada, o sistema fica sem exigir login
    # (é o caso do ambiente local de desenvolvimento, por padrão).
    SITE_PASSWORD = os.environ.get("SITE_PASSWORD")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'mgt.sqlite3')}"
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Nos testes automatizados o login nunca é exigido, mesmo que a máquina
    # que roda os testes tenha essa variável de ambiente configurada.
    SITE_PASSWORD = None


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
