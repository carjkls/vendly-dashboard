-- Vendly: Sistema de Vendas de Infoprodutos
-- Esquema relacional compativel com SQLite e PostgreSQL (Supabase)

DROP TABLE IF EXISTS itens_pedido;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS produtos;
DROP TABLE IF EXISTS clientes;

CREATE TABLE clientes (
    id     INTEGER PRIMARY KEY,
    nome   VARCHAR(100) NOT NULL,
    email  VARCHAR(120) NOT NULL UNIQUE,
    estado CHAR(2)      NOT NULL
);

CREATE TABLE produtos (
    id        INTEGER PRIMARY KEY,
    nome      VARCHAR(120)  NOT NULL,
    categoria VARCHAR(40)   NOT NULL,
    preco     NUMERIC(10,2) NOT NULL
);

CREATE TABLE pedidos (
    id             INTEGER     PRIMARY KEY,
    cliente_id     INTEGER     NOT NULL REFERENCES clientes(id),
    data_pedido    TIMESTAMP   NOT NULL,
    status         VARCHAR(20) NOT NULL,   -- aprovado, pendente, reembolsado
    meio_pagamento VARCHAR(20) NOT NULL    -- pix, cartao, boleto
);

CREATE TABLE itens_pedido (
    id             INTEGER       PRIMARY KEY,
    pedido_id      INTEGER       NOT NULL REFERENCES pedidos(id),
    produto_id     INTEGER       NOT NULL REFERENCES produtos(id),
    quantidade     INTEGER       NOT NULL,
    valor_unitario NUMERIC(10,2) NOT NULL
);
