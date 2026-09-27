from datetime import date

from app.models import Cliente, Orcamento


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
    orcamento1 = Orcamento(codigo=codigo1, cliente_id=cliente.id, tipo_produto="Caneca personalizada")
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

    orcamento = Orcamento(
        codigo=Orcamento.gerar_codigo(),
        cliente_id=cliente.id,
        tipo_produto="Azulejo personalizado",
    )
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.status == "Solicitado"


def test_excluir_cliente_remove_orcamentos_em_cascata(app, db):
    cliente = Cliente(nome="Ana Lima")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(
        codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, tipo_produto="Descanso de mouse personalizado"
    )
    db.session.add(orcamento)
    db.session.commit()

    db.session.delete(cliente)
    db.session.commit()

    assert Orcamento.query.count() == 0


def test_whatsapp_url_usa_telefone_do_cliente_com_ddi(app, db):
    cliente = Cliente(nome="Thaís Toledo", telefone="(11) 94298-9460")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(
        codigo=Orcamento.gerar_codigo(),
        cliente_id=cliente.id,
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

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, tipo_produto="Chaveiro personalizado")
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.whatsapp_url.startswith("https://wa.me/5511988881234?text=")


def test_whatsapp_url_sem_telefone_cadastrado_abre_selecao_de_contato(app, db):
    cliente = Cliente(nome="Sem Telefone")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, tipo_produto="Caneta personalizada")
    db.session.add(orcamento)
    db.session.commit()

    assert orcamento.whatsapp_url.startswith("https://wa.me/?text=")


def test_mensagem_whatsapp_usa_valor_a_combinar_quando_sem_valor(app, db):
    cliente = Cliente(nome="Maria Souza")
    db.session.add(cliente)
    db.session.commit()

    orcamento = Orcamento(codigo=Orcamento.gerar_codigo(), cliente_id=cliente.id, tipo_produto="Boné personalizado")
    db.session.add(orcamento)
    db.session.commit()

    assert "Valor: a combinar" in orcamento.mensagem_whatsapp
