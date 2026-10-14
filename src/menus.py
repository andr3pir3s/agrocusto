"""Telas e menus (interface de linha de comando)."""
import getpass
import os
from datetime import date

from src import arquivos, banco, calculos, relatorios, servico
from src.constantes import (
    AREA_MAXIMA_HA, CATEGORIAS, CULTURAS, DSN_PADRAO, PRODUTIVIDADE_MAXIMA, VALOR_MAXIMO,
)
from src.formatacao import moeda
from src.validacao import (
    OperacaoCancelada, confirmar, ler_data, ler_decimal, ler_escolha, ler_id,
    ler_nome_arquivo, ler_texto,
)

DICA_CANCELAR = "(digite 'voltar' a qualquer momento para cancelar)"


# ---------- infraestrutura de menus ----------

def executar_menu(titulo, opcoes, estado):
    """opcoes: {"1": ("Rótulo", função)}. A função None significa 'voltar/sair'."""
    while True:
        relatorios.exibir(relatorios.titulo(titulo))
        for tecla, (rotulo, _) in opcoes.items():
            print(f"  {tecla}) {rotulo}")
        escolha = ler_opcao_menu(opcoes)
        funcao = opcoes[escolha][1]
        if funcao is None:
            return
        try:
            funcao(estado)
        except OperacaoCancelada:
            print("\n  Operação cancelada.")
        except banco.ErroBanco as erro:
            print(f"\n  [ERRO] {erro}")


def ler_opcao_menu(opcoes):
    while True:
        resposta = input("\nEscolha uma opção: ").strip()
        if resposta in opcoes:
            return resposta
        print(f"  [!] Opção inválida. Escolha entre: {', '.join(opcoes)}.")


def menu_principal(estado):
    opcoes = {
        "1": ("Talhões (cadastro)", menu_talhoes),
        "2": ("Custos (lançamentos)", menu_custos),
        "3": ("Análises e alertas", menu_analises),
        "4": ("Arquivos (JSON / TXT)", menu_arquivos),
        "0": ("Sair", None),
    }
    executar_menu(f"AgroCusto - modo: {servico.nome_do_modo(estado)}", opcoes, estado)


def menu_talhoes(estado):
    opcoes = {
        "1": ("Cadastrar talhão", cadastrar_talhao),
        "2": ("Listar talhões", listar_talhoes),
        "3": ("Alterar talhão", alterar_talhao),
        "4": ("Excluir talhão", excluir_talhao),
        "0": ("Voltar", None),
    }
    executar_menu("Talhões", opcoes, estado)


def menu_custos(estado):
    opcoes = {
        "1": ("Lançar custo", cadastrar_custo),
        "2": ("Listar custos", listar_custos),
        "3": ("Alterar custo", alterar_custo),
        "4": ("Excluir custo", excluir_custo),
        "0": ("Voltar", None),
    }
    executar_menu("Custos", opcoes, estado)


def menu_analises(estado):
    opcoes = {
        "1": ("Análise de um talhão (custo/ha, margem, equilíbrio)", analisar_um_talhao),
        "2": ("Painel geral da propriedade", painel_geral),
        "3": ("Alertas automáticos", mostrar_alertas),
        "0": ("Voltar", None),
    }
    executar_menu("Análises e alertas", opcoes, estado)


def menu_arquivos(estado):
    opcoes = {
        "1": ("Exportar dados para JSON", exportar_json),
        "2": ("Importar dados de JSON", importar_json),
        "3": ("Gerar relatório em TXT", gerar_relatorio_txt),
        "4": ("Ver histórico de operações", ver_historico),
        "0": ("Voltar", None),
    }
    executar_menu("Arquivos", opcoes, estado)


# ---------- conexão ----------

def tela_conexao(estado):
    relatorios.exibir(relatorios.titulo("Conexão com o Oracle"))
    print("Credenciais lidas do .env / variáveis de ambiente; o que faltar será perguntado.")
    print("Deixe o usuário em branco para usar o modo offline.")
    usuario = os.getenv("ORACLE_USER") or input("Usuário Oracle (ENTER = offline): ").strip()
    if not usuario:
        print("\n  Modo offline: os dados ficam em data/backup_offline.json.")
        servico.carregar_dados(estado)
        return
    senha = os.getenv("ORACLE_PASSWORD") or getpass.getpass("Senha: ")
    dsn = os.getenv("ORACLE_DSN") or input(f"DSN [{DSN_PADRAO}]: ").strip() or DSN_PADRAO
    print(f"\n  Conectando a {dsn} como {usuario}...")
    try:
        estado["conn"] = banco.conectar(usuario, senha, dsn)
        servico.carregar_dados(estado)
        print("\n  Conectado ao Oracle.")
        pendentes = servico.contar_talhoes_offline()
        if pendentes:
            print(f"  Há {pendentes} talhão(ões) salvos do modo offline. Para enviá-los ao Oracle, use "
                  "Arquivos > Importar dados de JSON (arquivo backup_offline).")
    except banco.ErroBanco as erro:
        print(f"\n  [ERRO] {erro}")
        if estado["conn"]:
            estado["conn"].close()
            estado["conn"] = None
        print("  Seguindo em modo offline.")
        servico.carregar_dados(estado)


