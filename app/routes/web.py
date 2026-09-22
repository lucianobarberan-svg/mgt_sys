from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import STATUS_ORCAMENTO, TIPOS_PRODUTO, Cliente, Orcamento

web_bp = Blueprint("web", __name__)


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

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_produto = request.form.get("tipo_produto", "").strip()
        erro = None
        if not cliente_id:
            erro = "Selecione um cliente."
        elif not tipo_produto:
            erro = "Selecione o tipo de produto."

        if erro:
            flash(erro, "erro")
            return render_template(
                "orcamentos/form.html",
                orcamento=None,
                form=request.form,
                clientes=clientes,
                tipos_produto=TIPOS_PRODUTO,
                status_opcoes=STATUS_ORCAMENTO,
            )

        prazo_entrega = request.form.get("prazo_entrega") or None
        if prazo_entrega:
            prazo_entrega = datetime.strptime(prazo_entrega, "%Y-%m-%d").date()

        valor_estimado = request.form.get("valor_estimado") or None
        if valor_estimado:
            valor_estimado = float(valor_estimado.replace(",", "."))

        orcamento = Orcamento(
            codigo=Orcamento.gerar_codigo(),
            cliente_id=int(cliente_id),
            tipo_produto=tipo_produto,
            descricao=request.form.get("descricao", "").strip() or None,
            valor_estimado=valor_estimado,
            status=request.form.get("status") or "Solicitado",
            prazo_entrega=prazo_entrega,
        )
        db.session.add(orcamento)
        db.session.commit()
        flash(f"Orçamento {orcamento.codigo} cadastrado com sucesso.", "sucesso")
        return redirect(url_for("web.orcamentos_lista"))

    return render_template(
        "orcamentos/form.html",
        orcamento=None,
        form={},
        clientes=clientes,
        tipos_produto=TIPOS_PRODUTO,
        status_opcoes=STATUS_ORCAMENTO,
    )


@web_bp.route("/orcamentos/<int:orcamento_id>/editar", methods=["GET", "POST"])
def orcamentos_editar(orcamento_id):
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    clientes = Cliente.query.order_by(Cliente.nome).all()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_produto = request.form.get("tipo_produto", "").strip()
        erro = None
        if not cliente_id:
            erro = "Selecione um cliente."
        elif not tipo_produto:
            erro = "Selecione o tipo de produto."

        if erro:
            flash(erro, "erro")
            return render_template(
                "orcamentos/form.html",
                orcamento=orcamento,
                form=request.form,
                clientes=clientes,
                tipos_produto=TIPOS_PRODUTO,
                status_opcoes=STATUS_ORCAMENTO,
            )

        prazo_entrega = request.form.get("prazo_entrega") or None
        if prazo_entrega:
            prazo_entrega = datetime.strptime(prazo_entrega, "%Y-%m-%d").date()

        valor_estimado = request.form.get("valor_estimado") or None
        if valor_estimado:
            valor_estimado = float(valor_estimado.replace(",", "."))

        orcamento.cliente_id = int(cliente_id)
        orcamento.tipo_produto = tipo_produto
        orcamento.descricao = request.form.get("descricao", "").strip() or None
        orcamento.valor_estimado = valor_estimado
        orcamento.status = request.form.get("status") or orcamento.status
        orcamento.prazo_entrega = prazo_entrega
        db.session.commit()
        flash(f"Orçamento {orcamento.codigo} atualizado com sucesso.", "sucesso")
        return redirect(url_for("web.orcamentos_lista"))

    return render_template(
        "orcamentos/form.html",
        orcamento=orcamento,
        form=None,
        clientes=clientes,
        tipos_produto=TIPOS_PRODUTO,
        status_opcoes=STATUS_ORCAMENTO,
    )


@web_bp.route("/orcamentos/<int:orcamento_id>/excluir", methods=["POST"])
def orcamentos_excluir(orcamento_id):
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    codigo = orcamento.codigo
    db.session.delete(orcamento)
    db.session.commit()
    flash(f"Orçamento {codigo} removido.", "sucesso")
    return redirect(url_for("web.orcamentos_lista"))


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
