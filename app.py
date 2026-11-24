import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

ALUNO = "Carlos Eduardo"
DISCIPLINA = "Banco de Dados · UNIFSA"
BASE = Path(__file__).parent

ESMERALDA = "#10b981"
CIANO = "#06b6d4"
PALETA_ROSCA = ["#10b981", "#06b6d4", "#3b82f6", "#6366f1", "#14b8a6"]

NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}
UFS = list(NOMES_UF.keys())

st.set_page_config(page_title="Vendly · Analytics", page_icon=":material/insights:", layout="wide")

st.markdown(
    """
<style>
.stApp { background: radial-gradient(circle at 15% 0%, #0f172a 0%, #090d16 55%); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #060911; border-right: 1px solid #162032; }
[class*="st-key-card"] {
    position: relative; overflow: hidden; padding: 1rem 1.2rem;
    background: linear-gradient(180deg, #111827 0%, #0b101b 100%);
    border: 1px solid #1e293b; border-radius: 14px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
}
[class*="st-key-card"]::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #10b981, #06b6d4, transparent);
}
[data-testid="stMetricLabel"] p {
    font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: #94a3b8;
}
[data-testid="stMetricValue"] { font-weight: 700; color: #f8fafc; }
.badge-db {
    display: inline-block; padding: .28rem .65rem; border-radius: 999px;
    font-size: .75rem; font-weight: 600; letter-spacing: .03em;
    background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);
}
</style>
""",
    unsafe_allow_html=True,
)


def obter_url_banco() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        try:
            url = str(st.secrets.get("DATABASE_URL", "")).strip()
        except Exception:
            url = ""
    if not url:
        db_local = BASE / "vendly.db"
        if not db_local.exists():
            eng = create_engine(f"sqlite:///{db_local.as_posix()}")
            with eng.begin() as c:
                for arq in ("schema.sql", "seed.sql"):
                    for stmt in (BASE / arq).read_text(encoding="utf-8").split(";\n"):
                        limpo = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
                        if limpo:
                            c.exec_driver_sql(limpo)
        return f"sqlite:///{db_local.as_posix()}"

    url = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def carregar_queries() -> dict[str, str]:
    out, nome = {}, None
    for linha in (BASE / "queries.sql").read_text(encoding="utf-8").splitlines():
        if linha.startswith("-- name:"):
            nome = linha.split(":", 1)[1].strip()
            out[nome] = []
        elif nome:
            out[nome].append(linha)
    return {k: "\n".join(v).strip() for k, v in out.items()}


URL_BANCO = obter_url_banco()
EH_POSTGRES = URL_BANCO.startswith("postgresql")
ROTULO_BANCO = "PostgreSQL · Supabase (Nuvem)" if EH_POSTGRES else "SQLite · Local"
CONNECT_ARGS = {"prepare_threshold": None} if URL_BANCO.startswith("postgresql+psycopg://") else {}

QUERIES = carregar_queries()
conn = st.connection("sql", url=URL_BANCO, connect_args=CONNECT_ARGS)


def q(nome: str, **params) -> pd.DataFrame:
    # ttl=0 garante leitura em tempo real para demonstracao de alteracoes no banco ao vivo
    return conn.query(QUERIES[nome], params=params, ttl=0)


def sincronizar_sequence_pg(sessao, tabela: str, novo_id: int) -> None:
    if EH_POSTGRES:
        seq = sessao.execute(text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": tabela}).scalar()
        if seq:
            sessao.execute(text("SELECT setval(:s, GREATEST((SELECT COALESCE(MAX(id), 1) FROM " + tabela + "), :v))"), {"s": seq, "v": novo_id})


def brl(v) -> str:
    return "R$ " + f"{float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def variacao(atual, anterior) -> str | None:
    return f"{(float(atual) - float(anterior)) / float(anterior) * 100:+.1f}%" if anterior and float(anterior) > 0 else None


def estilo(fig: go.Figure, altura: int = 310) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=10, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=12),
        xaxis=dict(gridcolor="#162032", zeroline=False),
        yaxis=dict(gridcolor="#162032", zeroline=False),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
    )
    return fig


def mostrar(fig: go.Figure, alt: str) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False}, alt=alt)


@st.cache_data
def carregar_geojson() -> dict:
    return json.loads((BASE / "data" / "br_states.geojson").read_text(encoding="utf-8"))


