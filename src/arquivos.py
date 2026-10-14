"""Manipulação de arquivos: JSON (dados) e texto (histórico e relatórios)."""
import json
from datetime import datetime
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"
# Um backup por modo: assim os dados do modo offline nunca são sobrescritos pelo Oracle.
BACKUP_OFFLINE = PASTA_DADOS / "backup_offline.json"
BACKUP_ORACLE = PASTA_DADOS / "backup_oracle.json"
ARQUIVO_HISTORICO = PASTA_DADOS / "historico.txt"


def salvar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def carregar_json(caminho):
    """Lê um JSON. Lança FileNotFoundError ou ValueError (JSON inválido)."""
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, dict):
        raise ValueError("O arquivo JSON deve conter um objeto com 'talhoes' e 'custos'.")
    return dados


def salvar_texto(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


def registrar_historico(mensagem):
    """Acrescenta uma linha com data/hora ao histórico de operações."""
    ARQUIVO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as arquivo:
        arquivo.write(f"[{carimbo}] {mensagem}\n")


def ler_ultimas_linhas(caminho, quantidade=15):
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return [linha.rstrip("\n") for linha in arquivo.readlines()[-quantidade:]]
    except FileNotFoundError:
        return []


def listar_arquivos(extensao):
    if not PASTA_DADOS.exists():
        return []
    return sorted(p.name for p in PASTA_DADOS.glob(f"*{extensao}"))
