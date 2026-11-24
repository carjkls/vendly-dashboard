-- =============================================================================
-- VENDLY - CONSULTAS SQL DO SISTEMA E DO DASHBOARD
-- Aluno: Carlos Eduardo | Disciplina: Banco de Dados (UNIFSA)
-- Compatibilidade: PostgreSQL (Supabase) e SQLite
-- =============================================================================

-- name: kpis
-- Recursos SQL aplicados: SUBQUERY (tabela derivada t), JOIN, GROUP BY, SUM, COUNT, AVG, MAX e MIN
SELECT COALESCE(SUM(t.total), 0) AS faturamento,
       COUNT(*)                  AS vendas,
       COALESCE(AVG(t.total), 0) AS ticket_medio,
       COALESCE(MAX(t.total), 0) AS maior_venda,
       COALESCE(MIN(t.total), 0) AS menor_venda
FROM (
    SELECT p.id, SUM(i.quantidade * i.valor_unitario) AS total
    FROM pedidos p
    JOIN itens_pedido i ON i.pedido_id = p.id
    WHERE p.status = 'aprovado'
      AND DATE(p.data_pedido) BETWEEN :ini AND :fim
    GROUP BY p.id
) t

-- name: taxa_aprovacao
-- Calcula o total de pedidos gerados vs aprovados no periodo
SELECT COUNT(*) AS total_pedidos,
       COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados
FROM pedidos
WHERE DATE(data_pedido) BETWEEN :ini AND :fim

-- name: faturamento_dia
-- Recursos SQL aplicados: JOIN + GROUP BY por data (alimenta o grafico de evolucao diaria)
SELECT DATE(p.data_pedido) AS dia,
       SUM(i.quantidade * i.valor_unitario) AS faturamento
FROM pedidos p
JOIN itens_pedido i ON i.pedido_id = p.id
WHERE p.status = 'aprovado'
  AND DATE(p.data_pedido) BETWEEN :ini AND :fim
GROUP BY DATE(p.data_pedido)
ORDER BY dia

-- name: vendas_estado
-- Recursos SQL aplicados: JOIN (3 tabelas) + GROUP BY estado + HAVING (alimenta o Mapa do Brasil e Top UFs)
SELECT c.estado,
       COUNT(DISTINCT p.id) AS vendas,
       SUM(i.quantidade * i.valor_unitario) AS faturamento
FROM pedidos p
JOIN clientes c ON c.id = p.cliente_id
JOIN itens_pedido i ON i.pedido_id = p.id
WHERE p.status = 'aprovado'
  AND DATE(p.data_pedido) BETWEEN :ini AND :fim
GROUP BY c.estado
HAVING COUNT(DISTINCT p.id) >= :min_vendas
ORDER BY vendas DESC, faturamento DESC

-- name: top_produtos
-- Recursos SQL aplicados: JOIN (3 tabelas) + GROUP BY + SUBQUERY escalar (participacao % na receita total)
SELECT pr.nome AS produto,
       pr.categoria,
       SUM(i.quantidade) AS unidades,
       SUM(i.quantidade * i.valor_unitario) AS receita,
       COALESCE(
           ROUND(
               100.0 * SUM(i.quantidade * i.valor_unitario) / NULLIF((
                   SELECT SUM(i2.quantidade * i2.valor_unitario)
                   FROM itens_pedido i2
                   JOIN pedidos p2 ON p2.id = i2.pedido_id
                   WHERE p2.status = 'aprovado'
                     AND DATE(p2.data_pedido) BETWEEN :ini AND :fim
               ), 0),
               1
           ),
           0
       ) AS share
FROM itens_pedido i
JOIN pedidos p ON p.id = i.pedido_id
JOIN produtos pr ON pr.id = i.produto_id
WHERE p.status = 'aprovado'
  AND DATE(p.data_pedido) BETWEEN :ini AND :fim
GROUP BY pr.id, pr.nome, pr.categoria
ORDER BY receita DESC
LIMIT 5

-- name: fat_categoria
-- Recursos SQL aplicados: JOIN (3 tabelas) + GROUP BY categoria (alimenta o grafico de rosca)
SELECT pr.categoria,
       SUM(i.quantidade * i.valor_unitario) AS receita
FROM itens_pedido i
JOIN pedidos p ON p.id = i.pedido_id
JOIN produtos pr ON pr.id = i.produto_id
WHERE p.status = 'aprovado'
  AND DATE(p.data_pedido) BETWEEN :ini AND :fim
GROUP BY pr.categoria
ORDER BY receita DESC

-- name: recentes
-- Recursos SQL aplicados: JOIN + GROUP BY + ORDER BY data_pedido DESC (alimenta a tabela de transacoes)
SELECT p.id,
       c.nome AS cliente,
       c.estado,
       p.data_pedido,
       p.status,
       p.meio_pagamento,
       SUM(i.quantidade * i.valor_unitario) AS valor
FROM pedidos p
JOIN clientes c ON c.id = p.cliente_id
JOIN itens_pedido i ON i.pedido_id = p.id
WHERE DATE(p.data_pedido) BETWEEN :ini AND :fim
GROUP BY p.id, c.nome, c.estado, p.data_pedido, p.status, p.meio_pagamento
ORDER BY p.data_pedido DESC, p.id DESC
LIMIT 10

-- name: listar_produtos
SELECT id, nome, categoria, preco
FROM produtos
ORDER BY nome

-- name: listar_clientes
SELECT id, nome, email, estado
FROM clientes
ORDER BY nome

-- name: ultimos_pedidos_gestao
SELECT p.id,
       c.nome AS cliente,
       c.estado,
       p.data_pedido,
       p.status,
       p.meio_pagamento,
       COALESCE(SUM(i.quantidade * i.valor_unitario), 0) AS valor
FROM pedidos p
JOIN clientes c ON c.id = p.cliente_id
LEFT JOIN itens_pedido i ON i.pedido_id = p.id
GROUP BY p.id, c.nome, c.estado, p.data_pedido, p.status, p.meio_pagamento
ORDER BY p.id DESC
LIMIT 30
