from datetime import date, timedelta

from app.models import Cliente, Orcamento


def _criar_cliente_com_orcamento(db, nome_cliente, data_solicitacao=None):
    cliente = Cliente(nome=nome_cliente)
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(
        codigo=Orcamento.gerar_codigo(),
        cliente_id=cliente.id,
        tipo_produto="Caneca personalizada",
    )
    if data_solicitacao is not None:
        orcamento.data_solicitacao = data_solicitacao
    db.session.add(orcamento)
    db.session.commit()
    return cliente, orcamento


def test_clientes_lista_filtra_por_nome(app, db, client):
    _criar_cliente_com_orcamento(db, "Thaís Toledo")
    _criar_cliente_com_orcamento(db, "Carlos Pereira")

    resposta = client.get("/clientes?nome=tha")
    assert resposta.status_code == 200
    assert "Thaís Toledo".encode() in resposta.data
    assert "Carlos Pereira".encode() not in resposta.data


def test_orcamentos_lista_filtra_por_codigo(app, db, client):
    _, orcamento_a = _criar_cliente_com_orcamento(db, "Cliente A")
    _, orcamento_b = _criar_cliente_com_orcamento(db, "Cliente B")

    resposta = client.get(f"/orcamentos?codigo={orcamento_a.codigo}")
    assert resposta.status_code == 200
    assert orcamento_a.codigo.encode() in resposta.data
    assert orcamento_b.codigo.encode() not in resposta.data


def test_orcamentos_lista_filtra_por_cliente_id(app, db, client):
    cliente_a, orcamento_a = _criar_cliente_com_orcamento(db, "Cliente A")
    _, orcamento_b = _criar_cliente_com_orcamento(db, "Cliente B")

    resposta = client.get(f"/orcamentos?cliente_id={cliente_a.id}")
    assert resposta.status_code == 200
    assert orcamento_a.codigo.encode() in resposta.data
    assert orcamento_b.codigo.encode() not in resposta.data
    assert "Cliente A".encode() in resposta.data


def test_orcamentos_lista_ignora_filtro_de_data(app, db, client):
    # O filtro por período (data/mês atual/mês anterior) pertence apenas ao
    # Dashboard — a lista de Orçamentos filtra somente por código e cliente.
    hoje = date.today()
    ha_sessenta_dias = hoje - timedelta(days=60)

    _, orcamento_recente = _criar_cliente_com_orcamento(db, "Cliente Recente", data_solicitacao=hoje)
    _, orcamento_antigo = _criar_cliente_com_orcamento(db, "Cliente Antigo", data_solicitacao=ha_sessenta_dias)

    data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    resposta = client.get(f"/orcamentos?data_inicio={data_inicio}")

    assert resposta.status_code == 200
    assert orcamento_recente.codigo.encode() in resposta.data
    assert orcamento_antigo.codigo.encode() in resposta.data
    assert b"M\xc3\xaas atual" not in resposta.data
    assert b"M\xc3\xaas anterior" not in resposta.data


def test_clientes_lista_link_orcamentos_do_cliente(app, db, client):
    cliente, _ = _criar_cliente_com_orcamento(db, "Thaís Toledo")

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert f"/orcamentos?cliente_id={cliente.id}".encode() in resposta.data


def test_dashboard_pagina_aceita_filtro_de_periodo(app, db, client):
    resposta = client.get("/dashboard?periodo=mes_atual")
    assert resposta.status_code == 200
    # Os campos de data devem vir preenchidos com o período resolvido no servidor.
    hoje = date.today()
    inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
    assert inicio_mes.encode() in resposta.data


def test_api_dashboard_resumo_filtra_por_intervalo_de_datas(app, db, client):
    hoje = date.today()
    ha_sessenta_dias = hoje - timedelta(days=60)

    _criar_cliente_com_orcamento(db, "Cliente Recente", data_solicitacao=hoje)
    _criar_cliente_com_orcamento(db, "Cliente Antigo", data_solicitacao=ha_sessenta_dias)

    data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    resposta = client.get(f"/api/dashboard/resumo?data_inicio={data_inicio}")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["total_orcamentos"] == 1
