/**
 * Consulta de clientes (por nome) e orçamentos (por código),
 * consumindo a API REST interna (/api/clientes e /api/orcamentos).
 */
(function () {
    const formCliente = document.getElementById("form-busca-cliente");
    const campoNomeCliente = document.getElementById("busca-nome-cliente");
    const resultadoClientes = document.getElementById("resultado-clientes");

    const formOrcamento = document.getElementById("form-busca-orcamento");
    const campoCodigoOrcamento = document.getElementById("busca-codigo-orcamento");
    const resultadoOrcamentos = document.getElementById("resultado-orcamentos");

    function escapeHtml(texto) {
        const div = document.createElement("div");
        div.textContent = texto == null ? "" : String(texto);
        return div.innerHTML;
    }

    async function buscarClientes(nome) {
        resultadoClientes.textContent = "Buscando...";
        try {
            const resposta = await fetch(`/api/clientes?nome=${encodeURIComponent(nome)}`);
            const clientes = await resposta.json();

            if (!clientes.length) {
                resultadoClientes.innerHTML = "<p>Nenhum cliente encontrado com esse nome.</p>";
                return;
            }

            const linhas = clientes.map((c) => `
                <tr>
                    <td>${escapeHtml(c.nome)}</td>
                    <td>${escapeHtml(c.telefone || "—")}</td>
                    <td>${escapeHtml(c.email || "—")}</td>
                    <td><a href="/orcamentos?cliente_id=${encodeURIComponent(c.id)}" title="Ver orçamentos de ${escapeHtml(c.nome)}">${c.quantidade_orcamentos}</a></td>
                </tr>`).join("");

            resultadoClientes.innerHTML = `
                <table>
                    <caption class="sr-only">Resultado da busca de clientes</caption>
                    <thead>
                        <tr><th scope="col">Nome</th><th scope="col">Telefone</th><th scope="col">E-mail</th><th scope="col">Orçamentos</th></tr>
                    </thead>
                    <tbody>${linhas}</tbody>
                </table>`;
        } catch (erro) {
            resultadoClientes.innerHTML = "<p>Não foi possível concluir a busca agora. Tente novamente.</p>";
        }
    }

    async function buscarOrcamentos(codigo) {
        resultadoOrcamentos.textContent = "Buscando...";
        try {
            const resposta = await fetch(`/api/orcamentos?codigo=${encodeURIComponent(codigo)}`);
            const orcamentos = await resposta.json();

            if (!orcamentos.length) {
                resultadoOrcamentos.innerHTML = "<p>Nenhum orçamento encontrado com esse código.</p>";
                return;
            }

            const linhas = orcamentos.map((o) => `
                <tr>
                    <td>${escapeHtml(o.codigo)}</td>
                    <td>${escapeHtml(o.cliente_nome)}</td>
                    <td>${escapeHtml(o.resumo_produtos)}</td>
                    <td>${o.valor_estimado ? "R$ " + Number(o.valor_estimado).toFixed(2) : "—"}</td>
                    <td><span class="badge">${escapeHtml(o.status)}</span></td>
                    <td>${escapeHtml(o.data_solicitacao || "—")}</td>
                </tr>`).join("");

            resultadoOrcamentos.innerHTML = `
                <table>
                    <caption class="sr-only">Resultado da busca de orçamentos</caption>
                    <thead>
                        <tr>
                            <th scope="col">Código</th><th scope="col">Cliente</th><th scope="col">Produto</th>
                            <th scope="col">Valor</th><th scope="col">Status</th><th scope="col">Solicitado em</th>
                        </tr>
                    </thead>
                    <tbody>${linhas}</tbody>
                </table>`;
        } catch (erro) {
            resultadoOrcamentos.innerHTML = "<p>Não foi possível concluir a busca agora. Tente novamente.</p>";
        }
    }

    if (formCliente) {
        formCliente.addEventListener("submit", (evento) => {
            evento.preventDefault();
            buscarClientes(campoNomeCliente.value.trim());
        });
    }

    if (formOrcamento) {
        formOrcamento.addEventListener("submit", (evento) => {
            evento.preventDefault();
            buscarOrcamentos(campoCodigoOrcamento.value.trim());
        });
    }
})();