# ---------- Sidebar (Filtros Globais e Status) ----------
hoje = date.today()
PERIODOS = {
    "Hoje": (hoje, hoje),
    "Ontem": (hoje - timedelta(1), hoje - timedelta(1)),
    "7d": (hoje - timedelta(6), hoje),
    "30d": (hoje - timedelta(29), hoje),
    "Tudo": (date(2000, 1, 1), date(2030, 12, 31)),
}

with st.sidebar:
    st.markdown("## :material/insights: Vendly")
    st.markdown(f'<span class="badge-db">● {ROTULO_BANCO}</span>', unsafe_allow_html=True)
    st.divider()
    periodo = st.segmented_control("Período de análise", list(PERIODOS), default="30d") or "30d"
    min_vendas = st.number_input(
        "Mín. de vendas por UF (HAVING)",
        min_value=1,
        max_value=50,
        value=1,
        help="Controla a cláusula HAVING COUNT(DISTINCT p.id) >= :min_vendas na consulta do Mapa.",
    )
    if st.button(":material/refresh: Atualizar dados agora", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"**Aluno:** {ALUNO}")
    st.caption(DISCIPLINA)

ini, fim = PERIODOS[periodo]
dias = (fim - ini).days + 1
anterior = None if periodo == "Tudo" else (ini - timedelta(dias), ini - timedelta(1))
P = dict(ini=ini, fim=fim)

# ---------- Cabeçalho Principal ----------
col_titulo, col_acao = st.columns([4, 1])
with col_titulo:
    st.title(f"Olá, {ALUNO}")
    st.caption(f"Painel analítico de vendas de infoprodutos · Período ativo: **{periodo}** · Fonte: **{ROTULO_BANCO}**")
with col_acao:
    st.write("")
    if st.button(":material/sync: Sincronizar", width="stretch"):
        st.cache_data.clear()
        st.rerun()

aba_dash, aba_crud, aba_sql = st.tabs([
    ":material/space_dashboard: Visão Geral (Dashboard)",
    ":material/bolt: Operações Ao Vivo (Banco)",
    ":material/database: Consultas SQL (Explicação)",
])

