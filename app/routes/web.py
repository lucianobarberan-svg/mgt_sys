from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import (
    STATUS_COM_BAIXA_ESTOQUE,
    STATUS_ORCAMENTO,
    TIPOS_PRODUTO,
    Cliente,
    ItemEstoque,
    ItemOrcamento,
    Orcamento,
    PerdaEstoque,
)

web_bp = Blueprint("web", __name__)


def _parse_quantidade(valor_bruto):
    """Converte o campo "quantidade" do formulário em um inteiro >= 1.
    Vazio vira 1 (padrão); qualquer valor inválido vira None (erro)."""
    valor_bruto = (valor_bruto or "").strip()
    if not valor_bruto:
        return 1
    try:
        quantidade = int(valor_bruto)
    except ValueError:
        return None
    return quantidade if quantidade >= 1 else None


def _aplicar_movimentacao_estoque(orcamento):
    """Dá baixa no estoque na primeira vez que o orçamento chega a um
    status confirmado (Aprovado, Em produção, Concluído ou Entregue), e
    devolve a quantidade ao estoque se o orçamento for cancelado depois de
    já ter baixado. Também trava o custo unitário de cada produto do
    orçamento (o valor atual do item no estoque) nesse momento, para que o
    relatório financeiro do Dashboard reflita o custo da época da baixa,
    mesmo que o custo do item mude depois. Um orçamento pode ter mais de
    um produto — a baixa/devolução é aplicada a cada um deles."""
    deve_baixar = orcamento.status in STATUS_COM_BAIXA_ESTOQUE
    if deve_baixar and not orcamento.estoque_baixado:
        for item_orcamento in orcamento.itens:
            item_estoque = ItemEstoque.query.filter_by(tipo_produto=item_orcamento.tipo_produto).first()
            quantidade = item_orcamento.quantidade or 1
            if item_estoque:
                item_estoque.quantidade_em_estoque -= quantidade
                item_orcamento.custo_unitario_produto = item_estoque.custo_unitario
                if item_estoque.quantidade_em_estoque < 0:
                    flash(
                        f"Atenção: o estoque de \"{item_orcamento.tipo_produto}\" ficou negativo "
                        f"({item_estoque.quantidade_em_estoque} un.). Confira a quantidade cadastrada em Estoque.",
                        "erro",
                    )
            else:
                flash(
                    f"Não há item de estoque cadastrado para \"{item_orcamento.tipo_produto}\" — "
                    "cadastre em Estoque para o custo entrar automaticamente no relatório financeiro.",
                    "erro",
                )
        orcamento.estoque_baixado = True
    elif orcamento.status == "Cancelado" and orcamento.estoque_baixado:
        for item_orcamento in orcamento.itens:
            item_estoque = ItemEstoque.query.filter_by(tipo_produto=item_orcamento.tipo_produto).first()
            if item_estoque:
                item_estoque.quantidade_em_estoque += item_orcamento.quantidade or 1
        orcamento.estoque_baixado = False


def _coletar_itens_do_formulario(form):
    """Lê as listas paralelas "item_tipo_produto[]" e "item_quantidade[]"
    enviadas pelo formulário (um orçamento pode ter vários produtos) e
    devolve uma lista de dicts {tipo_produto, quantidade}. Linhas em
    branco (deixadas pelo botão "+ Adicionar produto" e não preenchidas)
    são ignoradas silenciosamente. Devolve (itens, erro)."""
    tipos = form.getlist("item_tipo_produto[]")
    quantidades_brutas = form.getlist("item_quantidade[]")

    itens = []
    for i, tipo_produto in enumerate(tipos):
        tipo_produto = (tipo_produto or "").strip()
        quantidade_bruta = quantidades_brutas[i] if i < len(quantidades_brutas) else ""
        if not tipo_produto and not (quantidade_bruta or "").strip():
            continue  # linha em branco — ignora

        if not tipo_produto:
            return None, "Selecione o produto em todas as linhas preenchidas."

        quantidade = _parse_quantidade(quantidade_bruta)
        if quantidade is None:
            return None, "Quantidade inválida — informe um número inteiro maior que zero em cada produto."

        itens.append({"tipo_produto": tipo_produto, "quantidade": quantidade})

    if not itens:
        return None, "Adicione pelo menos um produto ao orçamento."

    return itens, None


