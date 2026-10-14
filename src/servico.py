"""Operações sobre os dados: mantém a memória, o Oracle e os arquivos sincronizados.

O 'estado' é um dicionário com a conexão e as duas tabelas de memória:
    {"conn": conexão Oracle ou None, "talhoes": [dict, ...], "custos": [dict, ...]}
"""
from datetime import datetime

from src import arquivos, banco
from src.validacao import custo_valido, talhao_valido

CAMPOS_TALHAO = ("nome", "cultura", "area_ha", "produtividade_sc_ha", "preco_saca", "data_plantio")
CAMPOS_CUSTO = ("talhao_id", "categoria", "descricao", "valor", "data")


def criar_estado():
    return {"conn": None, "talhoes": [], "custos": []}


def nome_do_modo(estado):
    return "Oracle" if estado["conn"] else "Offline (arquivo JSON)"


def _arquivo_backup(estado):
    return arquivos.BACKUP_ORACLE if estado["conn"] else arquivos.BACKUP_OFFLINE


def contar_talhoes_offline():
    """Quantos talhões existem no backup do modo offline (0 se não houver)."""
    try:
        return len(arquivos.carregar_json(arquivos.BACKUP_OFFLINE).get("talhoes", []))
    except (OSError, ValueError):
        return 0


def carregar_dados(estado):
    """Carrega do Oracle (se conectado) ou do backup JSON do modo offline."""
    if estado["conn"]:
        banco.criar_tabelas(estado["conn"])
        estado["talhoes"] = banco.listar_talhoes(estado["conn"])
        estado["custos"] = banco.listar_custos(estado["conn"])
        return
    try:
        dados = arquivos.carregar_json(arquivos.BACKUP_OFFLINE)
    except (FileNotFoundError, ValueError):
        return
    estado["talhoes"] = [t for t in dados.get("talhoes", []) if talhao_valido(t)]
    ids = {t["id"] for t in estado["talhoes"]}
    estado["custos"] = [
        c for c in dados.get("custos", []) if custo_valido(c) and c["talhao_id"] in ids
    ]


def montar_exportacao(estado):
    return {
        "versao": 1,
        "exportado_em": datetime.now().isoformat(timespec="seconds"),
        "talhoes": estado["talhoes"],
        "custos": estado["custos"],
    }


def _depois_de_alterar(estado, mensagem):
    """Grava o backup JSON e uma linha no histórico (arquivo texto)."""
    try:
        arquivos.salvar_json(_arquivo_backup(estado), montar_exportacao(estado))
        arquivos.registrar_historico(mensagem)
    except OSError as erro:
        print(f"  [AVISO] Não foi possível gravar os arquivos locais: {erro}")


def _proximo_id(registros):
    return max((r["id"] for r in registros), default=0) + 1


def buscar_talhao(estado, id_talhao):
    return next((t for t in estado["talhoes"] if t["id"] == id_talhao), None)


def buscar_custo(estado, id_custo):
    return next((c for c in estado["custos"] if c["id"] == id_custo), None)


def _nome_unico(estado, nome):
    """Evita nomes de talhão repetidos (ex.: ao importar duas vezes o mesmo JSON)."""
    existentes = {t["nome"].lower() for t in estado["talhoes"]}
    candidato, numero = nome, 1
    while candidato.lower() in existentes:
        numero += 1
        sufixo = f" ({numero})"
        candidato = nome[: 50 - len(sufixo)] + sufixo
    return candidato


def adicionar_talhao(estado, dados):
    novo = dict(dados)
    if estado["conn"]:
        novo["id"] = banco.inserir_talhao(estado["conn"], novo)
    else:
        novo["id"] = _proximo_id(estado["talhoes"])
    estado["talhoes"].append(novo)
    _depois_de_alterar(estado, f"Talhão {novo['id']} cadastrado: {novo['nome']}")
    return novo


def alterar_talhao(estado, talhao, novos_dados):
    atualizado = {**talhao, **novos_dados}
    if estado["conn"]:
        banco.atualizar_talhao(estado["conn"], atualizado)
    talhao.update(novos_dados)
    _depois_de_alterar(estado, f"Talhão {talhao['id']} alterado: {talhao['nome']}")


def excluir_talhao(estado, talhao):
    """Remove o talhão e seus custos. Devolve quantos custos foram removidos."""
    if estado["conn"]:
        banco.excluir_talhao(estado["conn"], talhao["id"])
    antes = len(estado["custos"])
    estado["custos"] = [c for c in estado["custos"] if c["talhao_id"] != talhao["id"]]
    estado["talhoes"].remove(talhao)
    removidos = antes - len(estado["custos"])
    _depois_de_alterar(estado, f"Talhão {talhao['id']} excluído ({removidos} custos removidos)")
    return removidos


def adicionar_custo(estado, dados):
    novo = dict(dados)
    if estado["conn"]:
        novo["id"] = banco.inserir_custo(estado["conn"], novo)
    else:
        novo["id"] = _proximo_id(estado["custos"])
    estado["custos"].append(novo)
    _depois_de_alterar(estado, f"Custo {novo['id']} lançado no talhão {novo['talhao_id']}: {novo['valor']:.2f}")
    return novo


def alterar_custo(estado, custo, novos_dados):
    atualizado = {**custo, **novos_dados}
    if estado["conn"]:
        banco.atualizar_custo(estado["conn"], atualizado)
    custo.update(novos_dados)
    _depois_de_alterar(estado, f"Custo {custo['id']} alterado")


def excluir_custo(estado, custo):
    if estado["conn"]:
        banco.excluir_custo(estado["conn"], custo["id"])
    estado["custos"].remove(custo)
    _depois_de_alterar(estado, f"Custo {custo['id']} excluído")


def importar_dados(estado, dados):
    """Acrescenta registros de um JSON. Devolve (talhões, custos, ignorados).

    Os IDs do arquivo são trocados pelos IDs novos (do Oracle ou da memória),
    e cada custo é religado ao seu talhão pelo mapa {id antigo: id novo}.
    """
    mapa_ids = {}
    ignorados = 0
    custos_importados = 0
    for t in dados.get("talhoes", []):
        if not talhao_valido(t):
            ignorados += 1
            continue
        registro = {campo: t[campo] for campo in CAMPOS_TALHAO}
        registro["nome"] = _nome_unico(estado, registro["nome"].strip())
        criado = adicionar_talhao(estado, registro)
        mapa_ids[t["id"]] = criado["id"]
    for c in dados.get("custos", []):
        if not custo_valido(c) or c["talhao_id"] not in mapa_ids:
            ignorados += 1
            continue
        registro = {campo: c[campo] for campo in CAMPOS_CUSTO}
        registro["talhao_id"] = mapa_ids[c["talhao_id"]]
        adicionar_custo(estado, registro)
        custos_importados += 1
    return len(mapa_ids), custos_importados, ignorados
