import os

from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name=None):
    """Application factory: cria e configura a instância do Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    from config import config_by_name

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app.routes.web import web_bp
    from app.routes.api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()
        _atualizar_esquema_banco()
        _migrar_orcamentos_para_itens()

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        def static_url(filename):
            """Gera a URL do arquivo estático com um parâmetro de versão
            baseado na data de modificação do arquivo, para que o navegador
            sempre baixe a versão mais nova de CSS/JS/imagens depois de uma
            atualização do sistema (em vez de usar uma cópia antiga guardada
            em cache)."""
            caminho = os.path.join(app.static_folder, filename)
            try:
                versao = int(os.path.getmtime(caminho))
            except OSError:
                versao = 0
            return url_for("static", filename=filename, v=versao)

        return {"ano_atual": datetime.now().year, "static_url": static_url}

    return app


def _atualizar_esquema_banco():
    """Adiciona colunas novas a um banco de dados já existente, sem apagar
    os dados que já estão lá.

    db.create_all() só cria tabelas que ainda não existem — quando o
    modelo ganha uma coluna nova numa tabela que o usuário já tem em
    produção (como aconteceu ao adicionar o controle de estoque e custos
    aos orçamentos), é preciso adicionar essa coluna manualmente, senão o
    sistema continua rodando com o banco antigo e quebra ao tentar ler a
    coluna nova."""
    from sqlalchemy import text

    colunas_novas_orcamentos = {
        "custo_personalizacao": "REAL",
        "estoque_baixado": "BOOLEAN NOT NULL DEFAULT 0",
    }

    with db.engine.connect() as conexao:
        resultado = conexao.execute(text("PRAGMA table_info(orcamentos)"))
        colunas_existentes = {linha[1] for linha in resultado}

        for nome, definicao_sql in colunas_novas_orcamentos.items():
            if nome not in colunas_existentes:
                conexao.execute(text(f"ALTER TABLE orcamentos ADD COLUMN {nome} {definicao_sql}"))

        conexao.commit()


def _migrar_orcamentos_para_itens():
    """Um orçamento passou a poder ter mais de um produto (tabela nova
    "itens_orcamento"). Bancos de dados já existentes ainda guardam o
    produto/quantidade/custo direto na tabela "orcamentos" (do jeito
    antigo, um produto só por orçamento) — essa função move esses dados
    para um item na tabela nova, na primeira vez que o sistema roda com a
    versão atualizada, sem duplicar nada nem perder o histórico."""
    from sqlalchemy import text

    with db.engine.connect() as conexao:
        resultado = conexao.execute(text("PRAGMA table_info(orcamentos)"))
        colunas_existentes = {linha[1] for linha in resultado}

        if "tipo_produto" not in colunas_existentes:
            # Banco já criado no formato atual (com itens_orcamento) —
            # não tem coluna antiga para migrar.
            return

        linhas = conexao.execute(
            text(
                "SELECT id, tipo_produto, quantidade, custo_unitario_produto "
                "FROM orcamentos WHERE tipo_produto IS NOT NULL"
            )
        ).fetchall()

        for orcamento_id, tipo_produto, quantidade, custo_unitario_produto in linhas:
            ja_tem_item = conexao.execute(
                text("SELECT COUNT(*) FROM itens_orcamento WHERE orcamento_id = :id"),
                {"id": orcamento_id},
            ).scalar()
            if ja_tem_item:
                continue

            conexao.execute(
                text(
                    "INSERT INTO itens_orcamento (orcamento_id, tipo_produto, quantidade, custo_unitario_produto) "
                    "VALUES (:orcamento_id, :tipo_produto, :quantidade, :custo_unitario_produto)"
                ),
                {
                    "orcamento_id": orcamento_id,
                    "tipo_produto": tipo_produto,
                    "quantidade": quantidade or 1,
                    "custo_unitario_produto": custo_unitario_produto,
                },
            )

        conexao.commit()