def _registrar_perda_estoque(tipo_produto, quantidade, motivo, custo_personalizacao=0.0):
    """Registra uma perda de estoque (produto quebrado, com defeito de
    personalização etc.). Dá baixa na quantidade e trava o custo unitário
    do item no momento da perda — não mexe em nenhum orçamento, já que o
    cliente não tem relação nenhuma com esse prejuízo. O custo da
    personalização (tinta, material etc.) que já tinha sido gasto nesse
    produto entra somado ao custo do produto no valor perdido."""
    item = ItemEstoque.query.filter_by(tipo_produto=tipo_produto).first()
    if not item:
        flash(f'Não há item de estoque cadastrado para "{tipo_produto}".', "erro")
        return None

    item.quantidade_em_estoque -= quantidade
    if item.quantidade_em_estoque < 0:
        flash(
            f"Atenção: o estoque de \"{tipo_produto}\" ficou negativo "
            f"({item.quantidade_em_estoque} un.) depois dessa perda. Confira a quantidade cadastrada em Estoque.",
            "erro",
        )

    perda = PerdaEstoque(
        tipo_produto=tipo_produto,
        quantidade=quantidade,
        custo_unitario=item.custo_unitario,
        custo_personalizacao=custo_personalizacao or 0.0,
        motivo=motivo,
    )
    db.session.add(perda)
    return perda


def _resolver_intervalo_datas(args):
    """Resolve data_inicio/data_fim (YYYY-MM-DD) a partir dos parâmetros da
    URL, aplicando os atalhos de período (?periodo=mes_atual|mes_anterior)
    quando presentes. Usado pela lista de orçamentos e pelo dashboard."""
    data_inicio = args.get("data_inicio", "").strip()
    data_fim = args.get("data_fim", "").strip()
    periodo = args.get("periodo", "").strip()

    hoje = date.today()
    if periodo == "mes_atual":
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
    elif periodo == "mes_anterior":
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
        data_inicio = primeiro_dia_mes_anterior.strftime("%Y-%m-%d")
        data_fim = ultimo_dia_mes_anterior.strftime("%Y-%m-%d")

    return data_inicio, data_fim


# --------------------------------------------------------------------------
# Página inicial
# --------------------------------------------------------------------------
@web_bp.route("/")
def index():
    total_clientes = Cliente.query.count()
    total_orcamentos = Orcamento.query.count()
    orcamentos_recentes = (
        Orcamento.query.order_by(Orcamento.data_solicitacao.desc()).limit(5).all()
    )
    return render_template(
        "index.html",
        total_clientes=total_clientes,
        total_orcamentos=total_orcamentos,
        orcamentos_recentes=orcamentos_recentes,
    )


# --------------------------------------------------------------------------
# Clientes
# --------------------------------------------------------------------------
@web_bp.route("/clientes")
def clientes_lista():
    termo_busca = request.args.get("nome", "").strip()
    query = Cliente.query
    if termo_busca:
        query = query.filter(Cliente.nome.ilike(f"%{termo_busca}%"))
    clientes = query.order_by(Cliente.nome).all()
    return render_template("clientes/list.html", clientes=clientes, termo_busca=termo_busca)


