"""Leitura opcional do arquivo .env (sem dependências externas)."""
import os
from pathlib import Path

ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


def interpretar_env(texto):
    """Converte o conteúdo de um .env em dicionário {CHAVE: valor}.

    Linhas em branco ou iniciadas por '#' são ignoradas. Aspas ao redor do
    valor são removidas. Não há comentário no fim da linha (a senha pode ter '#').
    """
    variaveis = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            valor = valor[1:-1]
        if chave.strip():
            variaveis[chave.strip()] = valor
    return variaveis


def carregar_env(caminho=ARQUIVO_ENV):
    """Carrega o .env para os.environ sem sobrescrever variáveis já definidas.

    Devolve True se o arquivo existia."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return False
    for chave, valor in interpretar_env(texto).items():
        os.environ.setdefault(chave, valor)
    return True
