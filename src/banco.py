"""Acesso ao Oracle (biblioteca python-oracledb). Todas as funções fazem commit/rollback."""
from datetime import date
from functools import wraps
from pathlib import Path

try:
    import oracledb
except ImportError:  # permite rodar em modo offline sem a biblioteca
    oracledb = None

ARQUIVO_SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
ORA_TABELA_JA_EXISTE = 955
TEMPO_LIMITE_CONEXAO_S = 10
DICA_SERVIDOR = "Servidor inalcançável. Confira host e porta do DSN, sua internet ou a VPN."


class ErroBanco(Exception):
    """Erro amigável de banco de dados, pronto para ser exibido ao usuário."""


# (códigos que identificam o erro, dica em português). Vale a primeira que casar.
DICAS_DE_ERRO = (
    (("ORA-01017",), "Usuário ou senha inválidos."),
    (("ORA-28000",), "A conta Oracle está bloqueada. Procure o administrador do banco."),
    (("ORA-12514", "ORA-12505", "DPY-6001"),
     "O serviço do DSN não foi encontrado. Confira o nome depois da barra (ex.: host:1521/ORCL)."),
    (("ORA-12541", "ORA-12170", "ORA-12154", "DPY-6005", "DPY-6000"), DICA_SERVIDOR),
    (("ORA-01031", "ORA-01950", "ORA-01536"),
     "O usuário não tem permissão ou espaço (cota) para criar tabelas."),
)


def traduzir_erro(texto):
    """Devolve uma dica em português para erros comuns do Oracle ('' se não houver)."""
    for codigos, dica in DICAS_DE_ERRO:
        if any(codigo in texto for codigo in codigos):
            return dica
    return ""


def _mensagem(prefixo, erro):
    detalhe = str(erro).strip().splitlines()[0] if str(erro).strip() else "sem detalhes"
    dica = traduzir_erro(str(erro))
    return f"{prefixo}: {dica} (detalhe técnico: {detalhe})" if dica else f"{prefixo}: {detalhe}"


def conectar(usuario, senha, dsn):
    if oracledb is None:
        raise ErroBanco("Biblioteca 'oracledb' não instalada. Rode: pip install oracledb")
    try:
        return oracledb.connect(
            user=usuario, password=senha, dsn=dsn, tcp_connect_timeout=TEMPO_LIMITE_CONEXAO_S
        )
    except oracledb.Error as erro:
        raise ErroBanco(_mensagem("Não foi possível conectar ao Oracle", erro)) from None
    except OSError as erro:  # host que não existe (DNS), recusa de conexão, tempo esgotado
        raise ErroBanco(
            f"Não foi possível conectar ao Oracle: {DICA_SERVIDOR} (detalhe técnico: {erro})"
        ) from None


def _protegido(funcao):
    """Decorador: em caso de erro faz rollback e converte para ErroBanco."""
    @wraps(funcao)
    def interna(conn, *args, **kwargs):
        try:
            return funcao(conn, *args, **kwargs)
        except oracledb.Error as erro:
            conn.rollback()
            raise ErroBanco(_mensagem("Erro no banco de dados", erro)) from None
    return interna


@_protegido
def criar_tabelas(conn):
    """Cria TB_TALHAO e TB_CUSTO se ainda não existirem."""
    comandos = []
    for bloco in ARQUIVO_SCHEMA.read_text(encoding="utf-8").split(";"):
        linhas = [l for l in bloco.splitlines() if l.strip() and not l.strip().startswith("--")]
        if linhas:
            comandos.append("\n".join(linhas))
    with conn.cursor() as cur:
        for comando in comandos:
            try:
                cur.execute(comando)
            except oracledb.DatabaseError as erro:
                (detalhe,) = erro.args
                if detalhe.code != ORA_TABELA_JA_EXISTE:
                    raise
    conn.commit()


# ---------- TALHÕES ----------

