import os
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

import folium
from folium import GeoJson, GeoJsonTooltip, LayerControl
from folium.plugins import HeatMap
from streamlit_folium import st_folium

import altair as alt
import streamlit.components.v1 as components
from urllib.error import HTTPError
from branca.element import Template, MacroElement

# =============================
# Config geral
# =============================
st.set_page_config(
    page_title="Poços de Pedra Branca - Monitoramento",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TZ = ZoneInfo("America/Fortaleza")

# =============================
# Estilos Modernizados
# =============================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Header moderno com gradiente sofisticado */
.app-header {
    background: linear-gradient(135deg, #0c2461 0%, #1e3799 25%, #4a69bd 50%, #6a89cc 100%);
    padding: 2.5rem 2.5rem 2rem 2.5rem;
    border-radius: 0 0 24px 24px;
    margin: -1rem -1rem 2.5rem -1rem;
    color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #00b894, #0984e3, #00cec9);
}
.app-header h1 {
    margin: 0;
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #e0f7fa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}
.app-header p {
    margin: 0.8rem 0 0 0;
    font-size: 1.15rem;
    opacity: 0.9;
    font-weight: 400;
}

/* Cards KPI modernos com hover */
.kpi-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
    border-radius: 20px;
    padding: 1.5rem 1.2rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid rgba(255,255,255,0.8);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #00b894, #0984e3);
}
.kpi-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}
.kpi-label {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #636e72;
    margin-bottom: 0.5rem;
    font-weight: 600;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #2d3436;
    margin-bottom: 0.3rem;
    background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.kpi-sub {
    font-size: 0.8rem;
    color: #b2bec3;
    font-weight: 500;
}

/* Seções modernas */
.section-title {
    font-weight: 700;
    font-size: 1.3rem;
    margin: 1rem 0 1.2rem 0;
    color: #2d3436;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid #0984e3;
    display: inline-block;
}

/* Filtros modernos */
.stMultiSelect [data-baseweb="tag"] {
    background: linear-gradient(135deg, #74b9ff, #0984e3) !important;
    color: white !important;
    border-radius: 12px !important;
}

.stSelectbox>div>div {
    border-radius: 12px !important;
}

/* Container principal */
.main {
    background: #f8f9fa;
}

/* Badges e indicadores */
.status-badge {
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-instalado { background: #00b894; color: white; }
.status-nao-instalado { background: #e17055; color: white; }
.status-desativado { background: #636e72; color: white; }
.status-obstruido { background: #d63031; color: white; }
.status-injetado { background: #6c5ce7; color: white; }

/* Cards de métricas secundárias */
.metric-card {
    background: white;
    border-radius: 16px;
    padding: 1.2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border-left: 4px solid #0984e3;
    transition: all 0.2s ease;
}
.metric-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

/* Animações suaves */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

/* Scrollbar personalizada */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #74b9ff, #0984e3);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #0984e3, #074b83);
}
</style>
""", unsafe_allow_html=True)

# =============================
# Funções auxiliares
# =============================
def load_from_gsheet_csv(sheet_id: str, gid: str = "0", sep: str = ","):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, sep=sep)
    except HTTPError as e:
        st.error(f"Erro HTTP ao acessar o Google Sheets: {e}")
        raise
    except Exception as e:
        st.error(f"Erro ao ler o CSV do Google Sheets: {e}")
        raise
    return df

def gdrive_extract_id(url: str):
    if not isinstance(url, str):
        return None
    url = url.strip()
    m = re.search(r"/d/([a-zA-Z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    return None

def drive_image_urls(file_id: str):
    thumb = f"https://drive.google.com/thumbnail?id={file_id}&sz=w450"
    big = f"https://drive.google.com/thumbnail?id={file_id}&sz=w2048"
    return thumb, big

# ⬇️ Galeria no modelo antigo, com auto_open
def render_lightgallery_images(items: list, height_px=420, auto_open: bool = False):
    if not items:
        st.info("📷 Nenhuma foto encontrada para os filtros atuais.")
        return

    anchors = []
    for it in items:
        anchors.append(
            f"""
            <a class="gallery-item" href="{it['src']}" data-sub-html="{it.get('caption','')}">
                <img src="{it['thumb']}" loading="lazy"/>
            </a>
            """
        )
    items_html = "\n".join(anchors)

    auto_open_js = """
        const firstItem = container.querySelector('.gallery-item');
        if (firstItem) {
          firstItem.click();
        }
    """ if auto_open else ""

    html = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/css/lightgallery-bundle.min.css">
    <style>
      .lg-backdrop {{ background: rgba(0,0,0,0.92); }}
      .gallery-container {{
          display:flex;
          flex-wrap:wrap;
          gap: 12px;
          align-items:flex-start;
      }}
      .gallery-item img {{
          height: 120px;
          width:auto;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,.25);
          transition: transform 0.25s ease, box-shadow 0.25s ease;
      }}
      .gallery-item:hover img {{
          transform: scale(1.04);
          box-shadow: 0 6px 18px rgba(0,0,0,.32);
      }}
    </style>
    <div id="lg-gallery" class="gallery-container">{items_html}</div>

    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/lightgallery.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/zoom/lg-zoom.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/thumbnail/lg-thumbnail.umd.js"></script>

    <script>
      window.addEventListener('load', () => {{
        const container = document.getElementById('lg-gallery');
        if (!container) return;
        const lgInstance = lightGallery(container, {{
          selector: '.gallery-item',
          zoom: true,
          thumbnail: true,
          download: false,
          loop: true,
          plugins: [lgZoom, lgThumbnail]
        }});
        {auto_open_js}
      }});
    </script>
    """
    components.html(html, height=height_px, scrolling=True)

def make_popup_html(row):
    safe = lambda v: "-" if v in [None, "", np.nan] else str(v)

    campos = [
        ("Localidade", "📍"),
        ("Vazão_LH", "💧"),
        ("Vazão_estimada_LH", "📊"),
        ("Monitorado", "🛰️"),
        ("Instalado", "⚙️"),
        ("Status", "✅"),
        ("Caixas_apoio", "📦"),
        ("Observações", "📝"),
    ]

    linhas = []
    for col, icon in campos:
        if col not in row:
            continue
        val = row[col]
        if col in ["Vazão_LH", "Vazão_estimada_LH"] and pd.notna(val):
            try:
                val = f"{float(val):,.2f} L/h".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                pass
        if col == "Caixas_apoio" and pd.notna(val):
            try:
                val = int(val)
            except Exception:
                pass
        linhas.append(
            f"""
            <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.92em;border-bottom:1px solid rgba(255,255,255,0.1);">
                <span style="font-weight:500;">{icon} {col}:</span>
                <span style="font-weight:600;text-align:right;">{safe(val)}</span>
            </div>
            """
        )

    corpo = "\n".join(linhas)
    html = f"""
    <div style="
        font-family: 'Segoe UI', system-ui, sans-serif;
        padding: 16px;
        min-width:280px;
        max-width:360px;
        background: linear-gradient(135deg,#1e3799 0%,#0984e3 100%);
        border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
        color: white;
        border: 2px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(10px);
    ">
        <div style="
            background: rgba(255,255,255,0.15);
            padding: 10px 14px;
            border-radius: 14px;
            text-align:center;
            font-weight:700;
            font-size:1.1em;
            margin-bottom:12px;
            border: 1px solid rgba(255,255,255,0.2);
        ">
            📍 Poço Monitorado
        </div>
        {corpo}
    </div>
    """
    return html

def normaliza_lower(x):
    if x is None:
        return None
    return str(x).strip().lower()

def safe_sum(series):
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())

def to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None

# =============================
# Header Modernizado
# =============================
st.markdown("""
<div class="app-header fade-in">
  <h1>💧 Sistema de Monitoramento de Poços</h1>
  <p>Pedra Branca - Análise em tempo real dos poços monitorados no município</p>
</div>
""", unsafe_allow_html=True)

# =============================
# Barra de status e informações
# =============================
col_info1, col_info2, col_info3 = st.columns([2,1,1])

with col_info1:
    st.caption(
        f"🕐 Última atualização: {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')} "
        f"(Horário de Fortaleza)"
    )

with col_info2:
    st.caption("📊 Dados em tempo real")

with col_info3:
    if st.button("🔄 Atualizar Dados"):
        st.rerun()

# =============================
# Carrega dados
# =============================
SHEET_ID = "12mU_58X2Ezlr_tG7pcinh1kGMY1xgXXXKfyOlXj75rc"
GID = "1870024591"
SEP = ","

try:
    df = load_from_gsheet_csv(SHEET_ID, GID, sep=SEP)
except Exception:
    st.error("❌ Erro ao carregar dados da planilha. Verifique a conexão.")
    st.stop()

if df.empty:
    st.info("📋 Planilha sem dados disponíveis.")
    st.stop()

df = df.replace({np.nan: None})

if "Ano" in df.columns:
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")

if "Data_visita" in df.columns:
    df["_Data_dt"] = pd.to_datetime(df["Data_visita"], errors="coerce")
    df["Ano_visita"] = df["_Data_dt"].dt.year
    df["Mes_visita_num"] = df["_Data_dt"].dt.month
    meses_map = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    df["Mes_visita"] = df["Mes_visita_num"].map(meses_map)
else:
    df["Ano_visita"] = None
    df["Mes_visita"] = None

monitorado_map = {
    "sim": "Sim",
    "nao": "Não",
    "não": "Não"
}
instalado_map = {
    "sim": "Sim",
    "nao": "Não",
    "não": "Não"
}
status_map = {
    "instalado": "Instalado",
    "nao_instalado": "Não instalado",
    "não_instalado": "Não instalado",
    "desativado": "Desativado",
    "obstruido": "Obstruído",
    "obstruído": "Obstruído",
    "injetado": "Injetado",
}

if "Monitorado" in df.columns:
    df["Monitorado"] = df["Monitorado"].apply(
        lambda v: monitorado_map.get(normaliza_lower(v), v)
    )

if "Instalado" in df.columns:
    df["Instalado"] = df["Instalado"].apply(
        lambda v: instalado_map.get(normaliza_lower(v), v)
    )

if "Status" in df.columns:
    df["Status"] = df["Status"].apply(
        lambda v: status_map.get(normaliza_lower(v), v)
    )

# =============================
# Filtros Modernizados
# =============================
st.markdown("### 🔍 Filtros Avançados")

with st.expander("Filtros de Pesquisa", expanded=True):
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    # -------------------------
    # Ano da visita (liga/desliga)
    # -------------------------
    with col_f1:
        anos = []
        if "Ano_visita" in df.columns:
            anos = sorted([a for a in df["Ano_visita"].dropna().unique().tolist()])

        use_filter_ano = st.toggle("📅 Filtrar ano da visita", value=False)

        if use_filter_ano and anos:
            ano_sel = st.multiselect(
                "Ano da visita",
                options=anos,
                default=anos,
                help="Selecione os anos de visita"
            )
        else:
            ano_sel = None

    # -------------------------
    # Mês da visita (liga/desliga)
    # -------------------------
    with col_f2:
        meses = []
        if "Mes_visita" in df.columns:
            meses = [m for m in df["Mes_visita"].dropna().unique().tolist()]
            if meses:
                ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
                               "Jul","Ago","Set","Out","Nov","Dez"]
                meses = sorted(meses, key=lambda x: ordem_meses.index(x))

        use_filter_mes = st.toggle("🗓️ Filtrar mês da visita", value=False)

        if use_filter_mes and meses:
            mes_sel = st.multiselect(
                "Mês da visita",
                options=meses,
                default=meses
            )
        else:
            mes_sel = None

    # -------------------------
    # Município (sempre ativo)
    # -------------------------
    with col_f3:
        mun_opts = sorted([m for m in df["Município"].dropna().unique().tolist()]) if "Município" in df.columns else []
        mun_sel = st.multiselect(
            "🏙️ Município",
            options=mun_opts,
            default=mun_opts if mun_opts else None
        )

    # -------------------------
    # Bairro (sempre ativo)
    # -------------------------
    with col_f4:
        bairro_opts = sorted([b for b in df["Bairro"].dropna().unique().tolist()]) if "Bairro" in df.columns else []
        bairro_sel = st.multiselect(
            "📍 Bairro",
            options=bairro_opts,
            default=bairro_opts if bairro_opts else None
        )

    # Segunda linha
    col_f5, col_f6, col_f7 = st.columns(3)

    # -------------------------
    # Monitorado pela COGERH (liga/desliga)
    # -------------------------
    with col_f5:
        mon_opts = []
        if "Monitorado" in df.columns:
            mon_opts = sorted([m for m in df["Monitorado"].dropna().unique().tolist()])

        use_filter_mon = st.toggle("📡 Filtrar Monitorado pela COGERH", value=False)

        if use_filter_mon and mon_opts:
            mon_sel = st.multiselect(
                "Monitorado pela COGERH",
                options=mon_opts,
                default=mon_opts
            )
        else:
            mon_sel = None

    # -------------------------
    # Instalado / Estado (liga/desliga)
    # -------------------------
    with col_f6:
        inst_opts = []
        if "Instalado" in df.columns:
            inst_opts = sorted([m for m in df["Instalado"].dropna().unique().tolist()])

        use_filter_inst = st.toggle("⚙️ Filtrar Instalado/Estado", value=False)

        if use_filter_inst and inst_opts:
            inst_sel = st.multiselect(
                "Instalado/Estado",
                options=inst_opts,
                default=inst_opts
            )
        else:
            inst_sel = None

    # -------------------------
    # Status (sempre ativo)
    # -------------------------
    with col_f7:
        status_opts = sorted([s for s in df["Status"].dropna().unique().tolist()]) if "Status" in df.columns else []
        status_sel = st.multiselect(
            "✅ Status",
            options=status_opts,
            default=status_opts if status_opts else None
        )

# =============================
# Aplicação dos filtros
# =============================
fdf = df.copy()

# Ano da visita
if use_filter_ano and "Ano_visita" in fdf.columns and ano_sel:
    fdf = fdf[fdf["Ano_visita"].isin(ano_sel)]

# Mês da visita
if use_filter_mes and "Mes_visita" in fdf.columns and mes_sel:
    fdf = fdf[fdf["Mes_visita"].isin(mes_sel)]

# Município (sempre considerado se houver seleção)
if "Município" in fdf.columns and mun_opts and mun_sel:
    fdf = fdf[fdf["Município"].isin(mun_sel)]

# Bairro (sempre considerado se houver seleção)
if "Bairro" in fdf.columns and bairro_opts and bairro_sel:
    fdf = fdf[fdf["Bairro"].isin(bairro_sel)]

# Monitorado (condicional ao toggle)
if use_filter_mon and "Monitorado" in fdf.columns and mon_sel:
    fdf = fdf[fdf["Monitorado"].isin(mon_sel)]

# Instalado (condicional ao toggle)
if use_filter_inst and "Instalado" in fdf.columns and inst_sel:
    fdf = fdf[fdf["Instalado"].isin(inst_sel)]

# Status (sempre considerado se houver seleção)
if "Status" in fdf.columns and status_opts and status_sel:
    fdf = fdf[fdf["Status"].isin(status_sel)]



# =============================
# KPIs Modernizados
# =============================
st.markdown("### 📈 Indicadores Principais")

# Base para KPI: agregação por Latitude_2 quando existir
kpi_df = fdf.copy()

if "Latitude_2" in kpi_df.columns:
    # Separa quem não tem Latitude_2
    null_part = kpi_df[kpi_df["Latitude_2"].isna()].copy()
    non_null = kpi_df[kpi_df["Latitude_2"].notna()].copy()

    # Dicionário de agregação por poço (Latitude_2)
    agg_dict = {}

    # Colunas categóricas: pega a primeira ocorrência
    for col in ["Localidade", "Município", "Bairro", "Monitorado", "Instalado", "Status"]:
        if col in non_null.columns:
            agg_dict[col] = "first"

    # Colunas numéricas principais: pega o valor máximo registrado para o poço
    for col in ["Vazão_LH", "Vazão_estimada_LH", "Caixas_apoio"]:
        if col in non_null.columns:
            agg_dict[col] = "max"

    # Garante que Ano_visita não quebre o groupby (se quiser, pode pegar o último ano)
    if "Ano_visita" in non_null.columns and "Ano_visita" not in agg_dict:
        agg_dict["Ano_visita"] = "max"

    if agg_dict:
        non_null_grouped = (
            non_null
            .groupby("Latitude_2", as_index=False)
            .agg(agg_dict)
        )
    else:
        # fallback, se por algum motivo não tiver colunas mapeadas
        non_null_grouped = non_null.drop_duplicates(subset=["Latitude_2"]).copy()

    # Junta poços com Latitude_2 agregados + linhas sem Latitude_2
    kpi_df = pd.concat([non_null_grouped, null_part], ignore_index=True)

# Garante que Caixas_apoio esteja numérico para a soma
if "Caixas_apoio" in kpi_df.columns:
    kpi_df["Caixas_apoio"] = pd.to_numeric(kpi_df["Caixas_apoio"], errors="coerce")

total_pocos = len(kpi_df[kpi_df["Localidade"].notna()]) if "Localidade" in kpi_df.columns else len(kpi_df)
total_vazao = safe_sum(kpi_df["Vazão_LH"]) if "Vazão_LH" in kpi_df.columns else 0
total_vazao_est = safe_sum(kpi_df["Vazão_estimada_LH"]) if "Vazão_estimada_LH" in kpi_df.columns else 0
total_caixas = safe_sum(kpi_df["Caixas_apoio"]) if "Caixas_apoio" in kpi_df.columns else 0

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Total de Poços</div>
          <div class="kpi-value">{total_pocos}</div>
          <div class="kpi-sub">Ativos e monitorados</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Vazão Medida</div>
          <div class="kpi-value">
            {total_vazao:,.0f} L/h
          </div>
          <div class="kpi-sub">Total de vazão medida</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Vazão Estimada</div>
          <div class="kpi-value">
            {total_vazao_est:,.0f} L/h
          </div>
          <div class="kpi-sub">Projeção total</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Caixas de Apoio</div>
          <div class="kpi-value">{int(total_caixas) if not math.isnan(total_caixas) else 0}</div>
          <div class="kpi-sub">Infraestrutura instalada</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =============================
# Layout Mapa + Fotos
# =============================
st.markdown("---")
st.markdown('<div class="section-title">🗺️ Visualização Geográfica</div>', unsafe_allow_html=True)

col_map, col_fotos = st.columns([1.2, 1])

map_data = None

with col_map:
    st.markdown("#### Mapa Interativo dos Poços")
    
    with st.container():
        fmap = folium.Map(
            location=[-5.45, -39.7],
            zoom_start=11,
            control_scale=True,
            tiles=None
        )

        folium.TileLayer("CartoDB Positron", name="CartoDB Positron").add_to(fmap)
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(fmap)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            name="Imagem de Satélite",
            attr="Tiles © Esri"
        ).add_to(fmap)

        # Camada bairros
        try:
            with open("bairros_pb.geojson", "r", encoding="utf-8") as f:
                bairros = json.load(f)
            GeoJson(
                bairros,
                name="Bairros de Pedra Branca",
                style_function=lambda feat: {
                    "color": "#00b894",
                    "weight": 2,
                    "fillColor": "#00b894",
                    "fillOpacity": 0.05,
                },
                tooltip=GeoJsonTooltip(
                    fields=["NM_BAIRRO"],
                    aliases=["Bairro:"],
                    sticky=False
                )
            ).add_to(fmap)
        except Exception as e:
            st.warning(f"⚠️ Camada de bairros não disponível: {e}")

        fg_pocos = folium.FeatureGroup(name="Poços (Status)", show=True)
        pts = []

        status_colors = {
            "Instalado": "#00b894",
            "Não instalado": "#e17055",
            "Desativado": "#636e72",
            "Obstruído": "#d63031",
            "Injetado": "#6c5ce7",
        }
        default_color = "#0984e3"

        lat_col = "latitude" if "latitude" in fdf.columns else None
        lon_col = "longitude" if "longitude" in fdf.columns else None

        if lat_col and lon_col:
            for _, row in fdf.iterrows():
                lat = to_float(row.get(lat_col))
                lon = to_float(row.get(lon_col))
                if lat is None or lon is None:
                    continue

                status = row.get("Status", "")
                color = status_colors.get(str(status), default_color)

                popup_html = make_popup_html(row)
                popup = folium.Popup(popup_html, max_width=360)

                tooltip_text = str(row.get("Localidade", "Poço"))
                if status:
                    tooltip_text += f" • {status}"

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=10,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    popup=popup,
                    tooltip=tooltip_text,
                    weight=2
                ).add_to(fg_pocos)

                pts.append((lat, lon))

        fg_pocos.add_to(fmap)

        # Heatmap
        if "Vazão_LH" in fdf.columns and lat_col and lon_col:
            heat_df = fdf[[lat_col, lon_col, "Vazão_LH"]].copy()
            heat_df["lat"] = heat_df[lat_col].apply(to_float)
            heat_df["lon"] = heat_df[lon_col].apply(to_float)
            heat_df["val"] = pd.to_numeric(heat_df["Vazão_LH"], errors="coerce")

            heat_df = heat_df.dropna(subset=["lat", "lon", "val"])

            if not heat_df.empty:
                heat_points = heat_df[["lat", "lon", "val"]].values.tolist()
                fg_heat = folium.FeatureGroup(name="Mapa de Calor - Vazão", show=False)
                HeatMap(
                    heat_points,
                    radius=25,
                    blur=20,
                    max_zoom=12,
                    gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
                ).add_to(fg_heat)
                fg_heat.add_to(fmap)

        if pts:
            fmap.fit_bounds([
                [min(p[0] for p in pts), min(p[1] for p in pts)],
                [max(p[0] for p in pts), max(p[1] for p in pts)],
            ])

        # Legenda com opção de recolher
        legend_html = """
        {% macro html(this, kwargs) %}
        <div id="legend-pocos" style="
            position: fixed;
            bottom: 40px;
            left: 10px;
            z-index: 9999;
            background: rgba(255,255,255,0.95);
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 16px;
            font-size: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            backdrop-filter: blur(10px);
            font-family: 'Segoe UI', system-ui, sans-serif;
        ">
          <div id="legend-pocos-header" style="font-weight:700; margin-bottom:6px; color:#2d3436; font-size:13px; cursor:pointer;"
               onclick="
                 var body = document.getElementById('legend-pocos-body');
                 if (body.style.display === 'none') {
                     body.style.display = 'block';
                     this.innerHTML = 'Status dos Poços ▾';
                 } else {
                     body.style.display = 'none';
                     this.innerHTML = 'Status dos Poços ▸';
                 }
               ">
            Status dos Poços ▾
          </div>
          <div id="legend-pocos-body" style="margin-top:4px;">
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#00b894;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Instalado
            </div>
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#e17055;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Não instalado
            </div>
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#636e72;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Desativado
            </div>
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#d63031;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Obstruído
            </div>
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#6c5ce7;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Injetado
            </div>
            <div style="display:flex;align-items:center;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#0984e3;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Outros
            </div>
          </div>
        </div>
        {% endmacro %}
        """
        legend = MacroElement()
        legend._template = Template(legend_html)
        fmap.get_root().add_child(legend)

        # ⬇️ Botão de camadas recolhido (apenas ícone)
        LayerControl(collapsed=True).add_to(fmap)

        map_data = st_folium(fmap, height=500, use_container_width=True)

with col_fotos:
    st.markdown("#### 📸 Galeria de Fotos")
    
    with st.container():
        foto_col = "Link da Foto" if "Link da Foto" in fdf.columns else None

        fdf_gallery = fdf.copy()
        clicked = False

        if map_data and 'last_object_clicked' in map_data and lat_col and lon_col:
            click_info = map_data.get("last_object_clicked") or map_data.get("last_clicked")
            if click_info:
                clicked = True
                click_lat = click_info["lat"]
                click_lon = click_info["lng"]

                tmp = fdf.copy()
                tmp["_lat"] = tmp[lat_col].apply(to_float)
                tmp["_lon"] = tmp[lon_col].apply(to_float)
                tmp = tmp.dropna(subset=["_lat", "_lon"])

                if not tmp.empty:
                    tmp["dist2"] = (tmp["_lat"] - click_lat) ** 2 + (tmp["_lon"] - click_lon) ** 2
                    tmp = tmp.sort_values("dist2")
                    fdf_gallery = tmp.head(1)

        if not foto_col:
            st.info("📷 Coluna de fotos não encontrada na planilha.")
        else:
            items = []
            vistos = set()

            for _, row in fdf_gallery.iterrows():
                link = row.get(foto_col)
                if not isinstance(link, str) or not link.strip():
                    continue
                if link in vistos:
                    continue
                vistos.add(link)

                loc = row.get("Localidade", "")
                bairro = row.get("Bairro", "")
                caption_parts = [str(loc) if loc else None, str(bairro) if bairro else None]
                caption = " • ".join([p for p in caption_parts if p])

                fid = gdrive_extract_id(link)
                if fid:
                    thumb, big = drive_image_urls(fid)
                    items.append({"thumb": thumb, "src": big, "caption": caption})
                else:
                    items.append({"thumb": link, "src": link, "caption": caption})

            if clicked and items:
                st.success("📍 Visualizando fotos do poço selecionado no mapa")
                auto_open = True
            else:
                if not items:
                    st.info("🗺️ Clique em um poço no mapa para ver fotos específicas")
                else:
                    st.info("🗺️ Clique em um poço no mapa para focar as fotos em um ponto específico")
                auto_open = False

            render_lightgallery_images(items, height_px=460, auto_open=auto_open)

# =============================
# Gráficos Modernizados
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📊 Análise Estatística</div>', unsafe_allow_html=True)

def barra_contagem_moderna(colname, titulo, col_container):
    if colname not in fdf.columns:
        with col_container:
            st.info(f"📋 Dados de {titulo} não disponíveis")
        return

    color_schemes = {
        "Monitorado": ["#74b9ff", "#0984e3", "#6c5ce7"],
        "Instalado": ["#00b894", "#00cec9", "#55efc4"],
        "Status": ["#00b894", "#e17055", "#636e72", "#d63031", "#6c5ce7"]
    }
    colors = color_schemes.get(colname, ["#74b9ff", "#0984e3"])

    # Caso especial: Status x Ano_visita
    if colname == "Status" and "Ano_visita" in fdf.columns:
        tmp = (
            fdf[["Ano_visita", colname]]
            .dropna(subset=["Ano_visita", colname])
            .groupby(["Ano_visita", colname])
            .size()
            .reset_index(name="contagem")
        )
        if tmp.empty:
            with col_container:
                st.info(f"📊 Sem dados de {titulo} para os filtros atuais")
            return

        # Totais por ano para exibir no topo
        totais = (
            tmp.groupby("Ano_visita")["contagem"]
            .sum()
            .reset_index(name="total")
        )

        bars = (
            alt.Chart(tmp)
            .mark_bar(cornerRadius=6)
            .encode(
                x=alt.X("Ano_visita:O", title="Ano da visita"),
                y=alt.Y("contagem:Q", title="Quantidade de Poços"),
                color=alt.Color(
                    f"{colname}:N",
                    scale=alt.Scale(range=colors),
                    legend=alt.Legend(title=titulo)
                ),
                tooltip=[
                    alt.Tooltip("Ano_visita:O", title="Ano"),
                    alt.Tooltip(f"{colname}:N", title=titulo),
                    alt.Tooltip("contagem:Q", title="Poços")
                ]
            )
        )

        labels = (
            alt.Chart(totais)
            .mark_text(
                dy=-10,
                fontSize=14,
                fontWeight="bold",
                color="#2d3436"
            )
            .encode(
                x=alt.X("Ano_visita:O", title="Ano da visita"),
                y=alt.Y("total:Q"),
                text=alt.Text("total:Q", format="d")
            )
        )

        chart = (
            (bars + labels)
            .properties(height=300, title=f"Distribuição de {titulo} por ano da visita")
            .configure_title(fontSize=16, font="Segoe UI", anchor="middle")
            .configure_axis(labelFont="Segoe UI", titleFont="Segoe UI")
            .configure_legend(labelFont="Segoe UI", titleFont="Segoe UI")
        )
    else:
        tmp = (
            fdf[[colname]]
            .dropna()
            .groupby(colname)
            .size()
            .reset_index(name="contagem")
        )
        if tmp.empty:
            with col_container:
                st.info(f"📊 Sem dados de {titulo} para os filtros atuais")
            return

        chart = (
            alt.Chart(tmp)
            .mark_bar(cornerRadius=8)
            .encode(
                x=alt.X(f"{colname}:N", title="", sort="-y", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("contagem:Q", title="Quantidade de Poços"),
                color=alt.Color(
                    f"{colname}:N",
                    scale=alt.Scale(range=colors),
                    legend=alt.Legend(title=titulo)
                ),
                tooltip=[
                    alt.Tooltip(f"{colname}:N", title=titulo),
                    alt.Tooltip("contagem:Q", title="Poços")
                ]
            )
            .properties(height=300, title=f"Distribuição por {titulo}")
            .configure_title(fontSize=16, font="Segoe UI", anchor="middle")
            .configure_axis(labelFont="Segoe UI", titleFont="Segoe UI")
            .configure_legend(labelFont="Segoe UI", titleFont="Segoe UI")
        )

    with col_container:
        st.altair_chart(chart, use_container_width=True)

def grafico_caixas_por_ano(col_container):
    """Gráfico de Caixas de apoio por ano da visita."""
    if "Caixas_apoio" not in fdf.columns or "Ano_visita" not in fdf.columns:
        with col_container:
            st.info("📋 Dados de Caixas de apoio por ano não disponíveis")
        return

    tmp = (
        fdf[["Ano_visita", "Caixas_apoio"]]
        .dropna(subset=["Ano_visita", "Caixas_apoio"])
        .copy()
    )

    if tmp.empty:
        with col_container:
            st.info("📊 Sem dados de Caixas de apoio para os filtros atuais")
        return

    tmp["Caixas_apoio"] = pd.to_numeric(tmp["Caixas_apoio"], errors="coerce")
    tmp = tmp.dropna(subset=["Caixas_apoio"])

    if tmp.empty:
        with col_container:
            st.info("📊 Sem dados numéricos de Caixas de apoio para os filtros atuais")
        return

    agg = (
        tmp.groupby("Ano_visita")["Caixas_apoio"]
        .sum()
        .reset_index(name="total_caixas")
    )

    chart = (
        alt.Chart(agg)
        .mark_bar(cornerRadius=6)
        .encode(
            x=alt.X("Ano_visita:O", title="Ano da visita"),
            y=alt.Y("total_caixas:Q", title="Total de caixas de apoio"),
            tooltip=[
                alt.Tooltip("Ano_visita:O", title="Ano"),
                alt.Tooltip("total_caixas:Q", title="Caixas de apoio")
            ]
        )
        .properties(height=300, title="Caixas de apoio por ano da visita")
        .configure_title(fontSize=16, font="Segoe UI", anchor="middle")
        .configure_axis(labelFont="Segoe UI", titleFont="Segoe UI")
    )

    with col_container:
        st.altair_chart(chart, use_container_width=True)

# Layout dos gráficos:
# Linha 1: Status x Ano  | Caixas_apoio x Ano
# Linha 2: Monitorado    | Instalado
top1, top2 = st.columns(2)
barra_contagem_moderna("Status", "Status", top1)
grafico_caixas_por_ano(top2)

bottom1, bottom2 = st.columns(2)
barra_contagem_moderna("Monitorado", "Monitoramento", bottom1)
barra_contagem_moderna("Instalado", "Instalação", bottom2)



# =============================
# Tabela Modernizada
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📋 Relatório Detalhado</div>', unsafe_allow_html=True)

cols_tabela = [
    "Ano", "Município", "Localidade", "Bairro", "Profundidade_m",
    "Vazão_LH", "Vazão_estimada_LH", "Cloretos", "Monitorado",
    "Instalado", "Status", "Observações",
]

cols_existentes = [c for c in cols_tabela if c in fdf.columns]

tabela = fdf[cols_existentes].copy()

for col in ["Vazão_LH", "Vazão_estimada_LH", "Cloretos"]:
    if col in tabela.columns:
        tabela[col] = pd.to_numeric(tabela[col], errors="coerce")

def style_dataframe(df: pd.DataFrame):
    fmt = {}
    if "Vazão_LH" in df.columns:
        fmt["Vazão_LH"] = "{:,.0f} L/h"
    if "Vazão_estimada_LH" in df.columns:
        fmt["Vazão_estimada_LH"] = "{:,.0f} L/h"
    if "Cloretos" in df.columns:
        fmt["Cloretos"] = "{:.2f}"

    styler = df.style.format(fmt, na_rep="-")

    subset_cols = [c for c in ["Vazão_LH", "Vazão_estimada_LH"] if c in df.columns]
    if subset_cols:
        styler = styler.background_gradient(subset=subset_cols, cmap="Blues")

    return styler

st.dataframe(
    style_dataframe(tabela),
    use_container_width=True,
    height=450
)

# =============================
# Footer Modernizado
# =============================
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding: 2rem 1rem; color: #636e72;">
    <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">
        💧 <strong>Sistema de Monitoramento de Poços - Pedra Branca</strong>
    </div>
    <div style="font-size: 0.8rem; opacity: 0.8;">
        Desenvolvido para acompanhamento contínuo e tomada de decisão baseada em dados
    </div>
</div>
""", unsafe_allow_html=True)
