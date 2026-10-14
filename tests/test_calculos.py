"""Testes das regras de negócio. Execute com: python -m unittest discover -s tests -t ."""
import unittest

from src import calculos
from src.validacao import custo_valido, talhao_valido

TALHAO = {
    "id": 1, "nome": "Gleba Norte", "cultura": "Soja", "area_ha": 10.0,
    "produtividade_sc_ha": 60.0, "preco_saca": 120.0, "data_plantio": "2026-09-15",
}


def custo(id_, talhao_id, categoria, valor):
    return {"id": id_, "talhao_id": talhao_id, "categoria": categoria,
            "descricao": "Teste", "valor": valor, "data": "2026-09-20"}


class TestCalculos(unittest.TestCase):
    def test_analise_com_lucro(self):
        custos = [custo(1, 1, "Sementes", 20000.0), custo(2, 1, "Fertilizantes", 10000.0)]
        a = calculos.analisar_talhao(TALHAO, custos)
        self.assertEqual(a["custo_total"], 30000.0)
        self.assertEqual(a["custo_ha"], 3000.0)
        self.assertEqual(a["receita"], 72000.0)
        self.assertEqual(a["margem"], 42000.0)
        self.assertEqual(a["preco_equilibrio"], 50.0)
        self.assertEqual(a["produtividade_equilibrio"], 25.0)

    def test_custos_de_outro_talhao_nao_entram(self):
        custos = [custo(1, 1, "Sementes", 100.0), custo(2, 2, "Sementes", 999.0)]
        self.assertEqual(calculos.custo_total(custos, 1), 100.0)

    def test_categorias_ordenadas(self):
        custos = [custo(1, 1, "Sementes", 10.0), custo(2, 1, "Defensivos", 30.0)]
        self.assertEqual(list(calculos.custo_por_categoria(custos)), ["Defensivos", "Sementes"])

    def test_alerta_margem_negativa(self):
        alertas = calculos.gerar_alertas([TALHAO], [custo(1, 1, "Sementes", 80000.0)])
        self.assertEqual(alertas[0][0], "CRITICO")

    def test_sem_alerta_quando_tudo_certo(self):
        custos = [custo(1, 1, "Sementes", 10000.0), custo(2, 1, "Defensivos", 10000.0)]
        self.assertEqual(calculos.gerar_alertas([TALHAO], custos), [])


class TestValidacaoImportacao(unittest.TestCase):
    def test_talhao_valido(self):
        self.assertTrue(talhao_valido(TALHAO))

    def test_talhao_com_area_negativa(self):
        self.assertFalse(talhao_valido({**TALHAO, "area_ha": -1}))

    def test_talhao_com_campo_faltando(self):
        ruim = dict(TALHAO)
        del ruim["cultura"]
        self.assertFalse(talhao_valido(ruim))

    def test_custo_com_categoria_invalida(self):
        self.assertFalse(custo_valido(custo(1, 1, "Inexistente", 10.0)))

    def test_custo_valido(self):
        self.assertTrue(custo_valido(custo(1, 1, "Sementes", 10.0)))


if __name__ == "__main__":
    unittest.main()