@web_bp.route("/clientes/novo", methods=["GET", "POST"])
def clientes_novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do cliente é obrigatório.", "erro")
            return render_template("clientes/form.html", cliente=None, form=request.form)

        cliente = Cliente(
            nome=nome,
            telefone=request.form.get("telefone", "").strip() or None,
            email=request.form.get("email", "").strip() or None,
            cep=request.form.get("cep", "").strip() or None,
            endereco=request.form.get("endereco", "").strip() or None,
            bairro=request.form.get("bairro", "").strip() or None,
            cidade=request.form.get("cidade", "").strip() or None,
            uf=request.form.get("uf", "").strip() or None,
        )
        db.session.add(cliente)
        db.session.commit()
        flash(f"Cliente \"{cliente.nome}\" cadastrado com sucesso.", "sucesso")
        return redirect(url_for("web.clientes_lista"))

    return render_template("clientes/form.html", cliente=None, form={})


@web_bp.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def clientes_editar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome do cliente é obrigatório.", "erro")
            return render_template("clientes/form.html", cliente=cliente, form=request.form)

        cliente.nome = nome
        cliente.telefone = request.form.get("telefone", "").strip() or None
        cliente.email = request.form.get("email", "").strip() or None
        cliente.cep = request.form.get("cep", "").strip() or None
        cliente.endereco = request.form.get("endereco", "").strip() or None
        cliente.bairro = request.form.get("bairro", "").strip() or None
        cliente.cidade = request.form.get("cidade", "").strip() or None
        cliente.uf = request.form.get("uf", "").strip() or None
        db.session.commit()
        flash(f"Cliente \"{cliente.nome}\" atualizado com sucesso.", "sucesso")
        return redirect(url_for("web.clientes_lista"))

    return render_template("clientes/form.html", cliente=cliente, form=None)


@web_bp.route("/clientes/<int:cliente_id>/excluir", methods=["POST"])
def clientes_excluir(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    nome = cliente.nome
    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente \"{nome}\" removido.", "sucesso")
    return redirect(url_for("web.clientes_lista"))


# --------------------------------------------------------------------------
# Orçamentos
# --------------------------------------------------------------------------
@web_bp.route("/orcamentos")
def orcamentos_lista():
    codigo_busca = request.args.get("codigo", "").strip()
    cliente_id = request.args.get("cliente_id", "").strip()

    query = Orcamento.query
    if codigo_busca:
        query = query.filter(Orcamento.codigo.ilike(f"%{codigo_busca}%"))
    if cliente_id:
        query = query.filter(Orcamento.cliente_id == cliente_id)

    orcamentos = query.order_by(Orcamento.data_solicitacao.desc()).all()

    cliente_filtrado = None
    if cliente_id:
        cliente_filtrado = Cliente.query.get(cliente_id)

    return render_template(
        "orcamentos/list.html",
        orcamentos=orcamentos,
        codigo_busca=codigo_busca,
        cliente_id=cliente_id,
        cliente_filtrado=cliente_filtrado,
    )


@web_bp.route("/orcamentos/novo", methods=["GET", "POST"])
def orcamentos_novo():
    clientes = Cliente.query.order_by(Cliente.nome).all()

    itens_estoque = {item.tipo_produto: item for item in ItemEstoque.query.all()}

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        itens_form, erro_itens = _coletar_itens_do_formulario(request.form)

        erro = None
        if not cliente_id:
            erro = "Selecione um cliente."
        elif erro_itens:
            erro = erro_itens

        if erro:
            flash(erro, "erro")
            return render_template(
                "orcamentos/form.html",
                orcamento=None,
                form=request.form,
                itens_form=itens_form or [],
                clientes=clientes,
                tipos_produto=TIPOS_PRODUTO,
                status_opcoes=STATUS_ORCAMENTO,
                itens_estoque=itens_estoque,
            )

        prazo_entrega = request.form.get("prazo_entrega") or None
        if prazo_entrega:
            prazo_entrega = datetime.strptime(prazo_entrega, "%Y-%m-%d").date()

        valor_estimado = request.form.get("valor_estimado") or None
        if valor_estimado:
            valor_estimado = float(valor_estimado.replace(",", "."))

        custo_personalizacao = request.form.get("custo_personalizacao") or None
        if custo_personalizacao:
            custo_personalizacao = float(custo_personalizacao.replace(",", "."))

        orcamento = Orcamento(
            codigo=Orcamento.gerar_codigo(),
            cliente_id=int(cliente_id),
            descricao=request.form.get("descricao", "").strip() or None,
            valor_estimado=valor_estimado,
            custo_personalizacao=custo_personalizacao,
            status=request.form.get("status") or "Solicitado",
            prazo_entrega=prazo_entrega,
        )
        for item_form in itens_form:
            orcamento.itens.append(
                ItemOrcamento(tipo_produto=item_form["tipo_produto"], quantidade=item_form["quantidade"])
            )
        db.session.add(orcamento)
        _aplicar_movimentacao_estoque(orcamento)
        db.session.commit()
        flash(f"Orçamento {orcamento.codigo} cadastrado com sucesso.", "sucesso")
        return redirect(url_for("web.orcamentos_lista"))

    return render_template(
        "orcamentos/form.html",
        orcamento=None,
        form={},
        itens_form=[{"tipo_produto": "", "quantidade": 1}],
        clientes=clientes,
        tipos_produto=TIPOS_PRODUTO,
        status_opcoes=STATUS_ORCAMENTO,
        itens_estoque=itens_estoque,
    )


