from datetime import date, datetime
from urllib.parse import quote

from app import db

TIPOS_PRODUTO = [
    "Caneca personalizada",
    "Chaveiro personalizado",
    "Caneta personalizada",
    "Copo personalizado",
    "Descanso de mouse personalizado",
    "Quebra-cabeça personalizado",
    "Camiseta personalizada",
    "Boné personalizado",
    "Chinelo personalizado",
    "Azulejo personalizado",
    "Ecobag personalizada",
    "Garrafa personalizada",
    "Outro",
]

STATUS_ORCAMENTO = [
    "Solicitado",
    "Em análise",
    "Aprovado",
    "Em produção",
    "Concluído",
    "Entregue",
    "Cancelado",
]

# Status a partir dos quais consideramos que o pedido foi confirmado: é
# quando o estoque é baixado e o custo passa a contar no relatório
# financeiro do Dashboard.
STATUS_COM_BAIXA_ESTOQUE = {"Aprovado", "Em produção", "Concluído", "Entregue"}


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    cep = db.Column(db.String(9))
    endereco = db.Column(db.String(200))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    orcamentos = db.relationship(
        "Orcamento", backref="cliente", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "telefone": self.telefone,
            "email": self.email,
            "cep": self.cep,
            "endereco": self.endereco,
            "bairro": self.bairro,
            "cidade": self.cidade,
            "uf": self.uf,
            "data_cadastro": self.data_cadastro.strftime("%d/%m/%Y") if self.data_cadastro else None,
            "quantidade_orcamentos": len(self.orcamentos),
        }

    def __repr__(self):
        return f"<Cliente {self.id} {self.nome}>"


class ItemEstoque(db.Model):
    """Um item de estoque: o produto em branco (ex.: caneca lisa) que é
    comprado por um custo e depois personalizado para revenda."""

    __tablename__ = "itens_estoque"

    id = db.Column(db.Integer, primary_key=True)
    tipo_produto = db.Column(db.String(80), unique=True, nullable=False)
    custo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    quantidade_em_estoque = db.Column(db.Integer, nullable=False, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_produto": self.tipo_produto,
            "custo_unitario": self.custo_unitario,
            "quantidade_em_estoque": self.quantidade_em_estoque,
            "estoque_minimo": self.estoque_minimo,
            "valor_total_em_estoque": round((self.custo_unitario or 0) * (self.quantidade_em_estoque or 0), 2),
            "estoque_baixo": self.quantidade_em_estoque <= (self.estoque_minimo or 0),
        }

    def __repr__(self):
        return f"<ItemEstoque {self.tipo_produto}>"


class PerdaEstoque(db.Model):
    """Registro de uma perda de estoque — um produto que quebrou ou saiu
    com defeito durante a personalização, por exemplo. Só dá baixa na
    quantidade em estoque; não tem nenhuma relação com orçamentos, porque
    o pedido do cliente continua normalmente com outra unidade."""

    __tablename__ = "perdas_estoque"

    id = db.Column(db.Integer, primary_key=True)
    tipo_produto = db.Column(db.String(80), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    custo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    motivo = db.Column(db.String(200))
    data_registro = db.Column(db.DateTime, default=datetime.now)

    @property
    def valor_perdido(self):
        return round((self.custo_unitario or 0) * (self.quantidade or 1), 2)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_produto": self.tipo_produto,
            "quantidade": self.quantidade,
            "custo_unitario": self.custo_unitario,
            "valor_perdido": self.valor_perdido,
            "motivo": self.motivo,
            "data_registro": self.data_registro.strftime("%d/%m/%Y") if self.data_registro else None,
        }

    def __repr__(self):
        return f"<PerdaEstoque {self.tipo_produto} x{self.quantidade}>"


class ItemOrcamento(db.Model):
    """Um produto dentro de um orçamento. Um orçamento pode ter mais de um
    produto (ex.: 2 canecas + 1 chaveiro no mesmo pedido do cliente)."""

    __tablename__ = "itens_orcamento"

    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey("orcamentos.id"), nullable=False)
    tipo_produto = db.Column(db.String(80), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    # Custo unitário do produto no estoque, travado no momento em que o
    # orçamento é aprovado (mesma lógica que já existia por orçamento).
    custo_unitario_produto = db.Column(db.Float)

    @property
    def custo_total(self):
        return round((self.custo_unitario_produto or 0) * (self.quantidade or 1), 2)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_produto": self.tipo_produto,
            "quantidade": self.quantidade,
            "custo_unitario_produto": self.custo_unitario_produto,
            "custo_total": self.custo_total,
        }

    def __repr__(self):
        return f"<ItemOrcamento {self.tipo_produto} x{self.quantidade}>"


