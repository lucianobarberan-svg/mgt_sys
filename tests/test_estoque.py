from app.models import Cliente, ItemEstoque, ItemOrcamento, Orcamento


def _criar_cliente(db, nome="Thaís Toledo"):
    cliente = Cliente(nome=nome)
    db.session.add(cliente)
    db.session.commit()
    return cliente


def test_criar_item_estoque(app, db):
    item = ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20)
    db.session.add(item)
    db.session.commit()

    assert item.id is not None
    assert item.to_dict()["valor_total_em_estoque"] == 200.0
    assert item.to_dict()["estoque_baixo"] is False


def test_item_estoque_baixo_quando_abaixo_do_minimo(app, db):
    item = ItemEstoque(tipo_produto="Chaveiro personalizado", custo_unitario=2.0, quantidade_em_estoque=3, estoque_minimo=5)
    db.session.add(item)
    db.session.commit()

    assert item.to_dict()["estoque_baixo"] is True


def test_custo_total_e_lucro_liquido_orcamento(app, db):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, valor_estimado=100.0, custo_personalizacao=5.0)
    orcamento.itens.append(
        ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=3, custo_unitario_produto=10.0)
    )
    db.session.add(orcamento)
    db.session.commit()

    # custo_total = (10 * 3) + 5 = 35 ; lucro = 100 - 35 = 65
    assert orcamento.custo_total == 35.0
    assert orcamento.lucro_liquido == 65.0


def test_custo_total_sem_custo_informado_e_zero(app, db):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, valor_estimado=50.0)
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=1))
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.custo_total == 0.0
    assert orcamento.lucro_liquido == 50.0


# --------------------------------------------------------------------------
# Rotas de Estoque
# --------------------------------------------------------------------------
def test_estoque_lista_vazia_carrega(client):
    resposta = client.get("/estoque")
    assert resposta.status_code == 200
    assert "Nenhum item de estoque cadastrado".encode() in resposta.data


