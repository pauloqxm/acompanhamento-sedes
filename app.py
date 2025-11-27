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
    page_title="Poços de Pedra Branca",
    layout="wide"
)

TZ = ZoneInfo("America/Fortaleza")

# =============================
# Estilos
# =============================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.app-header {
    background: linear-gradient(135deg, #0f4c75 0%, #3282b8 100%);
    padding: 1.8rem 2.2rem;
    border-radius: 0 0 22px 22px;
    margin: -1rem -1rem 1.5rem -1rem;
    color: white;
    box-shadow: 0 4px 18px rgba(0,0,0,0.18);
}
.app-header h1 {
    margin: 0;
    font-size: 2.1rem;
    font-weight: 700;
}
.app-header p {
    margin: 0.4rem 0 0 0;
    font-size: 1.05rem;
    opacity: 0.92;
}

.kpi-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 0.9rem 1rem;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
    border: 1px solid #e6ecf5;
}
.kpi-label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7f8c8d;
    margin-bottom: 0.15rem;
}
.kpi-value {
    font-size: 1.4rem;
    font-weight: 800;
    color: #2c3e50;
}
.kpi-sub {
    font-size: 0.85rem;
    color: #95a5a6;
}

.section-title {
    font-weight: 700;
    font-size: 1.1rem;
    margin: 0.3rem 0 0.3rem 0;
    color: #2c3e50;
}

