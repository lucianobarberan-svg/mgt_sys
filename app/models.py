from datetime import date, datetime

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


class Orcamento(db.Model):
    __tablename__ = "orcamentos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    tipo_produto = db.Column(db.String(80), nullable=False)
    descricao = db.Column(db.Text)
    valor_estimado = db.Column(db.Float)
    status = db.Column(db.String(30), nullable=False, default="Solicitado")
    data_solicitacao = db.Column(db.DateTime, default=datetime.now)
    prazo_entrega = db.Column(db.Date)

    @staticmethod
    def gerar_codigo():
        """Gera um código sequencial no formato ORC-0001."""
        ultimo = Orcamento.query.order_by(Orcamento.id.desc()).first()
        proximo_numero = (ultimo.id + 1) if ultimo else 1
        return f"ORC-{proximo_numero:04d}"

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "cliente_id": self.cliente_id,
            "cliente_nome": self.cliente.nome if self.cliente else None,
            "tipo_produto": self.tipo_produto,
            "descricao": self.descricao,
            "valor_estimado": self.valor_estimado,
            "status": self.status,
            "data_solicitacao": self.data_solicitacao.strftime("%d/%m/%Y") if self.data_solicitacao else None,
            "prazo_entrega": self.prazo_entrega.strftime("%d/%m/%Y") if self.prazo_entrega else None,
        }

    def __repr__(self):
        return f"<Orcamento {self.codigo}>"