# ---------- auxiliares ----------

def _ha_talhoes(estado):
    if not estado["talhoes"]:
        print("\n  Cadastre ao menos um talhão primeiro (menu Talhões).")
        return False
    return True


def _escolher_talhao(estado, mensagem, permitir_zero=False):
    relatorios.exibir(relatorios.linhas_talhoes(estado["talhoes"]))
    ids = {t["id"] for t in estado["talhoes"]}
    return ler_id(mensagem, ids, permitir_zero)


def _escolher_custo(estado, mensagem):
    relatorios.exibir(relatorios.linhas_custos(estado["custos"], estado["talhoes"]))
    ids = {c["id"] for c in estado["custos"]}
    return ler_id(mensagem, ids)


# ---------- talhões ----------

def cadastrar_talhao(estado):
    relatorios.exibir(relatorios.subtitulo("Novo talhão"))
    print(DICA_CANCELAR)
    nomes = tuple(t["nome"].lower() for t in estado["talhoes"])
    dados = {
        "nome": ler_texto("Nome do talhão (ex.: Gleba Norte)", proibidos=nomes),
        "cultura": ler_escolha("Cultura", CULTURAS),
        "area_ha": ler_decimal("Área (ha)", 0.01, AREA_MAXIMA_HA),
        "produtividade_sc_ha": ler_decimal("Produtividade esperada (sacas/ha)", 0.01, PRODUTIVIDADE_MAXIMA),
        "preco_saca": ler_decimal("Preço esperado por saca (R$)", 0.01, VALOR_MAXIMO),
        "data_plantio": ler_data("Data de plantio (dd/mm/aaaa)"),
    }
    novo = servico.adicionar_talhao(estado, dados)
    print(f"\n  Talhão {novo['id']} ({novo['nome']}) cadastrado com sucesso.")


def listar_talhoes(estado):
    relatorios.exibir(relatorios.linhas_talhoes(estado["talhoes"]))


def alterar_talhao(estado):
    if not _ha_talhoes(estado):
        return
    id_talhao = _escolher_talhao(estado, "ID do talhão a alterar")
    t = servico.buscar_talhao(estado, id_talhao)
    print("\nENTER mantém o valor atual. " + DICA_CANCELAR)
    outros = tuple(x["nome"].lower() for x in estado["talhoes"] if x["id"] != id_talhao)
    novos = {
        "nome": ler_texto("Nome do talhão", padrao=t["nome"], proibidos=outros),
        "cultura": ler_escolha("Cultura", CULTURAS, padrao=t["cultura"]),
        "area_ha": ler_decimal("Área (ha)", 0.01, AREA_MAXIMA_HA, padrao=t["area_ha"]),
        "produtividade_sc_ha": ler_decimal(
            "Produtividade esperada (sacas/ha)", 0.01, PRODUTIVIDADE_MAXIMA, padrao=t["produtividade_sc_ha"]),
        "preco_saca": ler_decimal("Preço esperado por saca (R$)", 0.01, VALOR_MAXIMO, padrao=t["preco_saca"]),
        "data_plantio": ler_data("Data de plantio (dd/mm/aaaa)", padrao=t["data_plantio"]),
    }
    servico.alterar_talhao(estado, t, novos)
    print("\n  Talhão alterado com sucesso.")


def excluir_talhao(estado):
    if not _ha_talhoes(estado):
        return
    id_talhao = _escolher_talhao(estado, "ID do talhão a excluir")
    t = servico.buscar_talhao(estado, id_talhao)
    qtd = sum(1 for c in estado["custos"] if c["talhao_id"] == id_talhao)
    if confirmar(f"Excluir '{t['nome']}' e seus {qtd} custo(s)?"):
        servico.excluir_talhao(estado, t)
        print("\n  Talhão excluído.")
    else:
        print("\n  Nada foi excluído.")


# ---------- custos ----------

def cadastrar_custo(estado):
    if not _ha_talhoes(estado):
        return
    relatorios.exibir(relatorios.subtitulo("Novo custo"))
    print(DICA_CANCELAR)
    id_talhao = _escolher_talhao(estado, "ID do talhão")
    dados = {
        "talhao_id": id_talhao,
        "categoria": ler_escolha("Categoria", CATEGORIAS),
        "descricao": ler_texto("Descrição (ex.: Adubo NPK 20 sacos)", 3, 100),
        "valor": ler_decimal("Valor (R$)", 0.01, VALOR_MAXIMO),
        "data": ler_data("Data do gasto (dd/mm/aaaa)", padrao=date.today().isoformat()),
    }
    novo = servico.adicionar_custo(estado, dados)
    print(f"\n  Custo {novo['id']} lançado com sucesso.")


