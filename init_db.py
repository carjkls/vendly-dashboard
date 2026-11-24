"""Cria as tabelas e carrega os dados iniciais.
Por padrao usa SQLite local (vendly.db). Se DATABASE_URL estiver definida, popula o PostgreSQL/Supabase.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine

base = Path(__file__).parent


def normalizar_url(url: str) -> str:
    url = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


db_url = normalizar_url(os.getenv("DATABASE_URL", f"sqlite:///{(base / 'vendly.db').as_posix()}"))
connect_args = {"prepare_threshold": None} if db_url.startswith("postgresql+psycopg://") else {}
engine = create_engine(db_url, connect_args=connect_args)

with engine.begin() as conn:
    if engine.dialect.name == "postgresql" and (base / "supabase_full.sql").exists():
        arquivos = ("supabase_full.sql",)
    else:
        arquivos = ("schema.sql", "seed.sql")

    for arquivo in arquivos:
        conteudo = (base / arquivo).read_text(encoding="utf-8")
        for stmt in conteudo.split(";\n"):
            limpo = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
            if limpo:
                conn.exec_driver_sql(limpo)

print(f"Banco pronto ({engine.dialect.name}).")
