import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import carregar_dados, get_remote_hash, URL_PARQUET

# === Configurações iniciais ===
st.set_page_config(layout="wide", page_title="Médias Móveis - Líquidos", page_icon="💧")
st.title("💧 Visualizador de Séries Temporais - Líquidos")

# === Dados e filtro fixo ===
df = carregar_dados()
fontes_l = ["BAR_Au_L", "LIX_Au_L", "TQ1_Au_L", "TQ2_Au_L", "TQ6_Au_L", "TQ7_Au_L", "REJ_Au_L"]

if df.empty:
    st.warning("Nenhum dado disponível.")
    st.stop()

# === Datas ===
data_max = df["DataHoraReal"].max()
data_min_total = df["DataHoraReal"].min()
data_min_default = data_max - pd.Timedelta(days=30)

# === Estado Inicial ===
st.session_state.setdefault("periodo", [data_min_default.date(), data_max.date()])
st.session_state.setdefault("periodo_movel", 6)
st.session_state.setdefault("grafico_unico", True)

# === Sidebar: botões lado a lado ===
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("🔁 Recarregar", key="recarregar_dados"):
        st.cache_data.clear()
        st.session_state.hash_parquet = None
        st.toast("📦 Dados recarregados manualmente!")

with col2:
    if st.button("🔄 Resetar", key="resetar_filtros"):
        st.session_state["periodo"] = [data_min_default.date(), data_max.date()]
        st.session_state["periodo_movel"] = 6
        st.session_state["grafico_unico"] = True

# === Datas lado a lado ===
col3, col4 = st.sidebar.columns(2)

with col3:
    data_inicio = st.date_input(
        "Início",
        value=st.session_state["periodo"][0],
        min_value=data_min_total.date(),
        max_value=data_max.date(),
        key="data_inicio"
    )

with col4:
    data_fim = st.date_input(
        "Fim",
        value=st.session_state["periodo"][1],
        min_value=data_min_total.date(),
        max_value=data_max.date(),
        key="data_fim"
    )

st.session_state["periodo"] = [data_inicio, data_fim]

st.sidebar.caption(f"Intervalo disponível: {data_min_total.date()} a {data_max.date()}")

# === Atualização por hash remoto ===
novo_hash = get_remote_hash(URL_PARQUET)
hash_antigo = st.session_state.get("hash_parquet")
if novo_hash and novo_hash != hash_antigo:
    st.cache_data.clear()
    st.session_state.hash_parquet = novo_hash
    st.toast("🆕 Novo conteúdo detectado!")

# === Sidebar: demais filtros ===
st.sidebar.header("Configurações")

periodo_movel = st.sidebar.slider("Média Móvel (períodos):", 1, 20, value=st.session_state["periodo_movel"], key="periodo_movel")
grafico_unico = st.sidebar.checkbox("Exibir em gráfico único", value=st.session_state["grafico_unico"], key="grafico_unico")

# === Fontes com toggle individual e sequência lógica ===
st.sidebar.markdown("### Fontes disponíveis")

fontes_disponiveis = sorted(df["Fonte"].unique())

# Sequência lógica desejada (pode incluir líquidos, sólidos e outras em ordem preferida)
sequencia_desejada = [
    "BAR_Au_L", "LIX_Au_L", "TQ1_Au_L", "TQ2_Au_L", "TQ6_Au_L", "TQ7_Au_L", "REJ_Au_L",
    "LIX_Au_S", "TQ2_Au_S", "TQ6_Au_S", "REJ_Au_S"
]

# Reorganiza fontes conforme sequência
fontes_ordenadas = [f for f in sequencia_desejada if f in fontes_disponiveis] + \
                   [f for f in fontes_disponiveis if f not in sequencia_desejada]

# Classifica por tipo
fontes_liquidas = [f for f in fontes_ordenadas if f.endswith("_L")]
fontes_solidas = [f for f in fontes_ordenadas if f.endswith("_S")]
fontes_outras = [f for f in fontes_ordenadas if not f.endswith("_L") and not f.endswith("_S")]

fontes_selecionadas = []

if fontes_liquidas:
    st.sidebar.markdown("**💧 Fontes Líquidas**")
    for fonte in fontes_liquidas:
        if st.sidebar.toggle(fonte, value=True, key=f"toggle_{fonte}"):
            fontes_selecionadas.append(fonte)

if fontes_solidas:
    st.sidebar.markdown("**🪨 Fontes Sólidas**")
    for fonte in fontes_solidas:
        if st.sidebar.toggle(fonte, value=True, key=f"toggle_{fonte}"):
            fontes_selecionadas.append(fonte)

if fontes_outras:
    st.sidebar.markdown("**📦 Outras Fontes**")
    for fonte in fontes_outras:
        if st.sidebar.toggle(fonte, value=True, key=f"toggle_{fonte}"):
            fontes_selecionadas.append(fonte)

fontes_sel = fontes_selecionadas

# === Filtragem base para todas as abas ===
inicio = data_inicio
fim = data_fim

df_filtrado = df[
    (df["Fonte"].isin(fontes_sel)) &
    (df["DataHoraReal"].dt.date >= inicio) &
    (df["DataHoraReal"].dt.date <= fim)
].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

# === Dados da Aba 1: apenas fontes líquidas ===
df_liquido = df_filtrado[df_filtrado["Fonte"].isin(fontes_l)].copy()

if not df_liquido.empty:
    df_liquido["MediaMovel"] = df_liquido.groupby("Fonte")["Valor"].transform(
        lambda x: x.rolling(window=periodo_movel, min_periods=1).mean()
    )

# === Criação das abas ===
nomes_abas = [
    "Líquido Au", "Aba 2", "Aba 3", "Aba 4", "Aba 5",
    "Aba 6", "Aba 7", "Aba 8", "Aba 9", "Aba 10"
]
abas = st.tabs(nomes_abas)

# === Aba 1: Líquido Au ===
with abas[0]:
    if df_liquido.empty:
        st.warning("Nenhum dado disponível para as fontes líquidas selecionadas.")
    else:
        if grafico_unico:
            fig = go.Figure()
            for fonte in fontes_l:
                if fonte not in df_liquido["Fonte"].unique():
                    continue
                dados_fonte = df_liquido[df_liquido["Fonte"] == fonte]
                fig.add_trace(go.Scatter(
                    x=dados_fonte["DataHoraReal"],
                    y=dados_fonte["MediaMovel"],
                    mode="lines",
                    name=fonte
                ))
            fig.update_layout(
                title=f"Médias Móveis - {periodo_movel} períodos",
                xaxis_title="Data",
                yaxis_title="Valor",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            for fonte in fontes_l:
                if fonte not in df_liquido["Fonte"].unique():
                    continue
                dados_fonte = df_liquido[df_liquido["Fonte"] == fonte]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dados_fonte["DataHoraReal"],
                    y=dados_fonte["Valor"],
                    mode="markers",
                    name="Bruto",
                    marker=dict(size=4, color="lightgray")
                ))
                fig.add_trace(go.Scatter(
                    x=dados_fonte["DataHoraReal"],
                    y=dados_fonte["MediaMovel"],
                    mode="lines",
                    name="Média Móvel"
                ))
                fig.update_layout(
                    title=fonte,
                    xaxis_title="Data",
                    yaxis_title="Valor",
                    height=500
                )
                st.subheader(fonte)
                st.plotly_chart(fig, use_container_width=True)

# === Abas vazias ===
for i in range(1, 10):
    with abas[i]:
        st.subheader(f"Conteúdo da {nomes_abas[i]}")
        st.info("📝 Esta aba ainda está vazia. Você pode editá-la posteriormente.")
