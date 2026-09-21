/**
 * Autopreenchimento de endereço a partir do CEP, usando a API pública ViaCEP.
 * Demonstra o uso de uma API externa via JavaScript (fetch).
 */
(function () {
    const campoCep = document.getElementById("cep");
    if (!campoCep) return;

    const campoEndereco = document.getElementById("endereco");
    const campoBairro = document.getElementById("bairro");
    const campoCidade = document.getElementById("cidade");
    const campoUf = document.getElementById("uf");
    const statusCep = document.querySelector("[data-status-cep]");

    function definirStatus(mensagem) {
        if (statusCep) statusCep.textContent = mensagem;
    }

    async function buscarEnderecoPorCep(cep) {
        const cepLimpo = cep.replace(/\D/g, "");
        if (cepLimpo.length !== 8) {
            definirStatus("");
            return;
        }

        definirStatus("Buscando endereço...");
        try {
            const resposta = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
            if (!resposta.ok) throw new Error("Falha na consulta do CEP.");
            const dados = await resposta.json();

            if (dados.erro) {
                definirStatus("CEP não encontrado.");
                return;
            }

            if (campoEndereco && !campoEndereco.value) campoEndereco.value = dados.logradouro || "";
            if (campoBairro) campoBairro.value = dados.bairro || "";
            if (campoCidade) campoCidade.value = dados.localidade || "";
            if (campoUf) campoUf.value = dados.uf || "";

            definirStatus("Endereço preenchido automaticamente a partir do CEP.");
        } catch (erro) {
            definirStatus("Não foi possível consultar o CEP agora. Preencha o endereço manualmente.");
        }
    }

    campoCep.addEventListener("blur", () => buscarEnderecoPorCep(campoCep.value));
})();
