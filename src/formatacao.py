"""Funções de formatação no padrão brasileiro (R$ 1.234,56 e dd/mm/aaaa)."""
from datetime import date


def numero(valor, casas=2):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor):
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {numero(abs(valor))}"


def percentual(valor):
    return f"{numero(valor, 1)}%"


def data_br(data_iso):
    return date.fromisoformat(data_iso).strftime("%d/%m/%Y")