# ==============================================================================
# ABA 1: DASHBOARD ANALITICO
# ==============================================================================
with aba_dash:
    k = q("kpis", **P).iloc[0]
    kp = q("kpis", ini=anterior[0], fim=anterior[1]).iloc[0] if anterior else None
    t = q("taxa_aprovacao", **P).iloc[0]
    taxa = (float(t.aprovados) / float(t.total_pedidos) * 100) if t.total_pedidos else 0.0

    def card_kpi(coluna, chave: str, rotulo: str, valor, delta=None):
        with coluna.container(key=f"card_kpi_{chave}"):
            st.metric(rotulo, valor, delta=delta)

    # Linha 1: 4 Indicadores Principais em linha horizontal
    c1, c2, c3, c4 = st.columns(4)
    card_kpi(c1, "fat", "Faturamento aprovado", brl(k.faturamento), variacao(k.faturamento, kp.faturamento) if kp is not None else None)
    card_kpi(c2, "vendas", "Vendas aprovadas", int(k.vendas), variacao(k.vendas, kp.vendas) if kp is not None else None)
    card_kpi(c3, "ticket", "Ticket médio", brl(k.ticket_medio), variacao(k.ticket_medio, kp.ticket_medio) if kp is not None else None)
    card_kpi(c4, "taxa", "Taxa de aprovação", f"{taxa:.1f}%".replace(".", ","))

    # Linha 2: Mapa do Brasil em destaque na esquerda + Extremos (MAX/MIN) e Evolucao na direita
    col_mapa, col_dir = st.columns([1.05, 0.95])

    with col_mapa.container(key="card_mapa"):
        est = q("vendas_estado", min_vendas=int(min_vendas), **P)
        total_uf_vendas = int(est.vendas.sum()) if not est.empty else 0
        st.subheader("Distribuição geográfica de vendas")
        st.caption(f"{total_uf_vendas} vendas em **{len(est)} estados** (filtro `HAVING >= {int(min_vendas)}`)")

        df_mapa = (
            pd.DataFrame({"estado": UFS})
            .merge(est, how="left", on="estado")
            .fillna({"vendas": 0, "faturamento": 0.0})
        )
        df_mapa["nome_uf"] = df_mapa["estado"].map(NOMES_UF)

        fig_mapa = go.Figure(
            go.Choropleth(
                geojson=carregar_geojson(),
                featureidkey="properties.sigla",
                locations=df_mapa.estado,
                z=df_mapa.vendas.astype(float),
                customdata=df_mapa[["nome_uf", "faturamento"]].values,
                zmin=0,
                colorscale=[[0, "#131c2e"], [0.02, "#064e3b"], [0.45, "#059669"], [1, ESMERALDA]],
                marker_line_color="#090d16",
                marker_line_width=0.8,
                showscale=False,
                hovertemplate="<b>%{customdata[0]} (%{location})</b><br>%{z:.0f} vendas aprovadas<br>R$ %{customdata[1]:,.2f}<extra></extra>",
            )
        )
        fig_mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        mostrar(estilo(fig_mapa, 315), "Mapa coroplético do Brasil por volume de vendas")

        if not est.empty:
            st.dataframe(
                est.head(5),
                hide_index=True,
                width="stretch",
                column_config={
                    "estado": "UF",
                    "vendas": st.column_config.ProgressColumn(
                        "Vendas",
                        min_value=0,
                        max_value=max(int(est.vendas.max()), 1),
                        format="%d",
                    ),
                    "faturamento": st.column_config.NumberColumn("Faturamento", format="R$ %.2f"),
                },
            )
        else:
            st.info("Nenhum estado atingiu o mínimo de vendas configurado no filtro HAVING.")

    with col_dir:
        m1, m2 = st.columns(2)
        card_kpi(m1, "max", "Maior venda (MAX)", brl(k.maior_venda))
        card_kpi(m2, "min", "Menor venda (MIN)", brl(k.menor_venda))

        with st.container(key="card_linha"):
            st.subheader("Evolução diária de faturamento")
            fim_grafico = hoje if periodo == "Tudo" else fim
            c_ini = min(ini if periodo != "Tudo" else hoje - timedelta(days=29), fim_grafico - timedelta(days=6))
            n_dias = (fim_grafico - c_ini).days + 1

            def serie_diaria(a: date, b: date) -> pd.Series:
                df_d = q("faturamento_dia", ini=a, fim=b)
                if df_d.empty:
                    return pd.Series(0.0, index=pd.date_range(a, b))
                s = pd.Series(df_d.faturamento.astype(float).values, index=pd.to_datetime(df_d.dia))
                return s.reindex(pd.date_range(a, b), fill_value=0.0)

            atual = serie_diaria(c_ini, fim_grafico)
            fig_linha = go.Figure()
            if periodo != "Tudo":
                ant = serie_diaria(c_ini - timedelta(n_dias), c_ini - timedelta(1))
                ant.index = ant.index + pd.Timedelta(days=n_dias)
                fig_linha.add_scatter(
                    x=ant.index,
                    y=ant.values,
                    name="Período anterior",
                    line=dict(color=CIANO, width=1.8, dash="dot"),
                )
            fig_linha.add_scatter(
                x=atual.index,
                y=atual.values,
                name="Período atual",
                line=dict(color=ESMERALDA, width=2.6),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.14)",
            )
            mostrar(estilo(fig_linha, 385), "Curva de faturamento por dia")

    # Linha 3: Rosca de Categorias na esquerda + Barras Horizontais Top Produtos na direita
    col_cat, col_prod = st.columns([0.9, 1.1])

    with col_cat.container(key="card_categorias"):
        st.subheader("Receita por categoria")
        cat = q("fat_categoria", **P)
        if not cat.empty:
            fig_cat = go.Figure(
                go.Pie(
                    labels=cat.categoria,
                    values=cat.receita.astype(float),
                    hole=0.64,
                    sort=False,
                    marker=dict(colors=PALETA_ROSCA, line=dict(color="#0b101b", width=2)),
                    textinfo="percent+label",
                    textposition="inside",
                )
            )
            fig_cat.update_layout(showlegend=False)
            mostrar(estilo(fig_cat, 300), "Participação de cada categoria no faturamento")
        else:
            st.info("Sem vendas aprovadas no período selecionado.")

    with col_prod.container(key="card_produtos"):
        st.subheader("Top 5 infoprodutos (com % via Subquery)")
        top = q("top_produtos", **P)
        if not top.empty:
            max_rec = float(top.receita.max())
            fig_bar = go.Figure(
                go.Bar(
                    x=top.receita.astype(float)[::-1],
                    y=top.produto[::-1],
                    orientation="h",
                    marker=dict(color=ESMERALDA, cornerradius=6),
                    text=[f"R$ {float(r):,.0f} ({s}%)".replace(",", ".") for r, s in zip(top.receita[::-1], top.share[::-1])],
                    textposition="outside",
                )
            )
            fig_bar.update_xaxes(range=[0, max_rec * 1.28])
            mostrar(estilo(fig_bar, 300), "Receita e participação dos 5 produtos mais vendidos")
        else:
            st.info("Sem produtos vendidos no período selecionado.")

    # Linha 4: Tabela de Vendas Recentes
    with st.container(key="card_recentes"):
        st.subheader("Últimas transações registradas")
        rec = q("recentes", **P)
        st.dataframe(
            rec,
            hide_index=True,
            width="stretch",
            column_config={
                "id": st.column_config.NumberColumn("Pedido #", format="#%d"),
                "cliente": "Cliente",
                "estado": "UF",
                "data_pedido": "Data / Hora",
                "status": "Status",
                "meio_pagamento": "Pagamento",
                "valor": st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
            },
        )

