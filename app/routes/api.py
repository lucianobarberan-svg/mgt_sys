from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from app.models import STATUS_COM_BAIXA_ESTOQUE, Cliente, ItemEstoque, Orcamento

api_bp = Blueprint("api", __name__)


# --------------------------------------------------------------------------
# Clientes
# --------------------------------------------------------------------------
@api_bp.route("/clientes", methods=["GET"])
def api_clientes():
    """Lista clientes, com busca opcional por nome (?nome=...)."""
    nome = request.args.get("nome", "").strip()
    query = Cliente.query
    if nome:
        query = query.filter(Cliente.nome.ilike(f"%{nome}%"))
    clientes = query.order_by(Cliente.nome).all()
    return jsonify([c.to_dict() for c in clientes])


@api_bp.route("/clientes/<int:cliente_id>", methods=["GET"])
def api_cliente_detalhe(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    dados = cliente.to_dict()
    dados["orcamentos"] = [o.to_dict() for o in cliente.orcamentos]
    return jsonify(dados)


# --------------------------------------------------------------------------
# Orçamentos
# --------------------------------------------------------------------------
@api_bp.route("/orcamentos", methods=["GET"])
def api_orcamentos():
    """Lista orçamentos, com busca opcional por código (?codigo=...)
    e/ou por nome do cliente (?nome_cliente=...)."""
    codigo = request.args.get("codigo", "").strip()
    nome_cliente = request.args.get("nome_cliente", "").strip()

    query = Orcamento.query
    if codigo:
        query = query.filter(Orcamento.codigo.ilike(f"%{codigo}%"))
    if nome_cliente:
        query = query.join(Cliente).filter(Cliente.nome.ilike(f"%{nome_cliente}%"))

    orcamentos = query.order_by(Orcamento.data_solicitacao.desc()).all()
    return jsonify([o.to_dict() for o in orcamentos])


@api_bp.route("/orcamentos/<int:orcamento_id>", methods=["GET"])
def api_orcamento_detalhe(orcamento_id):
    orcamento = Orcamento.query.get_or_404(orcamento_id)
    return jsonify(orcamento.to_dict())


# --------------------------------------------------------------------------
# Dashboard / análise de dados
# --------------------------------------------------------------------------
@api_bp.route("/dashboard/resumo", methods=["GET"])
def api_dashboard_resumo():
    """Resumo agregado dos orçamentos, com filtro opcional por período
    (?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD)."""
    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()

    query = Orcamento.query
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query = query.filter(Orcamento.data_solicitacao >= dt_inicio)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            # Inclui o dia final inteiro (até 23:59:59).
            query = query.filter(Orcamento.data_solicitacao < dt_fim + timedelta(days=1))
        except ValueError:
            pass

    orcamentos = query.all()

    por_status = {}
    por_tipo = {}
    valor_total = 0.0

    # O relatório de custo/lucro só considera orçamentos confirmados (a
    # partir de "Aprovado"), pois é aí que o custo do produto é travado a
    # partir do estoque — um orçamento "Solicitado" ainda não tem custo real.
    receita_confirmada = 0.0
    custo_confirmado = 0.0
    lucro_por_tipo = {}

    for o in orcamentos:
        por_status[o.status] = por_status.get(o.status, 0) + 1
        por_tipo[o.tipo_produto] = por_tipo.get(o.tipo_produto, 0) + 1
        if o.valor_estimado:
            valor_total += o.valor_estimado

        if o.status in STATUS_COM_BAIXA_ESTOQUE:
            receita_confirmada += o.valor_estimado or 0
            custo_confirmado += o.custo_total
            lucro_por_tipo[o.tipo_produto] = lucro_por_tipo.get(o.tipo_produto, 0) + o.lucro_liquido

    lucro_confirmado = receita_confirmada - custo_confirmado
    margem_percentual = round((lucro_confirmado / receita_confirmada * 100), 1) if receita_confirmada else 0.0

    return jsonify(
        {
            "total_orcamentos": len(orcamentos),
            "total_clientes": Cliente.query.count(),
            "valor_total_estimado": round(valor_total, 2),
            "por_status": por_status,
            "por_tipo_produto": por_tipo,
            "financeiro": {
                "receita_confirmada": round(receita_confirmada, 2),
                "custo_confirmado": round(custo_confirmado, 2),
                "lucro_confirmado": round(lucro_confirmado, 2),
                "margem_percentual": margem_percentual,
                "lucro_por_tipo_produto": {k: round(v, 2) for k, v in lucro_por_tipo.items()},
            },
        }
    )


# --------------------------------------------------------------------------
# Estoque
# --------------------------------------------------------------------------
@api_bp.route("/estoque/resumo", methods=["GET"])
def api_estoque_resumo():
    itens = ItemEstoque.query.all()
    valor_total = sum((i.custo_unitario or 0) * (i.quantidade_em_estoque or 0) for i in itens)
    itens_estoque_baixo = [i.tipo_produto for i in itens if i.quantidade_em_estoque <= (i.estoque_minimo or 0)]
    return jsonify(
        {
            "valor_total_em_estoque": round(valor_total, 2),
            "itens_estoque_baixo": itens_estoque_baixo,
        }
    )