def listar_custos(estado):
    if not estado["custos"]:
        print("\n  Nenhum custo lançado.")
        return
    id_talhao = _escolher_talhao(estado, "ID do talhão (0 = todos)", permitir_zero=True)
    custos = [c for c in estado["custos"] if id_talhao in (0, c["talhao_id"])]
    relatorios.exibir(relatorios.linhas_custos(custos, estado["talhoes"]))
    print(f"\nTotal listado: {moeda(calculos.custo_total(custos))}")


def alterar_custo(estado):
    if not estado["custos"]:
        print("\n  Nenhum custo lançado.")
        return
    id_custo = _escolher_custo(estado, "ID do custo a alterar")
    c = servico.buscar_custo(estado, id_custo)
    print("\nENTER mantém o valor atual. " + DICA_CANCELAR)
    novos = {
        "categoria": ler_escolha("Categoria", CATEGORIAS, padrao=c["categoria"]),
        "descricao": ler_texto("Descrição", 3, 100, padrao=c["descricao"]),
        "valor": ler_decimal("Valor (R$)", 0.01, VALOR_MAXIMO, padrao=c["valor"]),
        "data": ler_data("Data do gasto (dd/mm/aaaa)", padrao=c["data"]),
    }
    servico.alterar_custo(estado, c, novos)
    print("\n  Custo alterado com sucesso.")


def excluir_custo(estado):
    if not estado["custos"]:
        print("\n  Nenhum custo lançado.")
        return
    id_custo = _escolher_custo(estado, "ID do custo a excluir")
    c = servico.buscar_custo(estado, id_custo)
    if confirmar(f"Excluir o custo '{c['descricao']}'?"):
        servico.excluir_custo(estado, c)
        print("\n  Custo excluído.")
    else:
        print("\n  Nada foi excluído.")


# ---------- análises ----------

def analisar_um_talhao(estado):
    if not _ha_talhoes(estado):
        return
    id_talhao = _escolher_talhao(estado, "ID do talhão a analisar")
    t = servico.buscar_talhao(estado, id_talhao)
    relatorios.exibir(relatorios.linhas_analise_talhao(t, calculos.analisar_talhao(t, estado["custos"])))


def painel_geral(estado):
    relatorios.exibir(relatorios.subtitulo("Painel geral da propriedade"))
    relatorios.exibir(relatorios.linhas_painel(estado["talhoes"], estado["custos"]))


def mostrar_alertas(estado):
    relatorios.exibir(relatorios.subtitulo("Alertas automáticos"))
    alertas = calculos.gerar_alertas(estado["talhoes"], estado["custos"])
    relatorios.exibir(relatorios.linhas_alertas(alertas))


# ---------- arquivos ----------

def exportar_json(estado):
    print(DICA_CANCELAR)
    nome = ler_nome_arquivo("Nome do arquivo", ".json", "safra_dados.json")
    caminho = arquivos.PASTA_DADOS / nome
    arquivos.salvar_json(caminho, servico.montar_exportacao(estado))
    print(f"\n  Dados exportados para data/{nome}")


def importar_json(estado):
    disponiveis = arquivos.listar_arquivos(".json")
    if not disponiveis:
        print("\n  Nenhum arquivo .json encontrado na pasta data/.")
        return
    print("Arquivos disponíveis em data/:")
    for nome in disponiveis:
        print(f"  - {nome}")
    print(DICA_CANCELAR)
    nome = ler_nome_arquivo("Nome do arquivo", ".json", disponiveis[0])
    try:
        dados = arquivos.carregar_json(arquivos.PASTA_DADOS / nome)
    except FileNotFoundError:
        print("\n  [ERRO] Arquivo não encontrado.")
        return
    except ValueError as erro:
        print(f"\n  [ERRO] Arquivo JSON inválido: {erro}")
        return
    if not confirmar("Os registros serão ADICIONADOS aos dados atuais. Continuar?"):
        print("\n  Importação cancelada.")
        return
    talhoes, custos, ignorados = servico.importar_dados(estado, dados)
    print(f"\n  Importados: {talhoes} talhão(ões) e {custos} custo(s). Registros ignorados (inválidos): {ignorados}.")


def gerar_relatorio_txt(estado):
    if not _ha_talhoes(estado):
        return
    print(DICA_CANCELAR)
    nome = ler_nome_arquivo("Nome do arquivo", ".txt", "relatorio_safra.txt")
    linhas = relatorios.relatorio_completo(estado["talhoes"], estado["custos"])
    arquivos.salvar_texto(arquivos.PASTA_DADOS / nome, linhas)
    print(f"\n  Relatório gerado em data/{nome}")


def ver_historico(estado):
    linhas = arquivos.ler_ultimas_linhas(arquivos.ARQUIVO_HISTORICO)
    relatorios.exibir(relatorios.subtitulo("Últimas operações"))
    print("\n".join(linhas) if linhas else "Nenhuma operação registrada ainda.")