@web_bp.route("/orcamentos/<int:orcamento_id>/editar", methods=["GET", "POST"])
def orcamentos_editar(orcamento_id):
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    clientes = Cliente.query.order_by(Cliente.nome).all()
    itens_estoque = {item.tipo_produto: item for item in ItemEstoque.query.all()}

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        itens_form, erro_itens = _coletar_itens_do_formulario(request.form)

        erro = None
        if not cliente_id:
            erro = "Selecione um cliente."
        elif erro_itens:
            erro = erro_itens

        if erro:
            flash(erro, "erro")
            return render_template(
                "orcamentos/form.html",
                orcamento=orcamento,
                form=request.form,
                itens_form=itens_form or [],
                clientes=clientes,
                tipos_produto=TIPOS_PRODUTO,
                status_opcoes=STATUS_ORCAMENTO,
                itens_estoque=itens_estoque,
            )

        prazo_entrega = request.form.get("prazo_entrega") or None
        if prazo_entrega:
            prazo_entrega = datetime.strptime(prazo_entrega, "%Y-%m-%d").date()

        valor_estimado = request.form.get("valor_estimado") or None
        if valor_estimado:
            valor_estimado = float(valor_estimado.replace(",", "."))

        custo_personalizacao = request.form.get("custo_personalizacao") or None
        if custo_personalizacao:
            custo_personalizacao = float(custo_personalizacao.replace(",", "."))

        orcamento.cliente_id = int(cliente_id)
        orcamento.descricao = request.form.get("descricao", "").strip() or None
        orcamento.valor_estimado = valor_estimado
        orcamento.custo_personalizacao = custo_personalizacao
        orcamento.status = request.form.get("status") or orcamento.status
        orcamento.prazo_entrega = prazo_entrega

        # Substitui a lista de produtos pela que veio do formulário.
        for item_antigo in list(orcamento.itens):
            orcamento.itens.remove(item_antigo)
        for item_form in itens_form:
            orcamento.itens.append(
                ItemOrcamento(tipo_produto=item_form["tipo_produto"], quantidade=item_form["quantidade"])
            )

        _aplicar_movimentacao_estoque(orcamento)
        db.session.commit()
        flash(f"Orçamento {orcamento.codigo} atualizado com sucesso.", "sucesso")
        return redirect(url_for("web.orcamentos_lista"))

    itens_form = [{"tipo_produto": item.tipo_produto, "quantidade": item.quantidade} for item in orcamento.itens]
    return render_template(
        "orcamentos/form.html",
        orcamento=orcamento,
        form=None,
        itens_form=itens_form,
        clientes=clientes,
        tipos_produto=TIPOS_PRODUTO,
        status_opcoes=STATUS_ORCAMENTO,
        itens_estoque=itens_estoque,
    )


