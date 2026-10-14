# AgroCusto - controle de safra e custos para o pequeno produtor

> Atividade FIAP - Python (capítulos 3 a 6) aplicada ao agronegócio.
> **Integrante:** André Victor Mestre Pires Ferreira RM576305

## 1. Qual problema do agronegócio estamos tratando?

Muitos pequenos produtores rurais controlam os gastos da lavoura em cadernos, notas
soltas ou planilhas, e só descobrem se a safra deu lucro depois da colheita, quando já
não há o que corrigir. Faltam três respostas simples durante a safra:

1. **Quanto já gastei em cada talhão (e por hectare)?**
2. **Qual é a margem esperada com o preço e a produtividade que estimo?**
3. **A que preço da saca ou a qual produtividade eu empato? (ponto de equilíbrio)**

O **AgroCusto** responde a essas perguntas pelo terminal. O produtor cadastra seus
talhões, lança os custos conforme acontecem e o sistema calcula custo por hectare,
margem estimada, ponto de equilíbrio e **alertas automáticos** (nossa inovação).

Contexto: o tema se conecta às leituras da atividade sobre agricultura digital (Embrapa),
inovação e qualificação do produtor na era digital (CropLife Brasil) e sustentabilidade
dos pequenos produtores (Portal do Agronegócio).

## 2. O que o sistema faz

| Menu | Funções |
|---|---|
| Talhões | cadastrar, listar, alterar e excluir (nome, cultura, área, produtividade esperada, preço esperado, data de plantio) |
| Custos | lançar, listar (por talhão ou todos), alterar e excluir, por categoria (sementes, fertilizantes, defensivos...) |
| Análises e alertas | análise por talhão, painel geral da propriedade e alertas automáticos |
| Arquivos | exportar e importar JSON, gerar relatório TXT e ver o histórico de operações |

### Inovação: alertas e ponto de equilíbrio
- **Margem negativa:** informa o preço mínimo da saca e a produtividade mínima para empatar.
- **Margem apertada:** margem abaixo de 10% da receita estimada.
- **Custo/ha acima da média** dos talhões da mesma cultura (a partir de 20% acima).
- **Concentração:** uma categoria com mais de 50% do custo do talhão.

Os limites ficam em `src/constantes.py`.

## 3. Onde cada conteúdo da disciplina aparece

| Conteúdo exigido | Onde está |
|---|---|
| Funções (com retorno) e passagem de parâmetros | `src/calculos.py` (`analisar_talhao`, `custo_total`, `gerar_alertas`...) e `src/formatacao.py` |
| Procedimentos (sem retorno) | `src/relatorios.py` (`exibir`) e as telas de `src/menus.py` |
| Lista | `estado["talhoes"]` e `estado["custos"]` |
| Tupla | `CULTURAS` e `CATEGORIAS` em `src/constantes.py` |
| Dicionário | cada talhão e cada custo é um dicionário; também `custo_por_categoria` |
| Tabela de memória | lista de dicionários mostrada em tabela por `relatorios.tabela` |
| Arquivo texto | `data/historico.txt` (log) e relatório `.txt` (`src/arquivos.py`) |
| Arquivo JSON | backup automático em `data/`, exportação e importação (`src/arquivos.py`) |
| Oracle | `src/banco.py` e `sql/schema.sql` (CRUD completo, com commit e rollback) |

## 4. Validação dos dados de entrada

Toda digitação passa por `src/validacao.py`, que repete a pergunta até receber um valor válido:

- números: aceita `1.234,56` e `R$ 120`; rejeita letras, negativos, zero, `nan`/`inf` e valores fora dos limites;
- datas: formato `dd/mm/aaaa`, rejeita datas inexistentes (ex.: 31/02);
- escolhas: culturas e categorias vêm de listas numeradas;
- nomes: tamanho mínimo/máximo, ao menos uma letra e sem duplicar nome de talhão;
- IDs: só aceita IDs existentes;
- nomes de arquivo: só letras, números, `_` e `-`;
- JSON importado: cada registro passa pelas mesmas regras e limites das telas; os inválidos são ignorados e contados, e nomes de talhão repetidos ganham um sufixo, como `Gleba Norte (2)`.

Em qualquer pergunta de cadastro, alteração ou exportação o usuário pode digitar **`voltar`** para cancelar (nos menus, a saída é a opção `0`). Nas alterações, **ENTER** mantém o valor atual.

