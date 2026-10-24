/**
 * Formulário de novo item de estoque: quando a pessoa escolhe a opção
 * "+ Cadastrar um novo produto" no lugar de um item da pré-lista, mostra
 * um campo de texto para digitar o nome do produto novo.
 */
(function () {
    const NOVO_PRODUTO_VALOR = "__novo__";

    const selectTipo = document.getElementById("tipo_produto");
    const campoNovoProduto = document.getElementById("campo-novo-tipo-produto");
    const inputNovoProduto = document.getElementById("novo_tipo_produto");

    if (!selectTipo || selectTipo.tagName !== "SELECT" || !campoNovoProduto || !inputNovoProduto) {
        return;
    }

    function atualizarVisibilidade() {
        const mostrar = selectTipo.value === NOVO_PRODUTO_VALOR;
        campoNovoProduto.hidden = !mostrar;
        inputNovoProduto.required = mostrar;
        if (mostrar) {
            inputNovoProduto.focus();
        }
    }

    selectTipo.addEventListener("change", atualizarVisibilidade);
    atualizarVisibilidade();
})();