@web_bp.route("/orcamentos/<int:orcamento_id>/excluir", methods=["POST"])
def orcamentos_excluir(orcamento_id):
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    codigo = orcamento.codigo

    # Se o estoque já tinha sido baixado para esse orçamento, devolve a
    # quantidade de cada produto antes de excluir — senão o item some do
    # estoque sem volta.
    if orcamento.estoque_baixado:
        for item_orcamento in orcamento.itens:
            item_estoque = ItemEstoque.query.filter_by(tipo_produto=item_orcamento.tipo_produto).first()
            if item_estoque:
                item_estoque.quantidade_em_estoque += item_orcamento.quantidade or 1

    db.session.delete(orcamento)
    db.session.commit()
    flash(f"Orçamento {codigo} removido.", "sucesso")
    return redirect(url_for("web.orcamentos_lista"))


@web_bp.route("/orcamentos/<int:orcamento_id>/imprimir")
def orcamentos_imprimir(orcamento_id):
    """Modelo de orçamento com o logo da MGT, pronto para imprimir ou
    salvar como PDF e enviar pelo WhatsApp. Não mostra custo nem lucro —
    só as informações que o cliente deve ver."""
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    return render_template("orcamentos/imprimir.html", orcamento=orcamento)


# --------------------------------------------------------------------------
# Estoque (itens em branco usados na personalização, com custo e quantidade)
# --------------------------------------------------------------------------
@web_bp.route("/estoque")
def estoque_lista():
    itens = ItemEstoque.query.order_by(ItemEstoque.tipo_produto).all()
    valor_total_estoque = round(sum((item.custo_unitario or 0) * (item.quantidade_em_estoque or 0) for item in itens), 2)
    return render_template("estoque/list.html", itens=itens, valor_total_estoque=valor_total_estoque)


@web_bp.route("/estoque/novo", methods=["GET", "POST"])
def estoque_novo():
    tipos_ja_cadastrados = {item.tipo_produto for item in ItemEstoque.query.all()}
    tipos_disponiveis = [t for t in TIPOS_PRODUTO if t not in tipos_ja_cadastrados]

    if request.method == "POST":
        tipo_produto = request.form.get("tipo_produto", "").strip()
        erro = None
        if not tipo_produto:
            erro = "Selecione o tipo de produto."
        elif tipo_produto in tipos_ja_cadastrados:
            erro = f'Já existe um item de estoque cadastrado para "{tipo_produto}".'

        if erro:
            flash(erro, "erro")
            return render_template(
                "estoque/form.html", item=None, form=request.form, tipos_produto=tipos_disponiveis
            )

        custo_unitario = float((request.form.get("custo_unitario") or "0").replace(",", "."))
        quantidade_em_estoque = int(request.form.get("quantidade_em_estoque") or 0)
        estoque_minimo = int(request.form.get("estoque_minimo") or 0)

        item = ItemEstoque(
            tipo_produto=tipo_produto,
            custo_unitario=custo_unitario,
            quantidade_em_estoque=quantidade_em_estoque,
            estoque_minimo=estoque_minimo,
        )
        db.session.add(item)
        db.session.commit()
        flash(f'Item de estoque "{tipo_produto}" cadastrado com sucesso.', "sucesso")
        return redirect(url_for("web.estoque_lista"))

    return render_template("estoque/form.html", item=None, form={}, tipos_produto=tipos_disponiveis)


@web_bp.route("/estoque/<int:item_id>/editar", methods=["GET", "POST"])
def estoque_editar(item_id):
    item = ItemEstoque.query.get_or_404(item_id)

    if request.method == "POST":
        item.custo_unitario = float((request.form.get("custo_unitario") or "0").replace(",", "."))
        item.quantidade_em_estoque = int(request.form.get("quantidade_em_estoque") or 0)
        item.estoque_minimo = int(request.form.get("estoque_minimo") or 0)
        db.session.commit()
        flash(f'Item de estoque "{item.tipo_produto}" atualizado com sucesso.', "sucesso")
        return redirect(url_for("web.estoque_lista"))

    return render_template("estoque/form.html", item=item, form=None, tipos_produto=[item.tipo_produto])


