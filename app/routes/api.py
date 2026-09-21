from flask import Blueprint, jsonify, request

from app.models import Cliente, Orcamento

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
    orcamentos = Orcamento.query.all()

    por_status = {}
    por_tipo = {}
    valor_total = 0.0

    for o in orcamentos:
        por_status[o.status] = por_status.get(o.status, 0) + 1
        por_tipo[o.tipo_produto] = por_tipo.get(o.tipo_produto, 0) + 1
        if o.valor_estimado:
            valor_total += o.valor_estimado

    return jsonify(
        {
            "total_orcamentos": len(orcamentos),
            "total_clientes": Cliente.query.count(),
            "valor_total_estimado": round(valor_total, 2),
            "por_status": por_status,
            "por_tipo_produto": por_tipo,
        }
    )
