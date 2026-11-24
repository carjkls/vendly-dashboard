# Vendly — Sistema e Dashboard Analítico de Vendas de Infoprodutos

**Aluno:** Carlos Eduardo  
**Instituição:** Centro Universitário Santo Agostinho (UNIFSA)  
**Disciplina:** Banco de Dados — Trabalho Prático: Dashboard com Indicadores e Análise de Dados  

---

## 1. Contexto e Objetivo do Sistema

O **Vendly** é um sistema de informação voltado para produtores e gestores de **infoprodutos digitais** (cursos online, mentorias, e-books e planners). Além de permitir o registro de vendas em tempo real e o gerenciamento de status de pedidos (`aprovado`, `pendente`, `reembolsado`), o sistema transforma os dados transacionais armazenados no banco de dados em indicadores estratégicos (**KPIs**) e visualizações interativas para apoiar a tomada de decisão comercial.

Todos os números, métricas, tabelas e gráficos são alimentados exclusivamente por **consultas SQL reais** executadas contra o banco de dados — sem valores estáticos no código.

---

## 2. Estrutura do Banco de Dados e Relacionamentos

O modelo relacional é composto por **4 tabelas** integradas por chaves primárias e estrangeiras:

```mermaid
erDiagram
    CLIENTES ||--o{ PEDIDOS : realiza
    PEDIDOS ||--|{ ITENS_PEDIDO : contem
    PRODUTOS ||--o{ ITENS_PEDIDO : compoe

    CLIENTES {
        int id PK
        varchar nome
        varchar email UK
        char estado
    }
    PRODUTOS {
        int id PK
        varchar nome
        varchar categoria
        numeric preco
    }
    PEDIDOS {
        int id PK
        int cliente_id FK
        timestamp data_pedido
        varchar status
        varchar meio_pagamento
    }
    ITENS_PEDIDO {
        int id PK
        int pedido_id FK
        int produto_id FK
        int quantidade
        numeric valor_unitario
    }
```

### Scripts SQL incluídos no repositório
* [`schema.sql`](./schema.sql): criação das tabelas e restrições de integridade referencial (`PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`).
* [`seed.sql`](./seed.sql): carga inicial coerente com o contexto (8 infoprodutos, 150 clientes distribuídos pelas UFs brasileiras e 460 pedidos com itens e *order bumps*).
* [`supabase_full.sql`](./supabase_full.sql): script unificado (`CREATE TABLE` com `SERIAL` + `INSERT` + ajuste de `SEQUENCE`) pronto para execução direta no **SQL Editor do Supabase (PostgreSQL)**.
* [`queries.sql`](./queries.sql): todas as consultas analíticas e operacionais consumidas pelo sistema.

---

## 3. Requisitos Obrigatórios de SQL Implementados

Todas as cláusulas exigidas pela disciplina estão implementadas em [`queries.sql`](./queries.sql) e podem ser inspecionadas também dentro da própria aplicação (aba **Consultas SQL**):

| Recurso SQL | Bloco em `queries.sql` | Aplicação no Sistema / Dashboard |
|---|---|---|
| **`MIN`** | `kpis` | Identifica a venda aprovada de **menor valor** no período selecionado (*KPI Menor Venda*). |
| **`MAX`** | `kpis` | Identifica a venda aprovada de **maior valor** no período selecionado (*KPI Maior Venda*). |
| **`GROUP BY`** | `kpis`, `faturamento_dia`, `vendas_estado`, `top_produtos`, `fat_categoria`, `recentes` | Agrupa itens por pedido, faturamento por data, vendas por UF, receita por produto e por categoria. |
| **`HAVING`** | `vendas_estado` | Filtra no **Mapa do Brasil** apenas os estados que possuem quantidade mínima de vendas aprovadas (`HAVING COUNT(DISTINCT p.id) >= :min_vendas`), controlado interativamente na barra lateral. |
| **`SUBQUERY`** | `kpis` e `top_produtos` | 1) Subconsulta no `FROM` (tabela derivada `t`) consolidando o total de cada pedido antes de extrair `SUM`, `AVG`, `MIN` e `MAX`; 2) Subconsulta escalar calculando a participação percentual (`share %`) de cada infoproduto sobre a receita total. |
| **`JOIN`** | Todas as consultas analíticas | Relaciona `pedidos`, `itens_pedido`, `clientes` e `produtos` para cruzar faturamento, localização geográfica (UF) e categorias. |

---

## 4. Indicadores, Gráficos e Funcionalidades

### KPIs (6 indicadores em tempo real)
1. **Faturamento Aprovado** (com variação percentual contra o período anterior)
2. **Vendas Aprovadas** (com variação percentual contra o período anterior)
3. **Ticket Médio** (com variação percentual contra o período anterior)
4. **Taxa de Aprovação** (`aprovados / total de pedidos`)
5. **Maior Venda (`MAX`)**
6. **Menor Venda (`MIN`)**

### Gráficos Interativos (4 tipos distintos)
1. **Mapa Coroplético do Brasil (GeoJSON):** volume de vendas e receita por unidade federativa, integrado ao filtro dinâmico `HAVING`.
2. **Gráfico de Área / Linha:** evolução diária do faturamento comparando o período atual com o período imediatamente anterior.
3. **Gráfico de Rosca (Donut):** distribuição do faturamento por categoria de infoproduto.
4. **Gráfico de Barras Horizontais:** ranking dos 5 infoprodutos de maior receita e sua fatia percentual no faturamento.

### Operações em Tempo Real no Banco (`CRUD`)
Na aba **Operações Ao Vivo**, o sistema permite:
* **Registrar nova venda (`INSERT`):** cadastrar cliente com sua UF, escolher infoproduto, quantidade, pagamento e status, atualizando imediatamente o mapa, os KPIs e os gráficos.
* **Alterar status ou remover pedido (`UPDATE` / `DELETE`):** aprovar pedidos pendentes, registrar reembolsos ou excluir registros de teste em tempo real.

---

## 5. Tecnologias Utilizadas

* **Linguagem:** Python 3.12
* **Interface e Servidor Web:** Streamlit
* **Visualização de Dados e Mapa GeoJSON:** Plotly
* **Manipulação de Dados e Conexão SQL:** Pandas + SQLAlchemy 2.0 + Psycopg 3
* **Banco de Dados:** **PostgreSQL (Supabase)** em produção na nuvem / **SQLite** para execução local imediata

---

## 6. Instalação e Execução

### Pré-requisitos
```bash
pip install -r requirements.txt
```

### Opção A — Rodando localmente (SQLite automático)
```bash
python init_db.py
streamlit run app.py
```

### Opção B — Rodando integrado ao PostgreSQL / Supabase
1. Crie um projeto gratuito no [Supabase](https://supabase.com), abra o **SQL Editor** e execute o conteúdo de [`supabase_full.sql`](./supabase_full.sql).
2. Configure a variável `DATABASE_URL` (ou `.streamlit/secrets.toml`) com a *Connection String* do Pooler IPv4 do Supabase:
   ```toml
   # .streamlit/secrets.toml
   DATABASE_URL = "postgresql://postgres.SEU_PROJETO:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
   ```
3. Inicie a aplicação:
   ```bash
   streamlit run app.py
   ```