@web_bp.route("/estoque/<int:item_id>/excluir", methods=["POST"])
def estoque_excluir(item_id):
    item = ItemEstoque.query.get_or_404(item_id)
    tipo_produto = item.tipo_produto
    db.session.delete(item)
    db.session.commit()
    flash(f'Item de estoque "{tipo_produto}" removido.', "sucesso")
    return redirect(url_for("web.estoque_lista"))


# --------------------------------------------------------------------------
# Perdas de estoque (produto quebrado, com defeito etc. — sem relação com
# orçamentos, já que o cliente continua com o pedido normalmente)
# --------------------------------------------------------------------------
@web_bp.route("/estoque/perdas")
def estoque_perdas_lista():
    perdas = PerdaEstoque.query.order_by(PerdaEstoque.data_registro.desc()).all()
    valor_total_perdido = round(sum(p.valor_perdido for p in perdas), 2)
    return render_template("estoque/perdas_list.html", perdas=perdas, valor_total_perdido=valor_total_perdido)


@web_bp.route("/estoque/perdas/nova", methods=["GET", "POST"])
def estoque_perdas_nova():
    itens = ItemEstoque.query.order_by(ItemEstoque.tipo_produto).all()

    if request.method == "POST":
        tipo_produto = request.form.get("tipo_produto", "").strip()
        quantidade = _parse_quantidade(request.form.get("quantidade", ""))
        motivo = request.form.get("motivo", "").strip() or None
        custo_personalizacao_texto = request.form.get("custo_personalizacao") or None

        erro = None
        if not tipo_produto:
            erro = "Selecione o produto."
        elif quantidade is None:
            erro = "Quantidade inválida — informe um número inteiro maior que zero."

        custo_personalizacao = 0.0
        if erro is None and custo_personalizacao_texto:
            try:
                custo_personalizacao = float(custo_personalizacao_texto.replace(",", "."))
            except ValueError:
                erro = "Custo da personalização inválido — informe um valor numérico."

        if erro:
            flash(erro, "erro")
            return render_template("estoque/perdas_form.html", itens=itens, form=request.form)

        perda = _registrar_perda_estoque(tipo_produto, quantidade, motivo, custo_personalizacao)
        if perda is None:
            return render_template("estoque/perdas_form.html", itens=itens, form=request.form)

        db.session.commit()
        flash(f'Perda de {quantidade} un. de "{tipo_produto}" registrada.', "sucesso")
        return redirect(url_for("web.estoque_perdas_lista"))

    tipo_pre_selecionado = request.args.get("tipo_produto", "")
    return render_template("estoque/perdas_form.html", itens=itens, form={"tipo_produto": tipo_pre_selecionado})


@web_bp.route("/estoque/perdas/<int:perda_id>/excluir", methods=["POST"])
def estoque_perdas_excluir(perda_id):
    perda = PerdaEstoque.query.get_or_404(perda_id)
    item = ItemEstoque.query.filter_by(tipo_produto=perda.tipo_produto).first()
    if item:
        item.quantidade_em_estoque += perda.quantidade
    db.session.delete(perda)
    db.session.commit()
    flash("Registro de perda removido e quantidade devolvida ao estoque.", "sucesso")
    return redirect(url_for("web.estoque_perdas_lista"))


# --------------------------------------------------------------------------
# Consulta (busca por nome do cliente e por código do orçamento)
# --------------------------------------------------------------------------
@web_bp.route("/consulta")
def consulta():
    return render_template("consulta.html")


# --------------------------------------------------------------------------
# Dashboard (análise de dados)
# --------------------------------------------------------------------------
@web_bp.route("/dashboard")
def dashboard():
    data_inicio, data_fim = _resolver_intervalo_datas(request.args)
    return render_template("dashboard.html", data_inicio=data_inicio, data_fim=data_fim)
