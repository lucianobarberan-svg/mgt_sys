"""Testes da proteção por senha (SITE_PASSWORD) do sistema.

Como a configuração de testes (config.py -> TestingConfig) sempre zera
SITE_PASSWORD, o cliente padrão (fixture `client`) nunca exige login — por
isso esses testes criam sua própria instância da aplicação, com uma senha
configurada de propósito, para exercitar o fluxo real de login/logout."""
import pytest

from app import create_app, db as _db
from config import config_by_name


@pytest.fixture
def app_com_senha():
    """Sobe a aplicação com SITE_PASSWORD configurada, simulando o sistema
    publicado na internet (ex.: no Render)."""
    classe_config = config_by_name["testing"]
    senha_original = classe_config.SITE_PASSWORD
    classe_config.SITE_PASSWORD = "segredo-123"
    try:
        application = create_app("testing")
        with application.app_context():
            _db.create_all()
            yield application
            _db.session.remove()
            _db.drop_all()
    finally:
        classe_config.SITE_PASSWORD = senha_original


@pytest.fixture
def client_com_senha(app_com_senha):
    return app_com_senha.test_client()


def test_sem_login_redireciona_para_tela_de_login(client_com_senha):
    resposta = client_com_senha.get("/", follow_redirects=False)
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_login_com_senha_errada_nao_libera_acesso(client_com_senha):
    resposta = client_com_senha.post("/login", data={"senha": "errada"}, follow_redirects=True)
    assert resposta.status_code == 200
    assert "Senha incorreta".encode() in resposta.data

    # continua bloqueado
    resposta_index = client_com_senha.get("/", follow_redirects=False)
    assert resposta_index.status_code == 302


def test_login_com_senha_certa_libera_acesso(client_com_senha):
    resposta = client_com_senha.post(
        "/login", data={"senha": "segredo-123", "proximo": "/"}, follow_redirects=True
    )
    assert resposta.status_code == 200
    assert "MGT".encode() in resposta.data

    # agora consegue acessar direto, sem ser redirecionado
    resposta_index = client_com_senha.get("/")
    assert resposta_index.status_code == 200


def test_login_protege_tambem_a_api(client_com_senha):
    resposta = client_com_senha.get("/api/clientes", follow_redirects=False)
    assert resposta.status_code == 302

    client_com_senha.post("/login", data={"senha": "segredo-123"})
    resposta_depois = client_com_senha.get("/api/clientes")
    assert resposta_depois.status_code == 200


def test_logout_bloqueia_acesso_de_novo(client_com_senha):
    client_com_senha.post("/login", data={"senha": "segredo-123"})
    assert client_com_senha.get("/").status_code == 200

    client_com_senha.post("/logout")
    resposta = client_com_senha.get("/", follow_redirects=False)
    assert resposta.status_code == 302


def test_sem_senha_configurada_sistema_fica_livre(client):
    # `client` vem da fixture padrão (conftest.py), que usa TestingConfig
    # com SITE_PASSWORD=None — comportamento igual ao de antes dessa feature.
    resposta = client.get("/")
    assert resposta.status_code == 200
