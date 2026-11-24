"""Gera seed.sql e supabase_full.sql com dados coerentes ate a data da apresentacao (25/11/2026)."""
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
base = Path(__file__).parent

# Referencia inclui o dia da apresentacao (25/11) para que filtros 'Hoje' e 'Ontem' tenham vendas reais
agora = max(datetime.now(), datetime(2026, 11, 25, 11, 45, 0))

PRODUTOS = [
    (1, "Metodo Emagrece em 30 Dias", "Saude", 47.00),
    (2, "Guia do Primeiro Milhao", "Financas", 97.00),
    (3, "Ingles em 90 Dias", "Educacao", 67.90),
    (4, "Planner Produtivo 2026", "Produtividade", 19.90),
    (5, "Receitas Fit Express", "Saude", 27.00),
    (6, "Curso de Trafego Pago", "Marketing", 197.00),
    (7, "Mentoria Instagram Pro", "Marketing", 250.00),
    (8, "Ebook Renda Extra", "Financas", 34.99),
]

# Estados fora da lista (AC, AP, RO, RR, TO) iniciam com 0 vendas de proposito (otimo para demonstracao ao vivo no mapa)
ESTADOS = {
    "SP": 28, "RJ": 12, "MG": 11, "BA": 6, "PR": 6, "RS": 6, "SC": 4, "PE": 4, "CE": 4,
    "GO": 3, "DF": 3, "PA": 2, "ES": 2, "AM": 1, "MA": 1, "MT": 1, "MS": 1, "RN": 1,
    "PB": 1, "AL": 1, "PI": 1, "SE": 1,
}
NOMES = "Ana Bruno Carla Diego Elisa Felipe Gabriela Hugo Isabela Joao Karen Lucas Marina Nicolas Olivia Paulo Rafaela Sergio Tatiana Vitor".split()
SOBRENOMES = "Silva Souza Oliveira Santos Lima Pereira Costa Ribeiro Almeida Carvalho Gomes Martins Rocha Barbosa Moreira Nunes Dias Cardoso Teixeira Freitas".split()

sql = ["-- Dados iniciais gerados por gen_seed.py (contexto: venda de infoprodutos)"]
for p in PRODUTOS:
    sql.append(f"INSERT INTO produtos (id, nome, categoria, preco) VALUES ({p[0]}, '{p[1]}', '{p[2]}', {p[3]:.2f});")

for cid in range(1, 151):
    n, s = random.choice(NOMES), random.choice(SOBRENOMES)
    uf = random.choices(list(ESTADOS), weights=ESTADOS.values())[0]
    sql.append(
        f"INSERT INTO clientes (id, nome, email, estado) "
        f"VALUES ({cid}, '{n} {s}', '{n.lower()}.{s.lower()}{cid}@email.com', '{uf}');"
    )

item_id = 1
for pid in range(1, 461):
    # Garante vendas distribuidas nos ultimos 90 dias, com volume consistente ontem (24/11) e hoje (25/11)
    if pid <= 8:
        dia = agora - timedelta(days=1)
    elif pid <= 15:
        dia = agora
    else:
        dia = agora - timedelta(days=int(90 * random.random() ** 1.25))

    hora = random.randint(7, 22)
    if dia.date() == agora.date():
        hora = random.randint(7, agora.hour)
    dt = dia.replace(hour=hora, minute=random.randint(0, 59), second=random.randint(0, 59))

    status = random.choices(["aprovado", "pendente", "reembolsado"], weights=[80, 12, 8])[0]
    pag = random.choices(["pix", "cartao", "boleto"], weights=[62, 28, 10])[0]
    sql.append(
        f"INSERT INTO pedidos (id, cliente_id, data_pedido, status, meio_pagamento) "
        f"VALUES ({pid}, {random.randint(1, 150)}, '{dt:%Y-%m-%d %H:%M:%S}', '{status}', '{pag}');"
    )

    principal = random.choices(PRODUTOS, weights=[5, 3, 4, 8, 6, 2, 1, 6])[0]
    itens = [principal]
    if random.random() < 0.25:  # Order bump: segundo infoproduto complementar no mesmo pedido
        itens.append(random.choice([p for p in PRODUTOS if p[3] < 40 and p != principal]))
    for it in itens:
        sql.append(
            f"INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, valor_unitario) "
            f"VALUES ({item_id}, {pid}, {it[0]}, 1, {it[3]:.2f});"
        )
        item_id += 1

seed_text = "\n".join(sql) + "\n"
(base / "seed.sql").write_text(seed_text, encoding="utf-8")

# Gera tambem um script unico otimizado para colar direto no SQL Editor do Supabase (PostgreSQL)
schema_pg = (
    (base / "schema.sql")
    .read_text(encoding="utf-8")
    .replace("id             INTEGER       PRIMARY KEY", "id             SERIAL        PRIMARY KEY")
    .replace("id             INTEGER     PRIMARY KEY", "id             SERIAL      PRIMARY KEY")
    .replace("id        INTEGER PRIMARY KEY", "id        SERIAL  PRIMARY KEY")
    .replace("id     INTEGER PRIMARY KEY", "id     SERIAL  PRIMARY KEY")
)
seq_fix = """
-- Sincroniza as sequences do PostgreSQL para permitir INSERT sem informar ID manualmente
SELECT setval(pg_get_serial_sequence('clientes', 'id'), COALESCE((SELECT MAX(id) FROM clientes), 1));
SELECT setval(pg_get_serial_sequence('produtos', 'id'), COALESCE((SELECT MAX(id) FROM produtos), 1));
SELECT setval(pg_get_serial_sequence('pedidos', 'id'), COALESCE((SELECT MAX(id) FROM pedidos), 1));
SELECT setval(pg_get_serial_sequence('itens_pedido', 'id'), COALESCE((SELECT MAX(id) FROM itens_pedido), 1));
"""
(base / "supabase_full.sql").write_text(schema_pg + "\n" + seed_text + seq_fix, encoding="utf-8")
print(f"seed.sql e supabase_full.sql gerados ({len(sql)} comandos SQL).")
