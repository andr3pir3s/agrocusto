"""Constantes do sistema: tuplas imutáveis e limites de regra de negócio."""

# Tuplas: listas fixas que não devem ser alteradas em tempo de execução.
CULTURAS = ("Soja", "Milho", "Feijão", "Café", "Trigo", "Arroz", "Outra")
CATEGORIAS = (
    "Sementes",
    "Fertilizantes",
    "Defensivos",
    "Combustível",
    "Mão de obra",
    "Máquinas e manutenção",
    "Outros",
)

# Limites usados na validação de entrada.
AREA_MAXIMA_HA = 10_000
PRODUTIVIDADE_MAXIMA = 10_000
VALOR_MAXIMO = 100_000_000

# Limites usados nos alertas automáticos.
LIMITE_MARGEM_APERTADA = 0.10         # margem abaixo de 10% da receita
LIMITE_CUSTO_HA_ACIMA_MEDIA = 0.20    # custo/ha 20% acima da média da cultura
LIMITE_CONCENTRACAO_CATEGORIA = 0.50  # uma categoria com mais de 50% do custo

DSN_PADRAO = "oracle.fiap.com.br:1521/ORCL"