def test_estoque_novo_cria_item(app, db, client):
    resposta = client.post(
        "/estoque/novo",
        data={"tipo_produto": "Caneca personalizada", "custo_unitario": "10,00", "quantidade_em_estoque": "15", "estoque_minimo": "3"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    assert item is not None
    assert item.custo_unitario == 10.0
    assert item.quantidade_em_estoque == 15


def test_estoque_novo_rejeita_tipo_duplicado(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=5))
    db.session.commit()

    resposta = client.post(
        "/estoque/novo",
        data={"tipo_produto": "Caneca personalizada", "custo_unitario": "12", "quantidade_em_estoque": "1"},
        follow_redirects=True,
    )
    assert "já existe um item de estoque cadastrado".encode() in resposta.data.lower() or ItemEstoque.query.count() == 1


def test_estoque_editar_atualiza_quantidade(app, db, client):
    item = ItemEstoque(tipo_produto="Copo personalizado", custo_unitario=5.0, quantidade_em_estoque=10)
    db.session.add(item)
    db.session.commit()

    resposta = client.post(
        f"/estoque/{item.id}/editar",
        data={"custo_unitario": "6,50", "quantidade_em_estoque": "25", "estoque_minimo": "2"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    item_atualizado = ItemEstoque.query.get(item.id)
    assert item_atualizado.custo_unitario == 6.5
    assert item_atualizado.quantidade_em_estoque == 25


def test_estoque_excluir_remove_item(app, db, client):
    item = ItemEstoque(tipo_produto="Garrafa personalizada", custo_unitario=8.0, quantidade_em_estoque=4)
    db.session.add(item)
    db.session.commit()

    client.post(f"/estoque/{item.id}/excluir", follow_redirects=True)

    assert ItemEstoque.query.count() == 0


# --------------------------------------------------------------------------
# Movimentação de estoque ao mudar status do orçamento
# --------------------------------------------------------------------------
def test_baixa_estoque_ao_criar_orcamento_ja_aprovado(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    orcamento = Orcamento.query.first()

    assert item.quantidade_em_estoque == 17  # 20 - 3
    assert orcamento.estoque_baixado is True
    assert orcamento.itens[0].custo_unitario_produto == 10.0


def test_orcamento_com_mais_de_um_produto_da_baixa_em_todos(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.add(ItemEstoque(tipo_produto="Chaveiro personalizado", custo_unitario=3.0, quantidade_em_estoque=15))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": ["Caneca personalizada", "Chaveiro personalizado"],
            "item_quantidade[]": ["2", "4"],
            "valor_estimado": "120",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )

    caneca = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    chaveiro = ItemEstoque.query.filter_by(tipo_produto="Chaveiro personalizado").first()
    orcamento = Orcamento.query.first()

    assert caneca.quantidade_em_estoque == 18  # 20 - 2
    assert chaveiro.quantidade_em_estoque == 11  # 15 - 4
    assert len(orcamento.itens) == 2
    assert orcamento.estoque_baixado is True
    # custo_total = (10*2) + (3*4) = 32
    assert orcamento.custo_total == 32.0


def test_orcamento_novo_exige_pelo_menos_um_produto(app, db, client):
    cliente = _criar_cliente(db)

    resposta = client.post(
        "/orcamentos/novo",
        data={"cliente_id": str(cliente.id), "item_tipo_produto[]": "", "item_quantidade[]": ""},
        follow_redirects=True,
    )

    assert "Adicione pelo menos um produto".encode() in resposta.data
    assert Orcamento.query.count() == 0


def test_nao_baixa_estoque_para_status_solicitado(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Solicitado",
        },
        follow_redirects=True,
    )

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    orcamento = Orcamento.query.first()

    assert item.quantidade_em_estoque == 20
    assert orcamento.estoque_baixado is False
    assert orcamento.itens[0].custo_unitario_produto is None


def test_devolve_estoque_ao_cancelar_orcamento_ja_baixado(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )
    orcamento = Orcamento.query.first()

    client.post(
        f"/orcamentos/{orcamento.id}/editar",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Cancelado",
        },
        follow_redirects=True,
    )

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    orcamento_atualizado = Orcamento.query.get(orcamento.id)

    assert item.quantidade_em_estoque == 20  # devolvido
    assert orcamento_atualizado.estoque_baixado is False


def test_avisa_quando_nao_ha_item_de_estoque_cadastrado(app, db, client):
    cliente = _criar_cliente(db)

    resposta = client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Boné personalizado",
            "item_quantidade[]": "1",
            "valor_estimado": "50",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )

    assert "Não há item de estoque cadastrado".encode() in resposta.data


def test_devolve_estoque_ao_excluir_orcamento_baixado(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )
    orcamento = Orcamento.query.first()

    client.post(f"/orcamentos/{orcamento.id}/excluir", follow_redirects=True)

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    assert item.quantidade_em_estoque == 20


# --------------------------------------------------------------------------
# Página de impressão do orçamento
# --------------------------------------------------------------------------
def test_orcamentos_imprimir_carrega_e_nao_mostra_custo(app, db, client):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(
        codigo=Orcamento.gerar_codigo(),
        cliente_id=cliente.id,
        valor_estimado=90.0,
        custo_personalizacao=5.0,
        estoque_baixado=True,
    )
    orcamento.itens.append(
        ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=2, custo_unitario_produto=10.0)
    )
    db.session.add(orcamento)
    db.session.commit()

    resposta = client.get(f"/orcamentos/{orcamento.id}/imprimir")

    assert resposta.status_code == 200
    assert orcamento.codigo.encode() in resposta.data
    # Dados internos de custo/lucro não podem aparecer na página do cliente.
    assert b"25.00" not in resposta.data  # custo_total
    assert "Custo".encode() not in resposta.data
    assert "Lucro".encode() not in resposta.data
    # Botão de compartilhar pelo WhatsApp, com a mensagem já pronta.
    assert b"wa.me" in resposta.data
    assert "Compartilhar no WhatsApp".encode() in resposta.data


def test_orcamentos_lista_mostra_link_whatsapp(app, db, client):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id)
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=1))
    db.session.add(orcamento)
    db.session.commit()

    resposta = client.get("/orcamentos")

    assert b"wa.me" in resposta.data


def test_orcamentos_lista_mostra_resumo_de_varios_produtos(app, db, client):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id)
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=2))
    orcamento.itens.append(ItemOrcamento(tipo_produto="Chaveiro personalizado", quantidade=1))
    db.session.add(orcamento)
    db.session.commit()

    resposta = client.get("/orcamentos")

    assert "Caneca personalizada (x2)".encode() in resposta.data
    assert "Chaveiro personalizado (x1)".encode() in resposta.data


# --------------------------------------------------------------------------
# API — relatório financeiro
# --------------------------------------------------------------------------
def test_api_dashboard_resumo_inclui_financeiro(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "2",
            "valor_estimado": "80",
            "custo_personalizacao": "10",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )

    resposta = client.get("/api/dashboard/resumo")
    dados = resposta.get_json()

    # custo_total = (10*2) + 10 = 30 ; lucro = 80 - 30 = 50
    assert dados["financeiro"]["receita_confirmada"] == 80.0
    assert dados["financeiro"]["custo_confirmado"] == 30.0
    assert dados["financeiro"]["lucro_confirmado"] == 50.0
    assert dados["financeiro"]["margem_percentual"] == 62.5


