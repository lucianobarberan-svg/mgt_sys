from app.models import Cliente, ItemOrcamento, Orcamento


def _criar_cliente_com_orcamento(db, nome_cliente="Thaís Toledo", tipo="Caneca personalizada"):
    cliente = Cliente(nome=nome_cliente)
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id)
    orcamento.itens.append(ItemOrcamento(tipo_produto=tipo, quantidade=1))
    db.session.add(orcamento)
    db.session.commit()
    return cliente, orcamento


def test_api_lista_clientes_vazia(client):
    resposta = client.get("/api/clientes")
    assert resposta.status_code == 200
    assert resposta.get_json() == []


def test_api_busca_cliente_por_nome(app, db, client):
    _criar_cliente_com_orcamento(db, nome_cliente="Thaís Toledo")
    db.session.add(Cliente(nome="Carlos Pereira"))
    db.session.commit()

    resposta = client.get("/api/clientes?nome=tha")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert len(dados) == 1
    assert dados[0]["nome"] == "Thaís Toledo"


def test_api_busca_cliente_nome_inexistente(app, db, client):
    _criar_cliente_com_orcamento(db, nome_cliente="Thaís Toledo")

    resposta = client.get("/api/clientes?nome=zzz")
    assert resposta.get_json() == []


def test_api_busca_orcamento_por_codigo(app, db, client):
    _, orcamento = _criar_cliente_com_orcamento(db)

    resposta = client.get(f"/api/orcamentos?codigo={orcamento.codigo}")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert len(dados) == 1
    assert dados[0]["codigo"] == orcamento.codigo
    assert dados[0]["cliente_nome"] == "Thaís Toledo"


def test_api_busca_orcamento_codigo_inexistente(app, db, client):
    _criar_cliente_com_orcamento(db)

    resposta = client.get("/api/orcamentos?codigo=ORC-9999")
    assert resposta.get_json() == []


def test_api_dashboard_resumo(app, db, client):
    _criar_cliente_com_orcamento(db, nome_cliente="Cliente A", tipo="Caneca personalizada")
    _criar_cliente_com_orcamento(db, nome_cliente="Cliente B", tipo="Caneca personalizada")

    resposta = client.get("/api/dashboard/resumo")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["total_clientes"] == 2
    assert dados["total_orcamentos"] == 2
    assert dados["por_tipo_produto"]["Caneca personalizada"] == 2


def test_pagina_inicial_carrega(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "MGT".encode() in resposta.data


def test_pagina_consulta_carrega(client):
    resposta = client.get("/consulta")
    assert resposta.status_code == 200
