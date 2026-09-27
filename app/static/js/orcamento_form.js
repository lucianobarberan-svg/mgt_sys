/**
 * Formulário de orçamento: permite adicionar/remover linhas de produto
 * (um orçamento pode ter mais de um produto) e calcula, em tempo real,
 * uma prévia do custo dos produtos (a partir do estoque), do custo total
 * e do lucro líquido estimado — só uma estimativa visual, o valor que
 * realmente conta é travado no servidor quando o orçamento vira
 * "Aprovado".
 */
(function () {
    const itensEstoque = window.MGT_ITENS_ESTOQUE || {};

    const listaItens = document.getElementById("lista-itens-orcamento");
    const botaoAdicionar = document.getElementById("botao-adicionar-item");
    const campoValorEstimado = document.getElementById("valor_estimado");
    const campoCustoPersonalizacao = document.getElementById("custo_personalizacao");

    const saidaCustoProduto = document.getElementById("preview-custo-produto");
    const saidaCustoTotal = document.getElementById("preview-custo-total");
    const saidaLucro = document.getElementById("preview-lucro");

    if (!listaItens || !saidaLucro) {
        return;
    }

    let contadorLinhas = listaItens.querySelectorAll(".linha-item-orcamento").length;

    function paraNumero(valor) {
        const numero = parseFloat(String(valor || "").replace(",", "."));
        return Number.isFinite(numero) ? numero : 0;
    }

    function formatarMoeda(valor) {
        return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }

    function atualizarBotoesRemover() {
        const linhas = listaItens.querySelectorAll(".linha-item-orcamento");
        linhas.forEach((linha) => {
            const botao = linha.querySelector(".botao-remover-item");
            if (botao) {
                botao.disabled = linhas.length <= 1;
            }
        });
    }

    function atualizarPreview() {
        const linhas = listaItens.querySelectorAll(".linha-item-orcamento");
        let custoProdutosTotal = 0;
        let algumSemEstoque = false;

        linhas.forEach((linha) => {
            const selectTipo = linha.querySelector("select");
            const inputQuantidade = linha.querySelector("input[type=number]");
            const tipoProduto = selectTipo ? selectTipo.value : "";
            if (!tipoProduto) {
                return;
            }
            const quantidade = Math.max(1, paraNumero(inputQuantidade ? inputQuantidade.value : 1) || 1);

            const custoUnitario = Object.prototype.hasOwnProperty.call(itensEstoque, tipoProduto)
                ? itensEstoque[tipoProduto]
                : null;

            if (custoUnitario === null) {
                algumSemEstoque = true;
            } else {
                custoProdutosTotal += custoUnitario * quantidade;
            }
        });

        const custoPersonalizacao = paraNumero(campoCustoPersonalizacao ? campoCustoPersonalizacao.value : 0);
        const valorEstimado = paraNumero(campoValorEstimado ? campoValorEstimado.value : 0);

        saidaCustoProduto.textContent = algumSemEstoque
            ? `${formatarMoeda(custoProdutosTotal)} (algum produto sem estoque)`
            : formatarMoeda(custoProdutosTotal);

        const custoTotal = custoProdutosTotal + custoPersonalizacao;
        saidaCustoTotal.textContent = formatarMoeda(custoTotal);

        const lucro = valorEstimado - custoTotal;
        saidaLucro.textContent = formatarMoeda(lucro);
        saidaLucro.style.color = lucro < 0 ? "var(--cor-erro)" : "var(--cor-sucesso)";
    }

    function criarLinha() {
        const primeiraLinha = listaItens.querySelector(".linha-item-orcamento");
        if (!primeiraLinha) {
            return;
        }
        const novaLinha = primeiraLinha.cloneNode(true);
        contadorLinhas += 1;

        novaLinha.querySelectorAll("select, input").forEach((campo) => {
            if (campo.tagName === "SELECT") {
                campo.value = "";
                campo.id = `item_tipo_produto_${contadorLinhas}`;
            } else if (campo.type === "number") {
                campo.value = 1;
                campo.id = `item_quantidade_${contadorLinhas}`;
            }
        });

        listaItens.appendChild(novaLinha);
        atualizarBotoesRemover();
        atualizarPreview();
    }

    if (botaoAdicionar) {
        botaoAdicionar.addEventListener("click", criarLinha);
    }

    listaItens.addEventListener("click", (evento) => {
        const botaoRemover = evento.target.closest(".botao-remover-item");
        if (!botaoRemover) {
            return;
        }
        const linhas = listaItens.querySelectorAll(".linha-item-orcamento");
        if (linhas.length <= 1) {
            return;
        }
        botaoRemover.closest(".linha-item-orcamento").remove();
        atualizarBotoesRemover();
        atualizarPreview();
    });

    listaItens.addEventListener("input", atualizarPreview);
    listaItens.addEventListener("change", atualizarPreview);

    [campoValorEstimado, campoCustoPersonalizacao]
        .filter(Boolean)
        .forEach((campo) => {
            campo.addEventListener("input", atualizarPreview);
            campo.addEventListener("change", atualizarPreview);
        });

    atualizarBotoesRemover();
    atualizarPreview();
})();