## 5. Como executar

Requisitos: Python 3.9 ou superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Conexão com o Oracle
1. Copie `.env.example` para `.env` e preencha `ORACLE_USER`, `ORACLE_PASSWORD` e `ORACLE_DSN`
   (formato `host:porta/servico`). O `.env` é lido automaticamente e está no `.gitignore`.
   Sem o arquivo (ou com campos em branco), o sistema pergunta o que faltar no terminal.
2. Rode `python main.py`. As tabelas `TB_TALHAO` e `TB_CUSTO` são criadas automaticamente
   na primeira conexão (`sql/schema.sql`, Oracle 12c ou superior).
3. **Nunca coloque a senha no código nem no GitHub.**

Erros comuns de conexão (senha inválida, servidor inalcançável, serviço inexistente, falta de
permissão) aparecem com uma explicação em português e o detalhe técnico.

Se o usuário ficar em branco (ou a conexão falhar), o sistema segue em **modo offline**.
Cada modo tem seu próprio backup, para um nunca sobrescrever o outro:

| Modo | Backup automático |
|---|---|
| Offline | `data/backup_offline.json` |
| Oracle | `data/backup_oracle.json` (cópia de segurança; a fonte dos dados é o banco) |

Para enviar ao Oracle o que foi feito offline, conecte e use *Arquivos > Importar dados de JSON*
com o arquivo `backup_offline`. O sistema avisa quando encontra dados offline ao conectar.

### Modelo de dados

```
TB_TALHAO (ID_TALHAO PK, NM_TALHAO, DS_CULTURA, VL_AREA_HA, VL_PRODUTIVIDADE, VL_PRECO_SACA, DT_PLANTIO)
     1 ──────< N
TB_CUSTO  (ID_CUSTO PK, ID_TALHAO FK, DS_CATEGORIA, DS_CUSTO, VL_CUSTO, DT_CUSTO)
```
Excluir um talhão remove seus custos (`ON DELETE CASCADE`).

### Trocar de banco de dados
O restante do sistema só conversa com as funções de `src/banco.py` (`listar_*`, `inserir_*`,
`atualizar_*`, `excluir_*`, `criar_tabelas`, `conectar`). Para usar PostgreSQL, MySQL ou
SQL Server, mantenha esses nomes e assinaturas e altere apenas:

1. **Driver e `conectar`**: troque `oracledb` por `psycopg`, `mysql-connector-python` ou `pyodbc`.
2. **Parâmetros das queries**: `:nome` (Oracle) vira `%s` (PostgreSQL/MySQL) ou `?` (SQL Server).
3. **`sql/schema.sql`**: `VARCHAR2`/`NUMBER` e `GENERATED ALWAYS AS IDENTITY` são do Oracle
   (use `SERIAL` no PostgreSQL ou `AUTO_INCREMENT` no MySQL).
4. **ID gerado no INSERT**: `RETURNING ... INTO` é do Oracle (PostgreSQL usa `RETURNING id`;
   MySQL usa `cursor.lastrowid`).
5. **Código de "tabela já existe"** (`ORA_TABELA_JA_EXISTE`) e o decorador `_protegido`,
   que captura os erros do driver; se preferir, use `CREATE TABLE IF NOT EXISTS`.
6. **`menus.tela_conexao`**: ajuste os textos e o DSN padrão (`src/constantes.py`).

`servico.py`, `calculos.py`, `relatorios.py` e os menus não mudam.

### Testes
```bash
python -m unittest discover -s tests -t .
```

## 6. Estrutura do repositório

```
main.py              ponto de entrada
src/constantes.py    tuplas e limites
src/validacao.py     leitura e validação de entradas
src/calculos.py      regras de negócio (funções)
src/formatacao.py    formatação em padrão brasileiro
src/relatorios.py    tabelas e relatórios
src/arquivos.py      JSON e texto
src/banco.py         Oracle (conexão, CRUD e mensagens de erro)
src/config.py        leitura do arquivo .env
src/servico.py       CRUD que sincroniza memória, Oracle e arquivos
src/menus.py         menus e telas
sql/schema.sql       criação das tabelas
tests/               testes das regras, validações, importação, .env e erros
```

Link do projeto: https://github.com/andr3pir3s/agrocusto