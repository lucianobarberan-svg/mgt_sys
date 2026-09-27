# MGT Sys

Sistema web de gestão de clientes e orçamentos para a **MGT Presentes Personalizados**,
empresa especializada em personalização de canecas, chaveiros, canetas, copos, descansos
de mouse, quebra-cabeças, camisetas, bonés, chinelos, azulejos, ecobags e garrafas.

Projeto desenvolvido no âmbito do **Projeto Integrador em Computação II** da Univesp,
substituindo o controle de clientes e pedidos atualmente feito em planilhas de Excel.

## Requisitos atendidos

- **Framework web**: Flask (Python)
- **Banco de dados relacional**: SQLite (via SQLAlchemy), pronto para trocar por PostgreSQL em produção
- **Script web (JavaScript)**: busca dinâmica de clientes/orçamentos e dashboard com gráficos (Chart.js)
- **Uso de API**:
  - API REST própria (`/api/clientes`, `/api/orcamentos`, `/api/dashboard/resumo`)
  - Consumo de API externa (ViaCEP) para autopreenchimento de endereço pelo CEP
- **Acessibilidade**: HTML semântico, labels associados aos campos, skip-link, `aria-live` nos
  resultados de busca e no dashboard, alternativa textual para os gráficos, foco visível, `lang="pt-BR"`
- **Controle de versão**: Git
- **Testes**: pytest (modelos e endpoints da API)
- **Nuvem**: aplicação pronta para deploy (ver seção *Deploy em nuvem*)
- **Análise de dados (opcional)**: dashboard com orçamentos por status e por tipo de produto

## Funcionalidades

- Cadastro, edição, exclusão e listagem de clientes, com busca por nome direto na lista
- Cadastro, edição, exclusão e listagem de orçamentos (vinculados a um cliente), com geração
  automática de código (`ORC-0001`, `ORC-0002`, ...), busca por código e filtro por período
  (data inicial/final, com atalhos para "mês atual" e "mês anterior") direto na lista
- **Mais de um produto por orçamento**: um mesmo pedido pode ter várias linhas de produto
  (ex.: 2 canecas + 3 chaveiros), adicionadas ou removidas dinamicamente no formulário
  ("+ Adicionar produto"); a lista de orçamentos mostra o resumo de todos os produtos do
  pedido
- Consulta de cliente pelo nome e de orçamento pelo código (página dedicada de consulta),
  com atalho para ver todos os orçamentos de um cliente encontrado
- **Controle de estoque com valores**: cadastro dos produtos em branco (caneca, chaveiro
  etc.) com custo unitário, quantidade em estoque e estoque mínimo, com aviso de "estoque
  baixo"
- **Custo e lucro por orçamento**: ao informar também o custo da personalização (tinta,
  material), o sistema calcula em tempo real o custo total (somando todos os produtos do
  pedido) e o lucro líquido estimado, com base no custo de cada produto cadastrado em Estoque
