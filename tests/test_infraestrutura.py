"""Testes de configuração, mensagens de erro, importação e persistência."""
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import arquivos, banco, config, servico
from src.validacao import custo_valido, talhao_valido

TALHAO = {
    "id": 1, "nome": "Gleba Norte", "cultura": "Soja", "area_ha": 10.0,
    "produtividade_sc_ha": 60.0, "preco_saca": 120.0, "data_plantio": "2026-09-15",
}
CUSTO = {
    "id": 1, "talhao_id": 1, "categoria": "Sementes", "descricao": "Sementes de soja",
    "valor": 1000.0, "data": "2026-09-20",
}


class TestConfig(unittest.TestCase):
    def test_interpreta_env(self):
        texto = "# comentário\n\nORACLE_USER=rm123\nORACLE_PASSWORD='a#b c'\nINVALIDA\n"
        self.assertEqual(
            config.interpretar_env(texto),
            {"ORACLE_USER": "rm123", "ORACLE_PASSWORD": "a#b c"},
        )

    def test_nao_sobrescreve_variavel_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / ".env"
            caminho.write_text("TESTE_AGRO_X=do_arquivo\nTESTE_AGRO_Y=novo\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"TESTE_AGRO_X": "do_terminal"}, clear=False):
                os.environ.pop("TESTE_AGRO_Y", None)
                self.assertTrue(config.carregar_env(caminho))
                self.assertEqual(os.environ["TESTE_AGRO_X"], "do_terminal")
                self.assertEqual(os.environ["TESTE_AGRO_Y"], "novo")
                os.environ.pop("TESTE_AGRO_Y", None)

    def test_arquivo_inexistente(self):
        self.assertFalse(config.carregar_env(Path("/nao/existe/.env")))


class TestErrosOracle(unittest.TestCase):
    def test_senha_invalida(self):
        self.assertIn("senha", banco.traduzir_erro("ORA-01017: invalid username/password").lower())

    def test_servidor_inalcancavel(self):
        self.assertIn("inalcançável", banco.traduzir_erro("DPY-6005: cannot connect to database"))

    def test_erro_desconhecido(self):
        self.assertEqual(banco.traduzir_erro("ORA-99999: algo raro"), "")


class TestConexao(unittest.TestCase):
    def test_host_inexistente_vira_erro_amigavel(self):
        falso = mock.Mock()
        falso.Error = type("Error", (Exception,), {})
        falso.connect.side_effect = socket.gaierror(-2, "Name or service not known")
        with mock.patch.object(banco, "oracledb", falso):
            with self.assertRaises(banco.ErroBanco) as ctx:
                banco.conectar("u", "s", "host-invalido:1521/ORCL")
        self.assertIn("inalcançável", str(ctx.exception))

    def test_sem_biblioteca_instalada(self):
        with mock.patch.object(banco, "oracledb", None):
            with self.assertRaises(banco.ErroBanco):
                banco.conectar("u", "s", "x")


class TestImportacao(unittest.TestCase):
    def test_limites_do_banco_na_importacao(self):
        self.assertFalse(talhao_valido({**TALHAO, "area_ha": 1e12}))
        self.assertFalse(custo_valido({**CUSTO, "valor": 1e15}))

    def test_descricao_curta_rejeitada(self):
        self.assertFalse(custo_valido({**CUSTO, "descricao": "ab"}))

    def test_booleano_nao_e_numero(self):
        self.assertFalse(talhao_valido({**TALHAO, "area_ha": True}))

    def test_importar_duas_vezes_nao_duplica_nome(self):
        estado = servico.criar_estado()
        dados = {"talhoes": [TALHAO], "custos": [CUSTO]}
        with mock.patch.object(servico, "_depois_de_alterar"):
            servico.importar_dados(estado, dados)
            talhoes, custos, ignorados = servico.importar_dados(estado, dados)
        nomes = [t["nome"] for t in estado["talhoes"]]
        self.assertEqual(nomes, ["Gleba Norte", "Gleba Norte (2)"])
        self.assertEqual((talhoes, custos, ignorados), (1, 1, 0))
        # cada custo ficou ligado ao talhão certo
        self.assertEqual({c["talhao_id"] for c in estado["custos"]}, {1, 2})

    def test_custo_de_talhao_inexistente_e_ignorado(self):
        estado = servico.criar_estado()
        dados = {"talhoes": [TALHAO], "custos": [{**CUSTO, "talhao_id": 99}]}
        with mock.patch.object(servico, "_depois_de_alterar"):
            _, custos, ignorados = servico.importar_dados(estado, dados)
        self.assertEqual((custos, ignorados), (0, 1))


class TestPersistenciaOffline(unittest.TestCase):
    def test_dados_voltam_ao_reabrir(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            with mock.patch.object(arquivos, "BACKUP_OFFLINE", pasta / "off.json"), \
                 mock.patch.object(arquivos, "BACKUP_ORACLE", pasta / "ora.json"), \
                 mock.patch.object(arquivos, "ARQUIVO_HISTORICO", pasta / "hist.txt"):
                estado = servico.criar_estado()
                novo = servico.adicionar_talhao(
                    estado, {k: v for k, v in TALHAO.items() if k != "id"})
                servico.adicionar_custo(
                    estado, {k: v for k, v in CUSTO.items() if k != "id"} | {"talhao_id": novo["id"]})

                reaberto = servico.criar_estado()
                servico.carregar_dados(reaberto)
                self.assertEqual(len(reaberto["talhoes"]), 1)
                self.assertEqual(len(reaberto["custos"]), 1)
                self.assertEqual(servico.contar_talhoes_offline(), 1)
                self.assertFalse((pasta / "ora.json").exists())


if __name__ == "__main__":
    unittest.main()
