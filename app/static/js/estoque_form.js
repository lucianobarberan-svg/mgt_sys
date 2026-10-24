/**
 * Formulário de novo item de estoque: a lista de produtos pré-cadastrados
 * é só um atalho pra preencher o nome — ao escolher um produto nela, o
 * campo de texto "Tipo de produto" é preenchido com esse nome e fica
 * selecionado, pronto pra ser ajustado ali mesmo (por exemplo, renomeado)
 * antes de salvar, junto com a quantidade. Quem preferir digitar direto o
 * nome de um produto que não está na lista também pode.
 */
(function () {
    const selectAtalho = document.getElementById("tipo_produto_atalho");
    const inputTipoProduto = document.getElementById("tipo_produto");

    if (!selectAtalho || !inputTipoProduto) {
        return;
    }

    selectAtalho.addEventListener("change", function () {
        if (!selectAtalho.value) {
            return;
        }
        inputTipoProduto.value = selectAtalho.value;
        inputTipoProduto.focus();
        inputTipoProduto.select();
    });
})();
