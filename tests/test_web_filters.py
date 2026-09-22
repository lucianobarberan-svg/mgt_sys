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


def test_orcamentos_lista_filtra_por_intervalo_de_datas(app, db, client):
    hoje = date.today()
    ha_dez_dias = hoje - timedelta(days=10)
    ha_sessenta_dias = hoje - timedelta(days=60)

    _, orcamento_recente = _criar_cliente_com_orcamento(db, "Cliente Recente", data_solicitacao=ha_dez_dias)
    _, orcamento_antigo = _criar_cliente_com_orcamento(db, "Cliente Antigo", data_solicitacao=ha_sessenta_dias)

    data_inicio = (hoje - timedelta(days=15)).strftime("%Y-%m-%d")
    resposta = client.get(f"/orcamentos?data_inicio={data_inicio}")

    assert resposta.status_code == 200
    assert orcamento_recente.codigo.encode() in resposta.data
    assert orcamento_antigo.codigo.encode() not in resposta.data


def test_orcamentos_lista_atalho_mes_atual(app, db, client):
    hoje = date.today()
    ha_sessenta_dias = hoje - timedelta(days=60)

    _, orcamento_este_mes = _criar_cliente_com_orcamento(db, "Cliente Este Mes", data_solicitacao=hoje)
    _, orcamento_ha_2_meses = _criar_cliente_com_orcamento(db, "Cliente Ha Meses", data_solicitacao=ha_sessenta_dias)

    resposta = client.get("/orcamentos?periodo=mes_atual")

    assert resposta.status_code == 200
    assert orcamento_este_mes.codigo.encode() in resposta.data
    assert orcamento_ha_2_meses.codigo.encode() not in resposta.data


def test_orcamentos_lista_atalho_mes_anterior(app, db, client):
    hoje = date.today()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)

    _, orcamento_mes_anterior = _criar_cliente_com_orcamento(
        db, "Cliente Mes Anterior", data_solicitacao=ultimo_dia_mes_anterior
    )
    _, orcamento_este_mes = _criar_cliente_com_orcamento(db, "Cliente Este Mes", data_solicitacao=hoje)

    resposta = client.get("/orcamentos?periodo=mes_anterior")

    assert resposta.status_code == 200
    assert orcamento_mes_anterior.codigo.encode() in resposta.data
    assert orcamento_este_mes.codigo.encode() not in resposta.data
