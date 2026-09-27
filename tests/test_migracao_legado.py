"""Testes de migração de um banco de dados "de verdade", no formato antigo
(um produto só por orçamento, antes da tabela itens_orcamento existir), para
o formato atual — reproduzindo o cenário de quem já vinha usando o sistema e
atualizou para uma versão mais nova.

Esses testes usam um arquivo .sqlite3 temporário (em vez do banco em memória
usado pelos outros testes) porque a migração de verdade só acontece quando o
banco já existe em disco com o esquema antigo.
"""
import sqlite3

import pytest


def _criar_banco_legado(caminho):
    """Cria um banco no formato anterior ao suporte a múltiplos produtos por
    orçamento: a tabela orcamentos ainda guarda tipo_produto/quantidade/
    custo_unitario_produto direto (com tipo_produto NOT NULL), sem a tabela
    itens_orcamento."""
    conexao = sqlite3.connect(caminho)
    conexao.executescript(
        """
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            telefone VARCHAR(20), email VARCHAR(120), cep VARCHAR(10),
            endereco VARCHAR(200), bairro VARCHAR(80), cidade VARCHAR(80), uf VARCHAR(2),
            data_cadastro DATETIME
        );
        CREATE TABLE itens_estoque (
            id INTEGER PRIMARY KEY,
            tipo_produto VARCHAR(80) NOT NULL UNIQUE,
            custo_unitario FLOAT NOT NULL DEFAULT 0.0,
            quantidade_em_estoque INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER DEFAULT 0,
            atualizado_em DATETIME
        );
        CREATE TABLE orcamentos (
            id INTEGER PRIMARY KEY,
            codigo VARCHAR(20) NOT NULL UNIQUE,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            tipo_produto VARCHAR(80) NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            custo_unitario_produto FLOAT,
            custo_personalizacao FLOAT,
            estoque_baixado BOOLEAN NOT NULL DEFAULT 0,
            descricao TEXT, valor_estimado FLOAT,
            status VARCHAR(20) NOT NULL DEFAULT 'Solicitado',
            data_solicitacao DATETIME, prazo_entrega DATE
        );
        INSERT INTO clientes (id, nome, telefone, data_cadastro)
            VALUES (1, 'Thaís Toledo', '(11) 94298-9460', '2026-01-01 09:00:00');
        INSERT INTO itens_estoque (tipo_produto, custo_unitario, quantidade_em_estoque, estoque_minimo)
            VALUES ('Caneca personalizada', 10.0, 50, 5);
        INSERT INTO orcamentos (
            id, codigo, cliente_id, tipo_produto, quantidade, custo_unitario_produto,
            custo_personalizacao, estoque_baixado, descricao, valor_estimado, status, data_solicitacao
        ) VALUES (
            1, 'ORC-0001', 1, 'Caneca personalizada', 3, 10.0,
            5.0, 1, 'pedido antigo', 90.0, 'Aprovado', '2026-01-10 10:00:00'
        );
        """
    )
    conexao.commit()
    conexao.close()


@pytest.fixture
def app_com_banco_legado(tmp_path):
    """Sobe a aplicação apontando para um banco recém-criado no formato
    antigo, para que create_app() rode a migração de verdade contra ele.

    Não dá pra usar a variável de ambiente DATABASE_URL aqui: config.py lê
    os.environ só uma vez, quando o módulo é importado pela primeira vez
    (o que já aconteceu antes deste teste rodar, via conftest.py) — depois
    disso, mudar a variável de ambiente não tem mais efeito nenhum. Por
    isso a gente troca a URL do banco direto na classe de configuração."""
    caminho_banco = tmp_path / "mgt_legado.sqlite3"
    _criar_banco_legado(str(caminho_banco))

    from app import create_app, db
    from config import config_by_name

    classe_config = config_by_name["development"]
    uri_original = classe_config.SQLALCHEMY_DATABASE_URI
    classe_config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{caminho_banco}"
    try:
        application = create_app("development")
        with application.app_context():
            yield application, db
            db.session.remove()
    finally:
        classe_config.SQLALCHEMY_DATABASE_URI = uri_original


def test_migracao_remove_colunas_legadas_do_orcamento(app_com_banco_legado):
    _app, db = app_com_banco_legado
    from sqlalchemy import text

    with db.engine.connect() as conexao:
        colunas = {linha[1] for linha in conexao.execute(text("PRAGMA table_info(orcamentos)"))}

    # As colunas do formato de um produto só não devem mais existir — é
    # exatamente isso que causava "NOT NULL constraint failed:
    # orcamentos.tipo_produto" ao tentar salvar um orçamento novo.
    assert "tipo_produto" not in colunas
    assert "quantidade" not in colunas
    assert "custo_unitario_produto" not in colunas
    # As colunas atuais continuam lá.
    assert "custo_personalizacao" in colunas
    assert "estoque_baixado" in colunas


def test_migracao_preserva_orcamento_existente_como_item(app_com_banco_legado):
    _app, db = app_com_banco_legado
    from app.models import Orcamento

    orcamento = Orcamento.query.filter_by(codigo="ORC-0001").first()
    assert orcamento is not None
    assert orcamento.status == "Aprovado"
    assert orcamento.estoque_baixado is True
    assert len(orcamento.itens) == 1
    assert orcamento.itens[0].tipo_produto == "Caneca personalizada"
    assert orcamento.itens[0].quantidade == 3
    assert orcamento.itens[0].custo_unitario_produto == 10.0


def test_consegue_salvar_orcamento_novo_apos_migrar_banco_legado(app_com_banco_legado):
    """Reproduz o bug relatado: depois de migrar um banco antigo, salvar um
    orçamento novo (com o formulário de vários produtos) não pode mais falhar
    com "NOT NULL constraint failed: orcamentos.tipo_produto"."""
    application, _db = app_com_banco_legado
    client = application.test_client()

    resposta = client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": "1",
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "2",
            "descricao": "tetse",
            "valor_estimado": "230.0",
            "custo_personalizacao": "12.0",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "NOT NULL".encode() not in resposta.data

    from app.models import Orcamento

    assert Orcamento.query.count() == 2
    novo = Orcamento.query.filter_by(codigo="ORC-0002").first()
    assert novo is not None
    assert novo.itens[0].tipo_produto == "Caneca personalizada"
    assert novo.itens[0].quantidade == 2
