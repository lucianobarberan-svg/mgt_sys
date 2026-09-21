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