@_protegido
def listar_talhoes(conn):
    sql = (
        "SELECT ID_TALHAO, NM_TALHAO, DS_CULTURA, VL_AREA_HA, VL_PRODUTIVIDADE, "
        "VL_PRECO_SACA, DT_PLANTIO FROM TB_TALHAO ORDER BY ID_TALHAO"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        return [
            {
                "id": int(l[0]), "nome": l[1], "cultura": l[2],
                "area_ha": float(l[3]), "produtividade_sc_ha": float(l[4]),
                "preco_saca": float(l[5]), "data_plantio": l[6].date().isoformat(),
            }
            for l in cur.fetchall()
        ]


@_protegido
def inserir_talhao(conn, t):
    sql = (
        "INSERT INTO TB_TALHAO (NM_TALHAO, DS_CULTURA, VL_AREA_HA, VL_PRODUTIVIDADE, "
        "VL_PRECO_SACA, DT_PLANTIO) VALUES (:nome, :cultura, :area, :prod, :preco, :plantio) "
        "RETURNING ID_TALHAO INTO :novo_id"
    )
    with conn.cursor() as cur:
        novo_id = cur.var(int)
        cur.execute(sql, {
            "nome": t["nome"], "cultura": t["cultura"], "area": t["area_ha"],
            "prod": t["produtividade_sc_ha"], "preco": t["preco_saca"],
            "plantio": date.fromisoformat(t["data_plantio"]), "novo_id": novo_id,
        })
        valor = novo_id.getvalue()
    conn.commit()
    return int(valor[0] if isinstance(valor, list) else valor)


@_protegido
def atualizar_talhao(conn, t):
    sql = (
        "UPDATE TB_TALHAO SET NM_TALHAO = :nome, DS_CULTURA = :cultura, VL_AREA_HA = :area, "
        "VL_PRODUTIVIDADE = :prod, VL_PRECO_SACA = :preco, DT_PLANTIO = :plantio "
        "WHERE ID_TALHAO = :id"
    )
    with conn.cursor() as cur:
        cur.execute(sql, {
            "nome": t["nome"], "cultura": t["cultura"], "area": t["area_ha"],
            "prod": t["produtividade_sc_ha"], "preco": t["preco_saca"],
            "plantio": date.fromisoformat(t["data_plantio"]), "id": t["id"],
        })
    conn.commit()


@_protegido
def excluir_talhao(conn, id_talhao):
    """Os custos do talhão são removidos pelo ON DELETE CASCADE."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM TB_TALHAO WHERE ID_TALHAO = :id", {"id": id_talhao})
    conn.commit()


# ---------- CUSTOS ----------

@_protegido
def listar_custos(conn):
    sql = (
        "SELECT ID_CUSTO, ID_TALHAO, DS_CATEGORIA, DS_CUSTO, VL_CUSTO, DT_CUSTO "
        "FROM TB_CUSTO ORDER BY ID_CUSTO"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        return [
            {
                "id": int(l[0]), "talhao_id": int(l[1]), "categoria": l[2],
                "descricao": l[3], "valor": float(l[4]), "data": l[5].date().isoformat(),
            }
            for l in cur.fetchall()
        ]


@_protegido
def inserir_custo(conn, c):
    sql = (
        "INSERT INTO TB_CUSTO (ID_TALHAO, DS_CATEGORIA, DS_CUSTO, VL_CUSTO, DT_CUSTO) "
        "VALUES (:talhao, :categoria, :descricao, :valor, :data) RETURNING ID_CUSTO INTO :novo_id"
    )
    with conn.cursor() as cur:
        novo_id = cur.var(int)
        cur.execute(sql, {
            "talhao": c["talhao_id"], "categoria": c["categoria"], "descricao": c["descricao"],
            "valor": c["valor"], "data": date.fromisoformat(c["data"]), "novo_id": novo_id,
        })
        valor = novo_id.getvalue()
    conn.commit()
    return int(valor[0] if isinstance(valor, list) else valor)


@_protegido
def atualizar_custo(conn, c):
    sql = (
        "UPDATE TB_CUSTO SET ID_TALHAO = :talhao, DS_CATEGORIA = :categoria, DS_CUSTO = :descricao, "
        "VL_CUSTO = :valor, DT_CUSTO = :data WHERE ID_CUSTO = :id"
    )
    with conn.cursor() as cur:
        cur.execute(sql, {
            "talhao": c["talhao_id"], "categoria": c["categoria"], "descricao": c["descricao"],
            "valor": c["valor"], "data": date.fromisoformat(c["data"]), "id": c["id"],
        })
    conn.commit()


@_protegido
def excluir_custo(conn, id_custo):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM TB_CUSTO WHERE ID_CUSTO = :id", {"id": id_custo})
    conn.commit()
