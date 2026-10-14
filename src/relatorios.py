"""Apresentação dos dados. As funções 'linhas_*' devolvem listas de texto;
'exibir' é o procedimento que imprime. Assim o mesmo conteúdo vai para a tela e para o TXT."""
from datetime import datetime

from src import calculos
from src.formatacao import data_br, moeda, numero, percentual

LARGURA = 78
SIMBOLO_ALERTA = {"CRITICO": "[!!]", "ATENCAO": "[! ]", "INFO": "[i ]"}


def exibir(linhas):
    print("\n".join(linhas))


def titulo(texto):
    return ["", "=" * LARGURA, texto.upper().center(LARGURA), "=" * LARGURA]


def subtitulo(texto):
    return ["", texto, "-" * len(texto)]


def tabela(cabecalhos, linhas, alinhamentos=None):
    """Monta uma tabela de texto alinhada. alinhamentos: '<' esquerda, '>' direita."""
    alinhamentos = alinhamentos or ["<"] * len(cabecalhos)
    textos = [[str(celula) for celula in linha] for linha in linhas]
    larguras = [
        max([len(str(cab))] + [len(linha[i]) for linha in textos])
        for i, cab in enumerate(cabecalhos)
    ]

    def montar(celulas):
        return " | ".join(
            f"{c:{a}{w}}" for c, a, w in zip(celulas, alinhamentos, larguras)
        )

    separador = "-+-".join("-" * w for w in larguras)
    return [montar(cabecalhos), separador] + [montar(l) for l in textos]


def barra(percentual_valor, largura=20):
    return "#" * round(percentual_valor / 100 * largura)


def linhas_talhoes(talhoes):
    if not talhoes:
        return ["Nenhum talhão cadastrado."]
    dados = [
        [t["id"], t["nome"], t["cultura"], numero(t["area_ha"]), numero(t["produtividade_sc_ha"]),
         moeda(t["preco_saca"]), data_br(t["data_plantio"])]
        for t in talhoes
    ]
    return tabela(
        ["ID", "Talhão", "Cultura", "Área (ha)", "Prod. (sc/ha)", "Preço/saca", "Plantio"],
        dados, ["<", "<", "<", ">", ">", ">", "<"],
    )


def linhas_custos(custos, talhoes):
    if not custos:
        return ["Nenhum custo lançado."]
    nomes = {t["id"]: t["nome"] for t in talhoes}
    dados = [
        [c["id"], nomes.get(c["talhao_id"], "?"), c["categoria"], c["descricao"],
         moeda(c["valor"]), data_br(c["data"])]
        for c in sorted(custos, key=lambda c: (c["data"], c["id"]))
    ]
    return tabela(
        ["ID", "Talhão", "Categoria", "Descrição", "Valor", "Data"],
        dados, ["<", "<", "<", "<", ">", "<"],
    )


def linhas_analise_talhao(talhao, analise):
    linhas = subtitulo(
        f"Talhão {talhao['id']} - {talhao['nome']} | {talhao['cultura']} | "
        f"{numero(talhao['area_ha'])} ha | plantio {data_br(talhao['data_plantio'])}"
    )
    linhas += [
        f"Produção estimada ....: {numero(analise['producao_sc'])} sacas "
        f"({numero(talhao['produtividade_sc_ha'])} sc/ha)",
        f"Receita estimada .....: {moeda(analise['receita'])} "
        f"({moeda(talhao['preco_saca'])} por saca)",
        f"Custo total ..........: {moeda(analise['custo_total'])}",
        f"Custo por hectare ....: {moeda(analise['custo_ha'])}",
        f"Margem estimada ......: {moeda(analise['margem'])} ({percentual(analise['margem_pct'])})",
        "",
        "Ponto de equilíbrio (margem zero):",
        f"  - preço mínimo da saca .....: {moeda(analise['preco_equilibrio'])}",
        f"  - produtividade mínima .....: {numero(analise['produtividade_equilibrio'])} sc/ha",
    ]
    if analise["por_categoria"]:
        linhas += subtitulo("Custos por categoria")
        dados = []
        for categoria, valor in analise["por_categoria"].items():
            parte = valor / analise["custo_total"] * 100
            dados.append([categoria, moeda(valor), percentual(parte), barra(parte)])
        linhas += tabela(["Categoria", "Valor", "%", ""], dados, ["<", ">", ">", "<"])
    else:
        linhas.append("\n(Nenhum custo lançado para este talhão.)")
    return linhas


def linhas_painel(talhoes, custos):
    if not talhoes:
        return ["Nenhum talhão cadastrado."]
    dados = []
    for t in talhoes:
        a = calculos.analisar_talhao(t, custos)
        dados.append([
            t["id"], t["nome"], t["cultura"], numero(t["area_ha"]), moeda(a["custo_total"]),
            moeda(a["custo_ha"]), moeda(a["receita"]), moeda(a["margem"]), percentual(a["margem_pct"]),
        ])
    total = calculos.consolidar(talhoes, custos)
    dados.append([
        "", "TOTAL", "", numero(total["area_ha"]), moeda(total["custo_total"]), moeda(total["custo_ha"]),
        moeda(total["receita"]), moeda(total["margem"]), percentual(total["margem_pct"]),
    ])
    return tabela(
        ["ID", "Talhão", "Cultura", "Área (ha)", "Custo total", "Custo/ha", "Receita est.", "Margem", "Margem %"],
        dados, ["<", "<", "<", ">", ">", ">", ">", ">", ">"],
    )


def linhas_alertas(alertas):
    if not alertas:
        return ["Nenhum alerta: custos e margens dentro dos limites."]
    return [f"{SIMBOLO_ALERTA[nivel]} {mensagem}" for nivel, mensagem in alertas]


def relatorio_completo(talhoes, custos):
    linhas = titulo("AgroCusto - Relatório da safra")
    linhas.append(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas += subtitulo("Visão geral dos talhões") + linhas_painel(talhoes, custos)
    for t in talhoes:
        linhas += linhas_analise_talhao(t, calculos.analisar_talhao(t, custos))
    linhas += subtitulo("Alertas") + linhas_alertas(calculos.gerar_alertas(talhoes, custos))
    return linhas