- **Baixa automática de estoque**: quando um orçamento é aprovado (ou avança para "Em
  produção", "Concluído" ou "Entregue"), o sistema dá baixa na quantidade de cada produto do
  pedido e trava o custo naquele momento; se o pedido for cancelado depois, a quantidade
  volta para o estoque
- **Perdas de estoque**: registro de produtos que quebraram ou saíram com defeito durante a
  personalização — dá baixa no estoque e no lucro do negócio, mas não tem nenhuma relação com
  o orçamento do cliente (o pedido dele continua normalmente); aparece em um card próprio no
  Dashboard, com o lucro líquido já descontado das perdas
- **Relatório de custos e lucros no Dashboard**: receita, custo e lucro confirmados, além da
  margem de lucro, considerando apenas os orçamentos já confirmados
- **Modelo de orçamento para WhatsApp**: página de orçamento com o logo da MGT, pronta para
  imprimir ou salvar como PDF e enviar ao cliente pelo WhatsApp (sem mostrar custo ou lucro);
  também é possível compartilhar o orçamento direto pelo WhatsApp sem precisar imprimir,
  tanto na lista de orçamentos quanto na página de impressão
- **Ações em ícones**: editar, imprimir, compartilhar no WhatsApp, registrar perda e excluir
  são todos botões de ícone (lápis, impressora, seta, alerta, X vermelho), no mesmo padrão em
  Orçamentos, Estoque e Clientes
- Dashboard com gráficos de orçamentos por status e por tipo de produto

## Estrutura do projeto

```
mgt_sys/
├── app/
│   ├── __init__.py        # application factory
│   ├── models.py          # modelos Cliente e Orcamento (SQLAlchemy)
│   ├── routes/
│   │   ├── web.py         # páginas HTML (CRUD, consulta, dashboard)
│   │   └── api.py         # API REST (JSON)
│   ├── templates/         # templates Jinja2
│   └── static/
│       ├── css/style.css
│       └── js/             # busca, autopreenchimento de CEP, dashboard
├── tests/                  # testes automatizados (pytest)
├── config.py                # configurações (development/testing/production)
├── run.py                   # ponto de entrada local (desenvolvimento)
├── wsgi.py                  # ponto de entrada para produção (gunicorn)
└── requirements.txt
```

## Como rodar localmente

### Windows (jeito mais simples)

Dê duplo clique em **`iniciar_mgt.bat`**. Na primeira vez, ele instala tudo o que é
necessário automaticamente (pode levar cerca de um minuto); nas próximas vezes, abre
direto. O navegador abre sozinho em `http://127.0.0.1:5000`. Para fechar o sistema, basta
fechar a janela preta que abriu.

Dica: clique com o botão direito em `iniciar_mgt.bat` → **Enviar para → Área de trabalho
(criar atalho)** para ter um ícone no Desktop que abre o sistema com um clique.

### Manualmente (Windows/Mac/Linux)

```bash
# 1. Criar e ativar um ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Rodar a aplicação
python run.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite é criado automaticamente em
`instance/mgt.sqlite3` na primeira execução.

## Como rodar os testes

```bash
python -m pytest -v
```

## Deploy em nuvem

O projeto já está pronto para publicação em serviços de hospedagem em nuvem com plano
gratuito. Algumas opções:

### Render (recomendado, mais simples)

1. Crie uma conta em [render.com](https://render.com) e conecte o repositório do GitHub.
2. Crie um **Web Service** apontando para este repositório.
3. Configure:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn wsgi:app`
4. (Opcional, mais robusto) Crie um banco **PostgreSQL** gratuito no próprio Render e
   defina a variável de ambiente `DATABASE_URL` no Web Service com a *Internal Database URL*
   fornecida — a aplicação já lê essa variável automaticamente (`config.py`).
5. Defina também a variável `SECRET_KEY` com um valor aleatório.

### Railway / PythonAnywhere

O mesmo princípio se aplica: instalar `requirements.txt`, rodar `gunicorn wsgi:app`
(Railway) ou configurar a aplicação WSGI apontando para `wsgi.py` (PythonAnywhere), e
opcionalmente definir `DATABASE_URL` para um banco PostgreSQL gerenciado.

## API

| Método | Rota                          | Descrição                                              |
|--------|-------------------------------|---------------------------------------------------------|
| GET    | `/api/clientes?nome=`         | Lista/busca clientes por nome                           |
| GET    | `/api/clientes/<id>`          | Detalhe de um cliente (com seus orçamentos)              |
| GET    | `/api/orcamentos?codigo=`     | Lista/busca orçamentos por código                        |
| GET    | `/api/orcamentos?nome_cliente=` | Busca orçamentos pelo nome do cliente                  |
| GET    | `/api/orcamentos/<id>`        | Detalhe de um orçamento                                  |
| GET    | `/api/dashboard/resumo`       | Totais e agregações para o dashboard                     |

## Autor

Luciano Vicente Barberan — Projeto Integrador em Computação II, Univesp, Polo São Carlos.
Orientadora: Profa. Dra. Thamires dos Santos Mota.