# ==============================================================================
# ABA 2: OPERACOES AO VIVO NO BANCO DE DADOS (CRUD REAL)
# ==============================================================================
with aba_crud:
    st.markdown("### Simulador de Checkout & Gestão de Pedidos em Tempo Real")
    st.caption(
        "Todas as ações abaixo executam comandos `INSERT`, `UPDATE` e `DELETE` reais no banco de dados "
        "e atualizam imediatamente os KPIs, gráficos e o mapa do Brasil."
    )

    produtos_df = q("listar_produtos")
    clientes_df = q("listar_clientes")
    gestao_df = q("ultimos_pedidos_gestao")

    col_ins, col_upd = st.columns(2)

    with col_ins.container(key="card_nova_venda"):
        st.subheader(":material/add_shopping_cart: Registrar Nova Venda (`INSERT`)")
        modo_cliente = st.radio(
            "Origem do comprador",
            ["Cadastrar novo cliente (escolher estado)", "Selecionar cliente existente"],
            horizontal=True,
        )

        with st.form("form_nova_venda", clear_on_submit=False):
            if modo_cliente.startswith("Cadastrar"):
                c_nome, c_uf = st.columns([2, 1])
                novo_nome = c_nome.text_input("Nome do cliente", placeholder="Ex.: Prof. Avaliador")
                uf_escolhida = c_uf.selectbox(
                    "Estado (UF)",
                    options=UFS,
                    index=UFS.index("AC"),
                    format_func=lambda u: f"{u} - {NOMES_UF[u]}",
                    help="Estados como AC, AP, RO, RR e TO começam sem vendas — ótimo para acender no mapa ao vivo!",
                )
                novo_email = st.text_input("E-mail (opcional)", placeholder="Gerado automaticamente se vazio")
                cliente_id_sel = None
            else:
                opcoes_cli = {
                    int(r.id): f"{r.nome} ({r.estado}) · #{int(r.id)}"
                    for _, r in clientes_df.iterrows()
                }
                cliente_id_sel = st.selectbox("Cliente cadastrado", options=list(opcoes_cli.keys()), format_func=lambda x: opcoes_cli[x])
                novo_nome, uf_escolhida, novo_email = "", "", ""

            opcoes_prod = {
                int(r.id): (r.nome, float(r.preco))
                for _, r in produtos_df.iterrows()
            }
            # Seleciona Mentoria Instagram Pro (R$ 250) como sugestao padrao
            idx_padrao = list(opcoes_prod.keys()).index(7) if 7 in opcoes_prod else 0
            prod_id = st.selectbox(
                "Infoproduto",
                options=list(opcoes_prod.keys()),
                index=idx_padrao,
                format_func=lambda pid: f"{opcoes_prod[pid][0]} — {brl(opcoes_prod[pid][1])}",
            )

            f1, f2, f3 = st.columns(3)
            qtd = f1.number_input("Quantidade", min_value=1, max_value=20, value=2)
            meio_pag = f2.selectbox("Pagamento", ["pix", "cartao", "boleto"])
            status_ini = f3.selectbox("Status", ["aprovado", "pendente"])

            preco_unit = opcoes_prod[prod_id][1]
            st.caption(f"Valor total calculado do pedido: **{brl(preco_unit * qtd)}**")

            enviar_venda = st.form_submit_button("Gravar Venda no Banco de Dados", type="primary", width="stretch")

        if enviar_venda:
            if modo_cliente.startswith("Cadastrar") and not novo_nome.strip():
                st.error("Informe o nome do cliente para registrar a venda.")
            else:
                agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with conn.session as s:
                    if modo_cliente.startswith("Cadastrar"):
                        cid = int(s.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM clientes")).scalar_one())
                        email_final = novo_email.strip() or f"cliente.{cid}.{int(time.time())}@vendly.com.br"
                        s.execute(
                            text("INSERT INTO clientes (id, nome, email, estado) VALUES (:id, :n, :e, :uf)"),
                            {"id": cid, "n": novo_nome.strip(), "e": email_final, "uf": uf_escolhida},
                        )
                        sincronizar_sequence_pg(s, "clientes", cid)
                    else:
                        cid = int(cliente_id_sel)

                    pid = int(s.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM pedidos")).scalar_one())
                    s.execute(
                        text(
                            "INSERT INTO pedidos (id, cliente_id, data_pedido, status, meio_pagamento) "
                            "VALUES (:id, :cid, :dt, :st, :mp)"
                        ),
                        {"id": pid, "cid": cid, "dt": agora_str, "st": status_ini, "mp": meio_pag},
                    )
                    sincronizar_sequence_pg(s, "pedidos", pid)

                    iid = int(s.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM itens_pedido")).scalar_one())
                    s.execute(
                        text(
                            "INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, valor_unitario) "
                            "VALUES (:id, :pid, :prid, :q, :vu)"
                        ),
                        {"id": iid, "pid": pid, "prid": prod_id, "q": int(qtd), "vu": preco_unit},
                    )
                    sincronizar_sequence_pg(s, "itens_pedido", iid)
                    s.commit()

                st.toast(f"Pedido #{pid} gravado com sucesso ({brl(preco_unit * qtd)})!", icon=":material/check_circle:")
                st.success(f"Pedido **#{pid}** registrado no banco ({brl(preco_unit * qtd)} · status `{status_ini}`). Volte à aba **Visão Geral** para ver os indicadores e o mapa atualizados!")
                st.rerun()

    with col_upd.container(key="card_gestao_pedido"):
        st.subheader(":material/edit_note: Alterar Status ou Excluir (`UPDATE` / `DELETE`)")
        if not gestao_df.empty:
            mapa_ped = {
                int(r.id): f"#{int(r.id)} · {r.cliente} ({r.estado}) · {brl(r.valor)} · [{r.status}]"
                for _, r in gestao_df.iterrows()
            }
            ped_escolhido = st.selectbox("Selecione um pedido recente", options=list(mapa_ped.keys()), format_func=lambda x: mapa_ped[x])
            status_atual = gestao_df.loc[gestao_df["id"] == ped_escolhido, "status"].iloc[0]

            opcoes_status = ["aprovado", "pendente", "reembolsado"]
            novo_st = st.segmented_control(
                "Novo status do pedido",
                options=opcoes_status,
                default=status_atual if status_atual in opcoes_status else "aprovado",
            ) or status_atual

            b_upd, b_del = st.columns(2)
            if b_upd.button("Atualizar Status (UPDATE)", type="primary", width="stretch"):
                with conn.session as s:
                    s.execute(text("UPDATE pedidos SET status = :st WHERE id = :id"), {"st": novo_st, "id": int(ped_escolhido)})
                    s.commit()
                st.toast(f"Pedido #{ped_escolhido} alterado para '{novo_st}'!", icon=":material/sync_saved_locally:")
                st.rerun()

            if b_del.button("Excluir Pedido (DELETE)", width="stretch"):
                with conn.session as s:
                    s.execute(text("DELETE FROM itens_pedido WHERE pedido_id = :id"), {"id": int(ped_escolhido)})
                    s.execute(text("DELETE FROM pedidos WHERE id = :id"), {"id": int(ped_escolhido)})
                    s.commit()
                st.toast(f"Pedido #{ped_escolhido} removido do banco.", icon=":material/delete:")
                st.rerun()

            st.divider()
            st.caption("Últimos pedidos no banco (tempo real):")
            st.dataframe(
                gestao_df.head(7),
                hide_index=True,
                width="stretch",
                column_config={
                    "id": st.column_config.NumberColumn("#ID", format="#%d"),
                    "cliente": "Cliente",
                    "estado": "UF",
                    "status": "Status",
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                },
            )
        else:
            st.info("Nenhum pedido encontrado.")

    with st.expander(":material/terminal: Comandos SQL prontos para testar direto no painel do Supabase"):
        st.markdown("Caso queira demonstrar uma alteração **direto pelo SQL Editor do Supabase** durante a apresentação:")
        st.code(
            """-- 1) Inserir cliente em Roraima (RR) + venda de alto valor para acender o estado RR no mapa e mudar o MAX:
INSERT INTO clientes (nome, email, estado) VALUES ('Cliente Demo Ao Vivo', 'demo.aovivo@unifsa.br', 'RR');

INSERT INTO pedidos (cliente_id, data_pedido, status, meio_pagamento)
VALUES ((SELECT MAX(id) FROM clientes), CURRENT_TIMESTAMP, 'aprovado', 'pix');

INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, valor_unitario)
VALUES ((SELECT MAX(id) FROM pedidos), 7, 4, 250.00);

-- 2) Aprovar todos os pedidos pendentes de hoje:
UPDATE pedidos SET status = 'aprovado' WHERE status = 'pendente';""",
            language="sql",
        )

# ==============================================================================
# ABA 3: EXPLICACAO DAS CONSULTAS SQL OBRIGATORIAS
# ==============================================================================
with aba_sql:
    st.markdown("### Mapeamento dos Recursos SQL Obrigatórios")
    st.caption("Todas as consultas abaixo ficam no arquivo `queries.sql` e alimentam diretamente os indicadores e gráficos.")

    matriz_sql = pd.DataFrame([
        {"Recurso SQL": "MIN", "Consulta em queries.sql": "kpis", "Aplicação no Negócio": "Identifica a venda aprovada de menor valor no período (KPI Menor Venda)."},
        {"Recurso SQL": "MAX", "Consulta em queries.sql": "kpis", "Aplicação no Negócio": "Identifica a venda aprovada de maior valor no período (KPI Maior Venda)."},
        {"Recurso SQL": "GROUP BY", "Consulta em queries.sql": "kpis, faturamento_dia, vendas_estado, top_produtos, fat_categoria", "Aplicação no Negócio": "Agrupa itens por pedido, vendas por dia, por estado (UF), por produto e por categoria."},
        {"Recurso SQL": "HAVING", "Consulta em queries.sql": "vendas_estado", "Aplicação no Negócio": "Filtra no Mapa do Brasil apenas estados com volume mínimo de vendas aprovadas (>= filtro lateral)."},
        {"Recurso SQL": "SUBQUERY", "Consulta em queries.sql": "kpis e top_produtos", "Aplicação no Negócio": "Tabela derivada para somar o total de cada pedido (kpis) e subquery escalar para calcular % de share de cada produto."},
        {"Recurso SQL": "JOIN", "Consulta em queries.sql": "Todas as consultas analíticas", "Aplicação no Negócio": "Relaciona pedidos, itens_pedido, clientes e produtos para consolidar valor, UF e categoria."},
    ])
    with st.container(key="card_matriz_sql"):
        st.dataframe(matriz_sql, hide_index=True, width="stretch")

    consultas_exibir = [
        ("kpis", "1. Indicadores Gerais (`SUBQUERY` + `JOIN` + `GROUP BY` + `MIN` + `MAX`)"),
        ("vendas_estado", "2. Mapa de Vendas por Estado (`JOIN` + `GROUP BY` + `HAVING`)"),
        ("top_produtos", "3. Top 5 Infoprodutos (`JOIN` + `GROUP BY` + `SUBQUERY` escalar)"),
        ("faturamento_dia", "4. Evolução Diária de Faturamento (`JOIN` + `GROUP BY`)"),
        ("fat_categoria", "5. Receita por Categoria (`JOIN` + `GROUP BY`)"),
        ("recentes", "6. Últimas Transações (`JOIN` + `GROUP BY`)"),
    ]
    for chave, titulo in consultas_exibir:
        with st.expander(titulo, expanded=(chave in ("kpis", "vendas_estado"))):
            st.code(QUERIES[chave], language="sql")
