/**
 * Dashboard de análise de dados: busca o resumo agregado na API
 * (/api/dashboard/resumo) e desenha os gráficos com Chart.js.
 * Também gera uma versão em texto/tabela (oculta visualmente) para
 * leitores de tela, já que gráficos em canvas não são acessíveis por padrão.
 */
(function () {
    const corPrimaria = "#1e4f58";
    const paleta = ["#1e4f58", "#2f707a", "#c6a15b", "#5a9099", "#8fbabf", "#0d2b30", "#a9c9a0"];

    function formatarMoeda(valor) {
        return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }

    function preencherAlternativaTextual(elementoId, titulo, dados) {
        const container = document.getElementById(elementoId);
        if (!container) return;
        const itens = Object.entries(dados)
            .map(([chave, valor]) => `<li>${chave}: ${valor}</li>`)
            .join("");
        container.innerHTML = `<h3>${titulo} (versão em texto)</h3><ul>${itens}</ul>`;
    }

    async function carregarDashboard() {
        try {
            const campoDataInicio = document.getElementById("filtro-data-inicio");
            const campoDataFim = document.getElementById("filtro-data-fim");
            const parametros = new URLSearchParams();
            if (campoDataInicio && campoDataInicio.value) {
                parametros.set("data_inicio", campoDataInicio.value);
            }
            if (campoDataFim && campoDataFim.value) {
                parametros.set("data_fim", campoDataFim.value);
            }
            const query = parametros.toString();

            const resposta = await fetch(`/api/dashboard/resumo${query ? "?" + query : ""}`);
            const dados = await resposta.json();

            document.getElementById("num-clientes").textContent = dados.total_clientes;
            document.getElementById("num-orcamentos").textContent = dados.total_orcamentos;
            document.getElementById("num-valor").textContent = formatarMoeda(dados.valor_total_estimado || 0);

            const financeiro = dados.financeiro || {};
            const elLucro = document.getElementById("fin-lucro");
            document.getElementById("fin-receita").textContent = formatarMoeda(financeiro.receita_confirmada || 0);
            document.getElementById("fin-custo").textContent = formatarMoeda(financeiro.custo_confirmado || 0);
            elLucro.textContent = formatarMoeda(financeiro.lucro_confirmado || 0);
            elLucro.style.color = (financeiro.lucro_confirmado || 0) < 0 ? "var(--cor-erro)" : "var(--cor-sucesso)";
            document.getElementById("fin-margem").textContent = `${(financeiro.margem_percentual || 0).toLocaleString("pt-BR")}%`;

            const rotulosStatus = Object.keys(dados.por_status);
            const valoresStatus = Object.values(dados.por_status);
            preencherAlternativaTextual("tabela-status-alt", "Orçamentos por status", dados.por_status);

            new Chart(document.getElementById("grafico-status"), {
                type: "bar",
                data: {
                    labels: rotulosStatus,
                    datasets: [{
                        label: "Quantidade de orçamentos",
                        data: valoresStatus,
                        backgroundColor: corPrimaria,
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
                },
            });

            const rotulosTipo = Object.keys(dados.por_tipo_produto);
            const valoresTipo = Object.values(dados.por_tipo_produto);
            preencherAlternativaTextual("tabela-tipo-alt", "Orçamentos por tipo de produto", dados.por_tipo_produto);

            new Chart(document.getElementById("grafico-tipo"), {
                type: "pie",
                data: {
                    labels: rotulosTipo,
                    datasets: [{
                        data: valoresTipo,
                        backgroundColor: paleta,
                    }],
                },
                options: { responsive: true },
            });
        } catch (erro) {
            document.getElementById("resumo-numeros").innerHTML =
                "<p>Não foi possível carregar os dados do dashboard agora.</p>";
        }
    }

    carregarDashboard();
})();
