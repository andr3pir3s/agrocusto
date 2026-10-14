"""Leitura e validação de tudo o que o usuário digita (e de dados importados)."""
import math
import re
from datetime import date, datetime

from src.constantes import (
    AREA_MAXIMA_HA, CATEGORIAS, CULTURAS, PRODUTIVIDADE_MAXIMA, VALOR_MAXIMO,
)
from src.formatacao import data_br, numero

PALAVRA_CANCELAR = "voltar"
ANO_MINIMO = 2000


class OperacaoCancelada(Exception):
    """Lançada quando o usuário digita 'voltar' em qualquer pergunta."""


def _ler(mensagem, conversor, padrao=None, texto_padrao=None):
    """Pergunta até receber um valor válido. ENTER devolve o padrão (se houver)."""
    sufixo = ""
    if padrao is not None:
        sufixo = f" [ENTER = {texto_padrao if texto_padrao is not None else padrao}]"
    while True:
        resposta = input(f"{mensagem}{sufixo}: ").strip()
        if resposta.lower() == PALAVRA_CANCELAR:
            raise OperacaoCancelada()
        if resposta == "" and padrao is not None:
            return padrao
        try:
            return conversor(resposta)
        except ValueError as erro:
            print(f"  [!] {erro}")


def ler_texto(mensagem, minimo=2, maximo=50, padrao=None, proibidos=()):
    def converter(r):
        if not minimo <= len(r) <= maximo:
            raise ValueError(f"Digite de {minimo} a {maximo} caracteres.")
        if not any(c.isalpha() for c in r):
            raise ValueError("Use pelo menos uma letra.")
        if r.lower() in proibidos:
            raise ValueError("Já existe um registro com esse nome.")
        return r

    return _ler(mensagem, converter, padrao)


def _texto_para_decimal(texto):
    limpo = texto.replace("R$", "").replace(" ", "")
    if "," in limpo:  # formato brasileiro: 1.234,56
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = float(limpo)
    except ValueError:
        raise ValueError("Digite um número válido (ex.: 12,5).") from None
    if not math.isfinite(valor):
        raise ValueError("Digite um número válido (ex.: 12,5).")
    return valor


def ler_decimal(mensagem, minimo, maximo, padrao=None):
    def converter(r):
        valor = _texto_para_decimal(r)
        if not minimo <= valor <= maximo:
            raise ValueError(f"O valor deve estar entre {numero(minimo)} e {numero(maximo)}.")
        return round(valor, 2)

    return _ler(mensagem, converter, padrao)


def ler_data(mensagem, padrao=None):
    """Lê dd/mm/aaaa e devolve 'aaaa-mm-dd'. O padrão também é 'aaaa-mm-dd'."""
    def converter(r):
        try:
            data = datetime.strptime(r, "%d/%m/%Y").date()
        except ValueError:
            raise ValueError("Data inválida. Use dd/mm/aaaa (ex.: 15/09/2026).") from None
        if not _data_no_intervalo(data):
            raise ValueError(f"Informe uma data entre {ANO_MINIMO} e o próximo ano.")
        return data.isoformat()

    texto = data_br(padrao) if padrao else None
    return _ler(mensagem, converter, padrao, texto)


def ler_escolha(mensagem, opcoes, padrao=None):
    """Mostra as opções numeradas e devolve o item escolhido."""
    for posicao, opcao in enumerate(opcoes, start=1):
        print(f"  {posicao}) {opcao}")

    def converter(r):
        if not r.isdigit() or not 1 <= int(r) <= len(opcoes):
            raise ValueError(f"Escolha um número de 1 a {len(opcoes)}.")
        return opcoes[int(r) - 1]

    return _ler(mensagem, converter, padrao)


def ler_id(mensagem, ids_validos, permitir_zero=False):
    def converter(r):
        if not r.isdigit():
            raise ValueError("Digite apenas o número do ID.")
        valor = int(r)
        if valor == 0 and permitir_zero:
            return 0
        if valor not in ids_validos:
            raise ValueError("ID não encontrado. Confira a lista acima.")
        return valor

    return _ler(mensagem, converter)


def confirmar(mensagem):
    def converter(r):
        if r.lower() not in ("s", "n"):
            raise ValueError("Responda com 's' ou 'n'.")
        return r.lower() == "s"

    return _ler(f"{mensagem} (s/n)", converter)


def ler_nome_arquivo(mensagem, extensao, padrao):
    """Aceita só letras, números, '_' e '-' (evita caminhos perigosos)."""
    def converter(r):
        nome = r[: -len(extensao)] if r.lower().endswith(extensao) else r
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", nome):
            raise ValueError("Use apenas letras, números, '_' ou '-' (até 40 caracteres).")
        return nome + extensao

    return _ler(mensagem, converter, padrao)


# ---------- validação de registros importados de JSON ----------

def _data_no_intervalo(data):
    return date(ANO_MINIMO, 1, 1) <= data <= date(date.today().year + 1, 12, 31)


def _data_iso_valida(texto):
    try:
        return _data_no_intervalo(date.fromisoformat(texto))
    except (TypeError, ValueError):
        return False


def _numero_no_limite(valor, maximo):
    """Número real (não booleano), finito, maior que zero e até o limite."""
    return (
        isinstance(valor, (int, float))
        and not isinstance(valor, bool)
        and math.isfinite(valor)
        and 0 < valor <= maximo
    )


def _texto_valido(valor, minimo, maximo):
    return isinstance(valor, str) and minimo <= len(valor.strip()) <= maximo


def talhao_valido(t):
    try:
        return (
            isinstance(t["id"], int)
            and _texto_valido(t["nome"], 2, 50)
            and t["cultura"] in CULTURAS
            and _numero_no_limite(t["area_ha"], AREA_MAXIMA_HA)
            and _numero_no_limite(t["produtividade_sc_ha"], PRODUTIVIDADE_MAXIMA)
            and _numero_no_limite(t["preco_saca"], VALOR_MAXIMO)
            and _data_iso_valida(t["data_plantio"])
        )
    except (KeyError, TypeError):
        return False


def custo_valido(c):
    try:
        return (
            isinstance(c["id"], int)
            and isinstance(c["talhao_id"], int)
            and c["categoria"] in CATEGORIAS
            and _texto_valido(c["descricao"], 3, 100)
            and _numero_no_limite(c["valor"], VALOR_MAXIMO)
            and _data_iso_valida(c["data"])
        )
    except (KeyError, TypeError):
        return False
