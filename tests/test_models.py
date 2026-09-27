from datetime import date

from app.models import Cliente, ItemOrcamento, Orcamento


def _orcamento_com_item(cliente_id, tipo_produto="Caneca personalizada", quantidade=1, **kwargs):
    """Cria um Orcamento (não commitado) já com um ItemOrcamento — um
    orçamento pode ter mais de um produto, mas a maioria dos testes só
    precisa de um para verificar o comportamento em questão."""
    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente_id, **kwargs)
    orcamento.itens.append(ItemOrcamento(tipo_produto=tipo_produto, quantidade=quantidade))
    return orcamento


def test_criar_cliente(app, db):
    cliente = Cliente(nome="Thaís Toledo", telefone="(11) 94298-9460")
    db.session.add(cliente)
    db.session.commit()

    assert cliente.id is not None
    assert Cliente.query.count() == 1


def test_gerar_codigo_orcamento_sequencial(app, db):
    cliente = Cliente(nome="Maria Souza")
    db.session.add(cliente)
    db.session.commit()

    codigo1 = Orcamento.gerar_codigo()
    orcamento1 = _orcamento_com_item(cliente.id)
    orcamento1.codigo = codigo1
    db.session.add(orcamento1)
    db.session.commit()

    codigo2 = Orcamento.gerar_codigo()

    assert codigo1 == "ORC-0001"
    assert codigo2 == "ORC-0002"
    assert codigo1 != codigo2


def test_orcamento_status_padrao(app, db):
    cliente = Cliente(nome="João Silva")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id, tipo_produto="Azulejo personalizado")
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.status == "Solicitado"


def test_excluir_cliente_remove_orcamentos_em_cascata(app, db):
    cliente = Cliente(nome="Ana Lima")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id, tipo_produto="Descanso de mouse personalizado")
    db.session.add(orcamento)
    db.session.commit()

    db.session.delete(cliente)
    db.session.commit()

    assert Orcamento.query.count() == 0


def test_orcamento_pode_ter_mais_de_um_produto(app, db):
    cliente = Cliente(nome="Beatriz Lima")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, valor_estimado=120.0)
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=2, custo_unitario_produto=10.0))
    orcamento.itens.append(ItemOrcamento(tipo_produto="Chaveiro personalizado", quantidade=3, custo_unitario_produto=3.0))
    db.session.add(orcamento)
    db.session.commit()

    assert len(orcamento.itens) == 2
    # custo_total = (10*2) + (3*3) = 29
    assert orcamento.custo_total == 29.0
    assert orcamento.lucro_liquido == 91.0
    assert "Caneca personalizada (x2)" in orcamento.resumo_produtos
    assert "Chaveiro personalizado (x3)" in orcamento.resumo_produtos


def test_excluir_orcamento_remove_itens_em_cascata(app, db):
    cliente = Cliente(nome="Rafael Souza")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id)
    db.session.add(orcamento)
    db.session.commit()
    orcamento_id = orcamento.id

    db.session.delete(orcamento)
    db.session.commit()

    assert ItemOrcamento.query.filter_by(orcamento_id=orcamento_id).count() == 0


def test_whatsapp_url_usa_telefone_do_cliente_com_ddi(app, db):
    cliente = Cliente(nome="Thaís Toledo", telefone="(11) 94298-9460")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(
        cliente.id,
        tipo_produto="Caneca personalizada",
        quantidade=2,
        valor_estimado=90.0,
        prazo_entrega=date(2026, 10, 15),
    )
    db.session.add(orcamento)
    db.session.commit()

    url = orcamento.whatsapp_url

    assert url.startswith("https://wa.me/5511942989460?text=")
    assert "Or%C3%A7amento" in url  # "Orçamento" codificado na URL
    # dados de custo/lucro nunca podem entrar na mensagem para o cliente.
    assert "custo" not in url.lower()
    assert "lucro" not in url.lower()


def test_whatsapp_url_nao_duplica_ddi_quando_ja_presente(app, db):
    cliente = Cliente(nome="Carlos Pereira", telefone="5511988881234")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id, tipo_produto="Chaveiro personalizado")
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.whatsapp_url.startswith("https://wa.me/5511988881234?text=")


def test_whatsapp_url_sem_telefone_cadastrado_abre_selecao_de_contato(app, db):
    cliente = Cliente(nome="Sem Telefone")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id, tipo_produto="Caneta personalizada")
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.whatsapp_url.startswith("https://wa.me/?text=")


def test_mensagem_whatsapp_usa_valor_a_combinar_quando_sem_valor(app, db):
    cliente = Cliente(nome="Maria Souza")
    db.session.add(cliente)
    db.session.commit()

    orcamento = _orcamento_com_item(cliente.id, tipo_produto="Boné personalizado")
    db.session.add(orcamento)
    db.session.commit()

    assert "Valor total: a combinar" in orcamento.mensagem_whatsapp


def test_mensagem_whatsapp_lista_todos_os_produtos(app, db):
    cliente = Cliente(nome="Paula Nunes")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, valor_estimado=100.0)
    orcamento.itens.append(ItemOrcamento(tipo_produto="Caneca personalizada", quantidade=2))
    orcamento.itens.append(ItemOrcamento(tipo_produto="Chaveiro personalizado", quantidade=1))
    db.session.add(orcamento)
    db.session.commit()

    mensagem = orcamento.mensagem_whatsapp
    assert "Caneca personalizada" in mensagem
    assert "Chaveiro personalizado" in mensagem