def test_api_dashboard_resumo_ignora_nao_confirmados_no_financeiro(app, db, client):
    cliente = _criar_cliente(db)
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, valor_estimado=100.0, status="Solicitado")
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=1))
    db.session.add(orcamento)
    db.session.commit()

    resposta = client.get("/api/dashboard/resumo")
    dados = resposta.get_json()

    assert dados["financeiro"]["receita_confirmada"] == 0.0
    assert dados["financeiro"]["custo_confirmado"] == 0.0


def test_api_estoque_resumo(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20, estoque_minimo=5))
    db.session.add(ItemEstoque(tipo_produto="Chaveiro personalizado", custo_unitario=2.0, quantidade_em_estoque=1, estoque_minimo=5))
    db.session.commit()

    resposta = client.get("/api/estoque/resumo")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["valor_total_em_estoque"] == 202.0  # 10*20 + 2*1
    assert dados["itens_estoque_baixo"] == ["Chaveiro personalizado"]


# --------------------------------------------------------------------------
# Perdas de estoque
# --------------------------------------------------------------------------
def test_registrar_perda_da_baixa_no_estoque(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    resposta = client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Caneca personalizada", "quantidade": "2", "motivo": "Quebrou na sublimação"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    assert item.quantidade_em_estoque == 18  # 20 - 2

    from app.models import PerdaEstoque

    perda = PerdaEstoque.query.first()
    assert perda is not None
    assert perda.quantidade == 2
    assert perda.custo_unitario == 10.0
    assert perda.valor_perdido == 20.0
    assert perda.motivo == "Quebrou na sublimação"


def test_perda_soma_custo_de_personalizacao_ao_valor_perdido(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    resposta = client.post(
        "/estoque/perdas/nova",
        data={
            "tipo_produto": "Caneca personalizada",
            "quantidade": "2",
            "custo_personalizacao": "5,50",
            "motivo": "Estampa saiu torta",
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    from app.models import PerdaEstoque

    perda = PerdaEstoque.query.first()
    assert perda is not None
    assert perda.custo_unitario == 10.0
    assert perda.custo_personalizacao == 5.5
    assert perda.custo_produto_total == 20.0  # 10 * 2
    assert perda.valor_perdido == 25.5  # (10*2) + 5.5


def test_perda_sem_custo_de_personalizacao_mantem_valor_perdido_so_do_produto(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Chaveiro personalizado", custo_unitario=3.0, quantidade_em_estoque=10))
    db.session.commit()

    client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Chaveiro personalizado", "quantidade": "1"},
        follow_redirects=True,
    )

    from app.models import PerdaEstoque

    perda = PerdaEstoque.query.first()
    assert perda.custo_personalizacao == 0.0
    assert perda.valor_perdido == 3.0


def test_perda_nao_mexe_em_orcamentos(app, db, client):
    cliente = _criar_cliente(db)
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/orcamentos/novo",
        data={
            "cliente_id": str(cliente.id),
            "item_tipo_produto[]": "Caneca personalizada",
            "item_quantidade[]": "3",
            "valor_estimado": "90",
            "status": "Aprovado",
        },
        follow_redirects=True,
    )
    orcamento = Orcamento.query.first()

    client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Caneca personalizada", "quantidade": "1", "motivo": "Defeito"},
        follow_redirects=True,
    )

    orcamento_depois = Orcamento.query.get(orcamento.id)
    assert orcamento_depois.status == "Aprovado"
    assert orcamento_depois.itens[0].quantidade == 3


def test_excluir_perda_devolve_estoque(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Caneca personalizada", "quantidade": "2"},
        follow_redirects=True,
    )

    from app.models import PerdaEstoque

    perda = PerdaEstoque.query.first()
    client.post(f"/estoque/perdas/{perda.id}/excluir", follow_redirects=True)

    item = ItemEstoque.query.filter_by(tipo_produto="Caneca personalizada").first()
    assert item.quantidade_em_estoque == 20  # devolvido
    assert PerdaEstoque.query.count() == 0


def test_perda_sem_item_de_estoque_mostra_erro(app, db, client):
    resposta = client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Boné personalizado", "quantidade": "1"},
        follow_redirects=True,
    )
    assert "Não há item de estoque cadastrado".encode() in resposta.data


def test_api_dashboard_resumo_inclui_perdas(app, db, client):
    db.session.add(ItemEstoque(tipo_produto="Caneca personalizada", custo_unitario=10.0, quantidade_em_estoque=20))
    db.session.commit()

    client.post(
        "/estoque/perdas/nova",
        data={"tipo_produto": "Caneca personalizada", "quantidade": "2"},
        follow_redirects=True,
    )

    resposta = client.get("/api/dashboard/resumo")
    dados = resposta.get_json()

    assert dados["financeiro"]["quantidade_perdida"] == 2
    assert dados["financeiro"]["valor_perdido"] == 20.0
