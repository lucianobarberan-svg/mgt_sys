/**
 * Formulário de orçamento: calcula, em tempo real, uma prévia do custo do
 * produto (a partir do estoque), do custo total e do lucro líquido
 * estimado — só uma estimativa visual, o valor que realmente conta é
 * travado no servidor quando o orçamento vira "Aprovado".
 */
(function () {
    const itensEstoque = window.MGT_ITENS_ESTOQUE || {};

    const campoTipoProduto = document.getElementById("tipo_produto");
    const campoQuantidade = document.getElementById("quantidade");
    const campoValorEstimado = document.getElementById("valor_estimado");
    const campoCustoPersonalizacao = document.getElementById("custo_personalizacao");

    const saidaCustoProduto = document.getElementById("preview-custo-produto");
    const saidaCustoTotal = document.getElementById("preview-custo-total");
    const saidaLucro = document.getElementById("preview-lucro");

    if (!campoTipoProduto || !saidaLucro) {
        return;
    }

    function paraNumero(valor) {
        const numero = parseFloat(String(valor || "").replace(",", "."));
        return Number.isFinite(numero) ? numero : 0;
    }

    function formatarMoeda(valor) {
        return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }

    function atualizarPreview() {
        const tipoProduto = campoTipoProduto.value;
        const quantidade = Math.max(1, paraNumero(campoQuantidade ? campoQuantidade.value : 1) || 1);
        const valorEstimado = paraNumero(campoValorEstimado ? campoValorEstimado.value : 0);
        const custoPersonalizacao = paraNumero(campoCustoPersonalizacao ? campoCustoPersonalizacao.value : 0);

        const custoUnitario = Object.prototype.hasOwnProperty.call(itensEstoque, tipoProduto)
            ? itensEstoque[tipoProduto]
            : null;

        if (custoUnitario === null) {
            saidaCustoProduto.textContent = tipoProduto ? "Sem item no estoque" : "—";
        } else {
            saidaCustoProduto.textContent = formatarMoeda(custoUnitario * quantidade);
        }

        const custoTotal = (custoUnitario || 0) * quantidade + custoPersonalizacao;
        saidaCustoTotal.textContent = formatarMoeda(custoTotal);

        const lucro = valorEstimado - custoTotal;
        saidaLucro.textContent = formatarMoeda(lucro);
        saidaLucro.style.color = lucro < 0 ? "var(--cor-erro)" : "var(--cor-sucesso)";
    }

    [campoTipoProduto, campoQuantidade, campoValorEstimado, campoCustoPersonalizacao]
        .filter(Boolean)
        .forEach((campo) => {
            campo.addEventListener("input", atualizarPreview);
            campo.addEventListener("change", atualizarPreview);
        });

    atualizarPreview();
})();
