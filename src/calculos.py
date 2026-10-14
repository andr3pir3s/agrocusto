"""Regras de negócio: funções puras (recebem dados e devolvem resultados)."""
from src.constantes import (
    LIMITE_CONCENTRACAO_CATEGORIA,
    LIMITE_CUSTO_HA_ACIMA_MEDIA,
    LIMITE_MARGEM_APERTADA,
)
from src.formatacao import moeda, numero, percentual


def arredondar(valor):
    return round(valor, 2)


def custo_total(custos, id_talhao=None):
    """Soma os custos; se id_talhao for informado, só os daquele talhão."""
    total = sum(
        c["valor"] for c in custos if id_talhao is None or c["talhao_id"] == id_talhao
    )
    return arredondar(total)


def custo_por_categoria(custos, id_talhao=None):
    """Devolve um dicionário {categoria: total}, do maior para o menor."""
    soma = {}
    for c in custos:
        if id_talhao is not None and c["talhao_id"] != id_talhao:
            continue
        soma[c["categoria"]] = soma.get(c["categoria"], 0.0) + c["valor"]
    ordenado = sorted(soma.items(), key=lambda item: item[1], reverse=True)
    return {categoria: arredondar(valor) for categoria, valor in ordenado}


def analisar_talhao(talhao, custos):
    """Calcula custo, receita, margem e ponto de equilíbrio de um talhão."""
    total = custo_total(custos, talhao["id"])
    producao = talhao["area_ha"] * talhao["produtividade_sc_ha"]
    receita = arredondar(producao * talhao["preco_saca"])
    margem = arredondar(receita - total)
    return {
        "custo_total": total,
        "custo_ha": arredondar(total / talhao["area_ha"]),
        "producao_sc": arredondar(producao),
        "receita": receita,
        "margem": margem,
        "margem_pct": arredondar(margem / receita * 100) if receita > 0 else 0.0,
        # Preço mínimo da saca e produtividade mínima para "empatar" (margem zero).
        "preco_equilibrio": arredondar(total / producao) if producao > 0 else 0.0,
        "produtividade_equilibrio": arredondar(
            total / (talhao["area_ha"] * talhao["preco_saca"])
        ),
        "por_categoria": custo_por_categoria(custos, talhao["id"]),
    }


def consolidar(talhoes, custos):
    """Totais de toda a propriedade."""
    area = sum(t["area_ha"] for t in talhoes)
    receita = sum(analisar_talhao(t, custos)["receita"] for t in talhoes)
    ids = {t["id"] for t in talhoes}
    total = arredondar(sum(c["valor"] for c in custos if c["talhao_id"] in ids))
    margem = arredondar(receita - total)
    return {
        "area_ha": arredondar(area),
        "custo_total": total,
        "custo_ha": arredondar(total / area) if area > 0 else 0.0,
        "receita": arredondar(receita),
        "margem": margem,
        "margem_pct": arredondar(margem / receita * 100) if receita > 0 else 0.0,
    }


def gerar_alertas(talhoes, custos):
    """Alertas automáticos. Devolve uma lista de tuplas (nível, mensagem)."""
    alertas = []
    analises = {t["id"]: analisar_talhao(t, custos) for t in talhoes}

    custo_ha_por_cultura = {}
    for t in talhoes:
        a = analises[t["id"]]
        if a["custo_total"] > 0:
            custo_ha_por_cultura.setdefault(t["cultura"], []).append(a["custo_ha"])

    for t in talhoes:
        a = analises[t["id"]]
        nome = t["nome"]

        if a["custo_total"] == 0:
            alertas.append(("INFO", f"{nome}: nenhum custo lançado; a margem é só a receita estimada."))
            continue

        if a["margem"] < 0:
            alertas.append((
                "CRITICO",
                f"{nome}: margem NEGATIVA ({moeda(a['margem'])}). Para empatar, a saca precisa de "
                f"{moeda(a['preco_equilibrio'])} (esperado: {moeda(t['preco_saca'])}) ou "
                f"{numero(a['produtividade_equilibrio'])} sc/ha (esperado: {numero(t['produtividade_sc_ha'])}).",
            ))
        elif a["margem_pct"] < LIMITE_MARGEM_APERTADA * 100:
            alertas.append((
                "ATENCAO",
                f"{nome}: margem apertada ({percentual(a['margem_pct'])}). "
                f"Qualquer queda de preço ou produtividade pode gerar prejuízo.",
            ))

        valores = custo_ha_por_cultura.get(t["cultura"], [])
        if len(valores) >= 2:
            media = sum(valores) / len(valores)
            if a["custo_ha"] > media * (1 + LIMITE_CUSTO_HA_ACIMA_MEDIA):
                alertas.append((
                    "ATENCAO",
                    f"{nome}: custo/ha ({moeda(a['custo_ha'])}) está acima da média dos talhões de "
                    f"{t['cultura']} ({moeda(media)}).",
                ))

        categoria, valor = next(iter(a["por_categoria"].items()))
        if valor / a["custo_total"] > LIMITE_CONCENTRACAO_CATEGORIA:
            alertas.append((
                "INFO",
                f"{nome}: {percentual(valor / a['custo_total'] * 100)} do custo está em '{categoria}'.",
            ))

    return alertas