[data-testid="stDataFrame"] table {
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# =============================
# Utilidades
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

def render_lightgallery_images(items: list, height_px=420):
    if not items:
        st.info("Nenhuma foto encontrada para os filtros atuais.")
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
        lightGallery(container, {{
          selector: '.gallery-item',
          zoom: true,
          thumbnail: true,
          download: false,
          loop: true,
          plugins: [lgZoom, lgThumbnail]
        }});
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
            <div style="display:flex;justify-content:space-between;padding:2px 0;font-size:0.9em;">
                <span style="font-weight:500;">{icon} {col}:</span>
                <span style="font-weight:600;text-align:right;">{safe(val)}</span>
            </div>
            """
        )

    corpo = "\n".join(linhas)
    html = f"""
    <div style="
        font-family: 'Segoe UI', Tahoma, sans-serif;
        padding: 10px 12px;
        min-width:240px;
        max-width:320px;
        background: linear-gradient(135deg,#1abc9c 0%,#3498db 100%);
        border-radius: 14px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.3);
        color: white;
        border: 2px solid rgba(255,255,255,0.3);
    ">
        <div style="
            background: rgba(0,0,0,0.18);
            padding: 6px 10px;
            border-radius: 10px;
            text-align:center;
            font-weight:700;
            font-size:1em;
            margin-bottom:6px;
        ">
            Poço monitorado
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
# Carrega dados da planilha
# =============================
SHEET_ID = "12mU_58X2Ezlr_tG7pcinh1kGMY1xgXXXKfyOlXj75rc"
GID = "1870024591"
SEP = ","

try:
    df = load_from_gsheet_csv(SHEET_ID, GID, sep=SEP)
except Exception:
    st.stop()

if df.empty:
    st.info("Planilha sem dados. Verifique permissões ou aba do Google Sheets.")
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

# Correção de textos
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
# Header
# =============================
st.markdown("""
<div class="app-header">
  <h1>💧 Poços de Pedra Branca</h1>
  <p>Monitoramento, instalação e situação dos poços perfurados no município.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    f"Última atualização do painel em {datetime.now(TZ).strftime('%d/%m/%Y %H:%M:%S')} "
    f"(fuso America/Fortaleza)."
)

# =============================
# Filtros
# =============================
st.markdown("### Filtros")

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    anos = sorted([a for a in df["Ano_visita"].dropna().unique().tolist()])
    ano_sel = st.multiselect(
        "Ano da visita",
        options=anos,
        default=anos if anos else None
    )

with col_f2:
    meses = [m for m in df["Mes_visita"].dropna().unique().tolist()]
    meses = sorted(meses, key=lambda x: ["Jan","Fev","Mar","Abr","Mai","Jun",
                                         "Jul","Ago","Set","Out","Nov","Dez"].index(x)) if meses else []
    mes_sel = st.multiselect(
        "Mês da visita",
        options=meses,
        default=meses if meses else None
    )

with col_f3:
    mun_opts = sorted([m for m in df["Município"].dropna().unique().tolist()]) if "Município" in df.columns else []
    mun_sel = st.multiselect(
        "Município",
        options=mun_opts,
        default=mun_opts if mun_opts else None
    )

with col_f4:
    bairro_opts = sorted([b for b in df["Bairro"].dropna().unique().tolist()]) if "Bairro" in df.columns else []
    bairro_sel = st.multiselect(
        "Bairro",
        options=bairro_opts,
        default=bairro_opts if bairro_opts else None
    )

col_f5, col_f6, col_f7 = st.columns(3)
with col_f5:
    mon_opts = sorted([m for m in df["Monitorado"].dropna().unique().tolist()]) if "Monitorado" in df.columns else []
    mon_sel = st.multiselect(
        "Monitorado",
        options=mon_opts,
        default=mon_opts if mon_opts else None
    )
with col_f6:
    inst_opts = sorted([m for m in df["Instalado"].dropna().unique().tolist()]) if "Instalado" in df.columns else []
    inst_sel = st.multiselect(
        "Instalado",
        options=inst_opts,
        default=inst_opts if inst_opts else None
    )
with col_f7:
    status_opts = sorted([s for s in df["Status"].dropna().unique().tolist()]) if "Status" in df.columns else []
    status_sel = st.multiselect(
        "Status",
        options=status_opts,
        default=status_opts if status_opts else None
    )

fdf = df.copy()

if anos and ano_sel:
    fdf = fdf[fdf["Ano_visita"].isin(ano_sel)]

if meses and mes_sel:
    fdf = fdf[fdf["Mes_visita"].isin(mes_sel)]

if mun_opts and mun_sel:
    fdf = fdf[fdf["Município"].isin(mun_sel)]

if bairro_opts and bairro_sel:
    fdf = fdf[fdf["Bairro"].isin(bairro_sel)]

if mon_opts and mon_sel:
    fdf = fdf[fdf["Monitorado"].isin(mon_sel)]

if inst_opts and inst_sel:
    fdf = fdf[fdf["Instalado"].isin(inst_sel)]

if status_opts and status_sel:
    fdf = fdf[fdf["Status"].isin(status_sel)]

st.markdown(
    f"Registros após filtros: **{len(fdf)}** poços."
)

# Colunas de coordenadas (compartilhadas entre mapa e galeria)
lat_col = "latitude" if "latitude" in fdf.columns else None
lon_col = "longitude" if "longitude" in fdf.columns else None

# =============================
# KPIs
# =============================
st.markdown("### Indicadores principais")

k1, k2, k3, k4 = st.columns(4)

total_pocos = len(fdf[fdf["Localidade"].notna()]) if "Localidade" in fdf.columns else len(fdf)
total_vazao = safe_sum(fdf["Vazão_LH"]) if "Vazão_LH" in fdf.columns else 0
total_vazao_est = safe_sum(fdf["Vazão_estimada_LH"]) if "Vazão_estimada_LH" in fdf.columns else 0
total_caixas = safe_sum(fdf["Caixas_apoio"]) if "Caixas_apoio" in fdf.columns else 0

with k1:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">Total de poços</div>
          <div class="kpi-value">{total_pocos}</div>
          <div class="kpi-sub">Linhas com informações válidas</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">Vazão medida</div>
          <div class="kpi-value">
            {total_vazao:,.0f} L/h
          </div>
          <div class="kpi-sub">Soma da coluna Vazão_LH</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">Vazão estimada</div>
          <div class="kpi-value">
            {total_vazao_est:,.0f} L/h
          </div>
          <div class="kpi-sub">Soma da coluna Vazão_estimada_LH</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">Caixas de apoio</div>
          <div class="kpi-value">{int(total_caixas) if not math.isnan(total_caixas) else 0}</div>
          <div class="kpi-sub">Soma da coluna Caixas_apoio</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =============================
# Layout mapa + fotos
# =============================
st.markdown("---")
col_map, col_fotos = st.columns([1.2, 1])

map_data = None

with col_map:
    st.markdown('<div class="section-title">🗺️ Mapa dos poços</div>', unsafe_allow_html=True)

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
        name="Esri World Imagery",
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
                "color": "#2ecc71",
                "weight": 1.5,
                "fillColor": "#2ecc71",
                "fillOpacity": 0.05,
            },
            tooltip=GeoJsonTooltip(
                fields=["NM_BAIRRO"],
                aliases=["Bairro"],
                sticky=False
            )
        ).add_to(fmap)
    except Exception as e:
        st.warning(f"Não foi possível carregar bairros_pb.geojson: {e}")

    fg_pocos = folium.FeatureGroup(name="Poços (por Status)", show=True)
    pts = []

    # Cores por Status (inclui Injetado)
    status_colors = {
        "Instalado": "#27ae60",       # verde
        "Não instalado": "#e67e22",   # laranja
        "Desativado": "#7f8c8d",      # cinza
        "Obstruído": "#c0392b",       # vermelho
        "Injetado": "#8e44ad",        # roxo
    }
    default_color = "#2980b9"        # azul padrão

    if lat_col and lon_col:
        for _, row in fdf.iterrows():
            lat = to_float(row.get(lat_col))
            lon = to_float(row.get(lon_col))
            if lat is None or lon is None:
                continue

            status = row.get("Status", "")
            color = status_colors.get(str(status), default_color)

            popup_html = make_popup_html(row)
            popup = folium.Popup(popup_html, max_width=320)

            tooltip_text = str(row.get("Localidade", "Poço"))
            if status:
                tooltip_text += f" • {status}"

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=popup,
                tooltip=tooltip_text,
            ).add_to(fg_pocos)

            pts.append((lat, lon))

    fg_pocos.add_to(fmap)

    # Heatmap da Vazão_LH
    if "Vazão_LH" in fdf.columns and lat_col and lon_col:
        heat_df = fdf[[lat_col, lon_col, "Vazão_LH"]].copy()
        heat_df["lat"] = heat_df[lat_col].apply(to_float)
        heat_df["lon"] = heat_df[lon_col].apply(to_float)
        heat_df["val"] = pd.to_numeric(heat_df["Vazão_LH"], errors="coerce")

        heat_df = heat_df.dropna(subset=["lat", "lon", "val"])

        if not heat_df.empty:
            heat_points = heat_df[["lat", "lon", "val"]].values.tolist()
            fg_heat = folium.FeatureGroup(name="Mapa de calor Vazão_LH", show=False)
            HeatMap(
                heat_points,
                radius=22,
                blur=18,
                max_zoom=12,
            ).add_to(fg_heat)
            fg_heat.add_to(fmap)

    if pts:
        fmap.fit_bounds([
            [min(p[0] for p in pts), min(p[1] for p in pts)],
            [max(p[0] for p in pts), max(p[1] for p in pts)],
        ])

    # Legenda visual de Status (inclui Injetado)
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed;
        bottom: 30px;
        left: 10px;
        z-index: 9999;
        background-color: white;
        padding: 8px 10px;
        border: 1px solid #ccc;
        border-radius: 6px;
        font-size: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    ">
      <div style="font-weight:600; margin-bottom:4px;">Status dos poços</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#27ae60;margin-right:4px;"></span>Instalado</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#e67e22;margin-right:4px;"></span>Não instalado</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#7f8c8d;margin-right:4px;"></span>Desativado</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#c0392b;margin-right:4px;"></span>Obstruído</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#8e44ad;margin-right:4px;"></span>Injetado</div>
      <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#2980b9;margin-right:4px;"></span>Outros / não informado</div>
    </div>
    {% endmacro %}
    """
    legend = MacroElement()
    legend._template = Template(legend_html)
    fmap.get_root().add_child(legend)

    LayerControl(collapsed=True).add_to(fmap)

    # CAPTURA DO CLICK NO MAPA (objeto ou mapa)
    map_data = st_folium(fmap, height=500, use_container_width=True)

# =============================
# Galeria de fotos (ligada ao clique do mapa)
# =============================
with col_fotos:
    st.markdown('<div class="section-title">📸 Fotos dos poços</div>', unsafe_allow_html=True)

    foto_col = "Link da Foto" if "Link da Foto" in fdf.columns else None

    # Por padrão, usa todos os poços filtrados
    fdf_gallery = fdf.copy()

    # Se o usuário clicou em um poço no mapa, tenta localizar o poço mais próximo
    if map_data and lat_col and lon_col:
        # Prioriza clique em objeto (marcador). Se não tiver, usa clique solto no mapa.
        click_info = map_data.get("last_object_clicked") or map_data.get("last_clicked")

        if click_info:
            click_lat = click_info["lat"]
            click_lon = click_info["lng"]

            tmp = fdf.copy()
            tmp["_lat"] = tmp[lat_col].apply(to_float)
            tmp["_lon"] = tmp[lon_col].apply(to_float)
            tmp = tmp.dropna(subset=["_lat", "_lon"])

            if not tmp.empty:
                tmp["dist2"] = (tmp["_lat"] - click_lat) ** 2 + (tmp["_lon"] - click_lon) ** 2
                tmp = tmp.sort_values("dist2")
                # pega apenas o poço mais próximo do clique
                fdf_gallery = tmp.head(1)

    if not foto_col:
        st.info("Coluna Link da Foto não encontrada na planilha.")
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

        if map_data and (map_data.get("last_object_clicked") or map_data.get("last_clicked")):
            st.caption("Exibindo fotos do poço selecionado no mapa.")
        else:
            st.caption("Clique em um poço no mapa para ver apenas as fotos daquele ponto.")

        render_lightgallery_images(items, height_px=460)

# =============================
# Gráficos de barra
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📊 Situação dos poços</div>', unsafe_allow_html=True)

g1, g2, g3 = st.columns(3)

def barra_contagem(colname, titulo, col_container):
    if colname not in fdf.columns:
        with col_container:
            st.info(f"Coluna {colname} não encontrada.")
        return
    tmp = (
        fdf[[colname]]
        .dropna()
        .groupby(colname)
        .size()
        .reset_index(name="contagem")
    )
    if tmp.empty:
        with col_container:
            st.info(f"Sem dados na coluna {colname} para os filtros atuais.")
        return

    chart = (
        alt.Chart(tmp)
        .mark_bar()
        .encode(
            x=alt.X(colname, title="", sort="-y"),
            y=alt.Y("contagem:Q", title="Quantidade"),
            tooltip=[alt.Tooltip(colname, title=titulo), alt.Tooltip("contagem:Q", title="Poços")]
        )
        .properties(height=260)
    )
    with col_container:
        st.altair_chart(chart, use_container_width=True)

barra_contagem("Monitorado", "Monitorado", g1)
barra_contagem("Instalado", "Instalado", g2)
barra_contagem("Status", "Status", g3)

# =============================
# Tabela detalhada
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📄 Tabela detalhada dos poços</div>', unsafe_allow_html=True)

cols_tabela = [
    "Ano",
    "Município",
    "Localidade",
    "Bairro",
    "Profundidade_m",
    "Vazão_LH",
    "Vazão_estimada_LH",
    "Cloretos",
    "Monitorado",
    "Instalado",
    "Status",
    "Observações",
]

cols_existentes = [c for c in cols_tabela if c in fdf.columns]

tabela = fdf[cols_existentes].copy()

for col in ["Vazão_LH", "Vazão_estimada_LH", "Cloretos"]:
    if col in tabela.columns:
        tabela[col] = pd.to_numeric(tabela[col], errors="coerce")

st.dataframe(
    tabela,
    use_container_width=True,
    height=420
)

st.markdown("""
<div style="text-align:center;color:#7f8c8d;font-size:0.85rem;margin-top:0.8rem;">
  Painel em construção permanente. Use os filtros para explorar cenários e apoiar decisões sobre os poços de Pedra Branca.
</div>
""", unsafe_allow_html=True)