class Orcamento(db.Model):
    __tablename__ = "orcamentos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    descricao = db.Column(db.Text)
    valor_estimado = db.Column(db.Float)
    custo_personalizacao = db.Column(db.Float)
    estoque_baixado = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(30), nullable=False, default="Solicitado")
    data_solicitacao = db.Column(db.DateTime, default=datetime.now)
    prazo_entrega = db.Column(db.Date)

    itens = db.relationship(
        "ItemOrcamento",
        backref="orcamento",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ItemOrcamento.id",
    )

    @staticmethod
    def gerar_codigo():
        """Gera um código sequencial no formato ORC-0001."""
        ultimo = Orcamento.query.order_by(Orcamento.id.desc()).first()
        proximo_numero = (ultimo.id + 1) if ultimo else 1
        return f"ORC-{proximo_numero:04d}"

    @property
    def custo_total(self):
        custo_produtos = sum(item.custo_total for item in self.itens)
        return round(custo_produtos + (self.custo_personalizacao or 0), 2)

    @property
    def lucro_liquido(self):
        return round((self.valor_estimado or 0) - self.custo_total, 2)

    @property
    def resumo_produtos(self):
        """Texto curto com os produtos do orçamento, ex.:
        "Caneca personalizada (x2), Chaveiro personalizado (x1)"."""
        return ", ".join(f"{item.tipo_produto} (x{item.quantidade})" for item in self.itens)

    @property
    def mensagem_whatsapp(self):
        """Texto pronto para compartilhar o orçamento pelo WhatsApp — sem
        nenhum dado de custo ou lucro, só o que o cliente deve ver."""
        linhas_produtos = [f"- {item.tipo_produto} (quantidade: {item.quantidade})" for item in self.itens]
        linhas = [
            f"Orçamento {self.codigo} — MGT Presentes Personalizados",
            f"Cliente: {self.cliente.nome}" if self.cliente else None,
            "Produtos:",
            *linhas_produtos,
            (
                f"Valor total: R$ {self.valor_estimado:.2f}".replace(".", ",")
                if self.valor_estimado
                else "Valor total: a combinar"
            ),
            f"Prazo de entrega: {self.prazo_entrega.strftime('%d/%m/%Y')}" if self.prazo_entrega else None,
            f"Status: {self.status}",
        ]
        return "\n".join(linha for linha in linhas if linha)

    @property
    def whatsapp_url(self):
        """Link "clique para conversar" do WhatsApp (wa.me) já com a
        mensagem do orçamento preenchida. Se o cliente tiver telefone
        cadastrado, abre a conversa direto com ele; senão, abre o seletor
        de contato do WhatsApp com a mensagem pronta para colar."""
        numero = "".join(c for c in (self.cliente.telefone or "") if c.isdigit()) if self.cliente else ""
        if numero and not numero.startswith("55"):
            numero = "55" + numero
        mensagem = quote(self.mensagem_whatsapp)
        return f"https://wa.me/{numero}?text={mensagem}"

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "cliente_id": self.cliente_id,
            "cliente_nome": self.cliente.nome if self.cliente else None,
            "itens": [item.to_dict() for item in self.itens],
            "resumo_produtos": self.resumo_produtos,
            "descricao": self.descricao,
            "valor_estimado": self.valor_estimado,
            "custo_personalizacao": self.custo_personalizacao,
            "custo_total": self.custo_total,
            "lucro_liquido": self.lucro_liquido,
            "status": self.status,
            "data_solicitacao": self.data_solicitacao.strftime("%d/%m/%Y") if self.data_solicitacao else None,
            "prazo_entrega": self.prazo_entrega.strftime("%d/%m/%Y") if self.prazo_entrega else None,
        }

    def __repr__(self):
        return f"<Orcamento {self.codigo}>"
