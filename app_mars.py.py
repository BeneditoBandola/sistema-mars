import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, date, timedelta
import unicodedata
import re
import math
import streamlit.components.v1 as components

# --- IMPORT DAS BIBLIOTECAS DE MAPA PROFISSIONAL ---
try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    st.error("Bibliotecas de mapa não encontradas. Abra o cmd e digite: pip install folium streamlit-folium")
    st.stop()

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Roteiro e Visitas Minassal", 
    layout="wide", 
    page_icon="🐾",
    initial_sidebar_state="expanded"
)

# --- INICIALIZAÇÃO DO ESTADO PARA CLIENTES PULADOS NO ROTEIRO ---
if "ocultos_roteiro" not in st.session_state:
    st.session_state.ocultos_roteiro = []

# --- SISTEMA DE SKINS / TEMAS DINÂMICOS ---
st.sidebar.markdown("### 🎨 Personalização")
tema_escolhido = st.sidebar.selectbox(
    "Escolha a Skin do Sistema:", 
    ["Roxo Premium (Pessoal)", "Minassal (Corporativo)", "Claro Minimalista", "Modo Escuro (Dark)"]
)

css_skin = ""

if tema_escolhido == "Roxo Premium (Pessoal)":
    css_skin = """
    <style>
        .stApp { background-color: #F6F4FA; }
        [data-testid="stSidebar"] { border-right: 3px solid #805AD5; background-color: #FFFFFF; }
        h1, h2, h3 { color: #44337A !important; }
        div.stButton > button:first-child { background-color: #6B46C1; color: white; border-radius: 8px; border: none; font-weight: 600; }
        div.stButton > button:first-child:hover { background-color: #805AD5; color: white; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(107, 70, 193, 0.3); }
        [data-testid="stMetric"] { background-color: white; padding: 15px; border-radius: 10px; border-left: 6px solid #805AD5; box-shadow: 0 4px 6px rgba(0,0,0,0.04); }
        [data-testid="stMetricValue"] { color: #44337A; font-weight: 800; }
        .streamlit-expanderHeader { background-color: white; border-radius: 8px; border: 1px solid #E9E3F4; color: #44337A; font-weight: 600; }
        .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px 8px 0px 0px; border: 1px solid #E9E3F4; border-bottom: none; color: #6B46C1; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #6B46C1 !important; color: white !important; border-bottom: 2px solid #44337A !important; }
    </style>
    """
elif tema_escolhido == "Minassal (Corporativo)":
    css_skin = """
    <style>
        .stApp { background-color: #F4F7F9; }
        [data-testid="stSidebar"] { border-right: 3px solid #007BBA; background-color: #FFFFFF; }
        h1, h2, h3 { color: #1A365D !important; }
        div.stButton > button:first-child { background-color: #1A365D; color: white; border-radius: 8px; font-weight: 600; border: none; }
        div.stButton > button:first-child:hover { background-color: #007BBA; color: white; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        [data-testid="stMetric"] { background-color: white; padding: 15px; border-radius: 10px; border-left: 6px solid #007BBA; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        [data-testid="stMetricValue"] { color: #1A365D; font-weight: 800; }
        .streamlit-expanderHeader { background-color: white; border-radius: 8px; border: 1px solid #E2E8F0; color: #1A365D; font-weight: 600; }
        .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px 8px 0px 0px; border: 1px solid #E2E8F0; color: #64748B; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #1A365D !important; color: white !important; border-bottom: 2px solid #007BBA !important; }
    </style>
    """
elif tema_escolhido == "Claro Minimalista":
    css_skin = """
    <style>
        .stApp { background-color: #FFFFFF; }
        [data-testid="stSidebar"] { border-right: 1px solid #E5E7EB; background-color: #F9FAFB; }
        h1, h2, h3 { color: #111827 !important; }
        div.stButton > button:first-child { background-color: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; font-weight: 500; }
        div.stButton > button:first-child:hover { background-color: #E5E7EB; color: #111827; }
        [data-testid="stMetric"] { background-color: #F9FAFB; padding: 15px; border-radius: 8px; border: 1px solid #E5E7EB; }
        [data-testid="stMetricValue"] { color: #111827; font-weight: 700; }
        .streamlit-expanderHeader { background-color: #F9FAFB; border-radius: 6px; border: 1px solid #E5E7EB; color: #374151; font-weight: 500; }
        .stTabs [data-baseweb="tab"] { background-color: #F9FAFB; border: 1px solid #E5E7EB; border-bottom: none; color: #6B7280; }
        .stTabs [aria-selected="true"] { background-color: #FFFFFF !important; color: #111827 !important; border-top: 2px solid #111827 !important; }
    </style>
    """
elif tema_escolhido == "Modo Escuro (Dark)":
    css_skin = """
    <style>
        .stApp { background-color: #121212; color: #E0E0E0; }
        [data-testid="stSidebar"] { border-right: 1px solid #333333; background-color: #1E1E1E; }
        h1, h2, h3, p, span { color: #FFFFFF !important; }
        div.stButton > button:first-child { background-color: #333333; color: #FFFFFF; border: 1px solid #444444; border-radius: 8px; }
        div.stButton > button:first-child:hover { background-color: #444444; border-color: #555555; }
        [data-testid="stMetric"] { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 6px solid #4CAF50; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        [data-testid="stMetricValue"] { color: #4CAF50 !important; font-weight: 800; }
        .streamlit-expanderHeader { background-color: #1E1E1E; border: 1px solid #333333; color: #FFFFFF; }
        .stTabs [data-baseweb="tab"] { background-color: #1E1E1E; border: 1px solid #333333; border-bottom: none; color: #AAAAAA; }
        .stTabs [aria-selected="true"] { background-color: #333333 !important; color: #FFFFFF !important; border-bottom: 2px solid #4CAF50 !important; }
    </style>
    """

st.markdown(css_skin, unsafe_allow_html=True)
# -------------------------------------------------------------

# --- IMPORT DO PDF ---
try:
    from fpdf import FPDF
except ImportError:
    st.error("Biblioteca FPDF não encontrada. Abra o terminal e digite: pip install fpdf")
    st.stop()

# --- CALENDÁRIO OFICIAL MARS 2026 (CICLOS DE 28 DIAS) ---
PERIODOS_MARS_2026 = [
    ("P1", datetime(2025, 12, 28), datetime(2026, 1, 24, 23, 59, 59)),
    ("P2", datetime(2026, 1, 25), datetime(2026, 2, 21, 23, 59, 59)),
    ("P3", datetime(2026, 2, 22), datetime(2026, 3, 21, 23, 59, 59)),
    ("P4", datetime(2026, 3, 22), datetime(2026, 4, 18, 23, 59, 59)),
    ("P5", datetime(2026, 4, 19), datetime(2026, 5, 16, 23, 59, 59)),
    ("P6", datetime(2026, 5, 17), datetime(2026, 6, 13, 23, 59, 59)),
    ("P7", datetime(2026, 6, 14), datetime(2026, 7, 11, 23, 59, 59)),
    ("P8", datetime(2026, 7, 12), datetime(2026, 8, 8, 23, 59, 59)),
    ("P9", datetime(2026, 8, 9), datetime(2026, 9, 5, 23, 59, 59)),
    ("P10", datetime(2026, 9, 6), datetime(2026, 10, 3, 23, 59, 59)),
    ("P11", datetime(2026, 10, 4), datetime(2026, 10, 31, 23, 59, 59)),
    ("P12", datetime(2026, 11, 1), datetime(2026, 11, 28, 23, 59, 59)),
    ("P13", datetime(2026, 11, 29), datetime(2026, 12, 26, 23, 59, 59))
]

def obter_periodo_atual():
    hoje = datetime.now()
    for nome, inicio, fim in PERIODOS_MARS_2026:
        if inicio <= hoje <= fim:
            return nome, inicio, fim
    return "DESCONHECIDO", datetime.min, datetime.max

# --- LISTA OFICIAL DE SMALL BAGS ---
SMALL_BAGS_CODES = [
    '98985', '98980', '98679', '98989', '98982', '98933', '98934', '98914', 
    '98915', '98911', '98912', '98930', '98931', '98899', '98898', '98941', 
    '98937', '98936', '98944', '98942', '98903', '98902', '98946'
]

CONFIG_ROTEIRO = "config_roteiro.json"
REGISTRO_VISITAS = "visitas_realizadas.json"
ARQ_GRUPOS = "config_grupos.json"
ARQ_STATUS = "status_clientes.json" 
ARQ_FREQUENCIA = "frequencia_clientes.json" # NOVO ARQUIVO DA AGENDA
PASTA_SISTEMA = os.path.dirname(os.path.abspath(__file__))

def extrair_link_iframe(texto):
    if not texto: return ""
    match = re.search(r'src="([^"]+)"', texto)
    return match.group(1) if match else texto.strip()

# --- 2. FUNÇÕES DE PERSISTÊNCIA E LIMPEZA COM GERAÇÃO AUTOMÁTICA DE JSON ---
def carregar_config():
    caminho = os.path.join(PASTA_SISTEMA, CONFIG_ROTEIRO)
    padrao = {"promotores": {}, "mapas_cidades": {}, "casas": {}}
    
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)
        return padrao

    try:
        with open(caminho, 'r', encoding='utf-8') as f: 
            config = json.load(f)
            if "mapas_cidades" not in config: config["mapas_cidades"] = {}
            if "casas" not in config: config["casas"] = {}
            return config
    except: 
        return padrao

def salvar_config(config):
    caminho = os.path.join(PASTA_SISTEMA, CONFIG_ROTEIRO)
    with open(caminho, 'w', encoding='utf-8') as f: 
        json.dump(config, f, indent=4, ensure_ascii=False)

def carregar_visitas():
    caminho = os.path.join(PASTA_SISTEMA, REGISTRO_VISITAS)
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def carregar_grupos():
    caminho = os.path.join(PASTA_SISTEMA, ARQ_GRUPOS)
    padrao = {"SMALL BAGS (Padrão)": {"codigos": SMALL_BAGS_CODES}}
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)
        return padrao
    try:
        with open(caminho, 'r', encoding='utf-8') as f: 
            grupos = json.load(f)
            if not isinstance(grupos, dict): grupos = {}
            if not any("SMALL BAGS" in k.upper() for k in grupos.keys()):
                grupos["SMALL BAGS (Padrão)"] = {"codigos": SMALL_BAGS_CODES}
            return grupos
    except: return padrao

def carregar_status():
    caminho = os.path.join(PASTA_SISTEMA, ARQ_STATUS)
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def registrar_status(cod_cliente, status):
    stats = carregar_status()
    stats[str(cod_cliente)] = status
    caminho = os.path.join(PASTA_SISTEMA, ARQ_STATUS)
    with open(caminho, 'w', encoding='utf-8') as f: json.dump(stats, f, indent=4, ensure_ascii=False)

def remover_status(cod_cliente):
    stats = carregar_status()
    cod_str = str(cod_cliente)
    if cod_str in stats:
        del stats[cod_str]
        caminho = os.path.join(PASTA_SISTEMA, ARQ_STATUS)
        with open(caminho, 'w', encoding='utf-8') as f: json.dump(stats, f, indent=4, ensure_ascii=False)

# --- FUNÇÕES DE FREQUÊNCIA FIXA ---
def carregar_frequencia():
    caminho = os.path.join(PASTA_SISTEMA, ARQ_FREQUENCIA)
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f: json.dump({}, f)
        return {}
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def salvar_frequencia(dados):
    caminho = os.path.join(PASTA_SISTEMA, ARQ_FREQUENCIA)
    with open(caminho, 'w', encoding='utf-8') as f: json.dump(dados, f, indent=4, ensure_ascii=False)

# --- LÓGICA DE MÚLTIPLAS VISITAS ---
def registrar_visita(cod_cliente):
    visitas = carregar_visitas()
    cod_str = str(cod_cliente)
    if cod_str not in visitas:
        visitas[cod_str] = []
    elif isinstance(visitas[cod_str], str):
        visitas[cod_str] = [visitas[cod_str]]
    visitas[cod_str].append(datetime.now().strftime("%d/%m/%Y %H:%M"))
    caminho = os.path.join(PASTA_SISTEMA, REGISTRO_VISITAS)
    with open(caminho, 'w', encoding='utf-8') as f: json.dump(visitas, f, indent=4, ensure_ascii=False)

def remover_visita(cod_cliente):
    visitas = carregar_visitas()
    cod_str = str(cod_cliente)
    if cod_str in visitas:
        if isinstance(visitas[cod_str], list) and len(visitas[cod_str]) > 0:
            visitas[cod_str].pop()
            if len(visitas[cod_str]) == 0:
                del visitas[cod_str]
        else:
            del visitas[cod_str]
        caminho = os.path.join(PASTA_SISTEMA, REGISTRO_VISITAS)
        with open(caminho, 'w', encoding='utf-8') as f: 
            json.dump(visitas, f, indent=4, ensure_ascii=False)

def get_qtd_visitas_periodo(cod_cliente, visitas_dict, dt_inicio, dt_fim):
    v = visitas_dict.get(str(cod_cliente))
    if not v: return 0
    if isinstance(v, str): v = [v]
    validas = 0
    for d_str in v:
        try:
            dt_obj = datetime.strptime(d_str, "%d/%m/%Y %H:%M")
            if dt_inicio <= dt_obj <= dt_fim:
                validas += 1
        except: pass
    return validas

def limpar_texto(texto):
    if pd.isna(texto): return ""
    return unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    break_point = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * break_point

# --- GERADORES DE PDF ---
def gerar_pdf_cliente_local(nome_cli, cod_cli, df_compras, periodos, c_fam, col_prod, pasta, todos_periodos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Historico de Compras (QTD Faturada)", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    n_limpo = unicodedata.normalize('NFKD', str(nome_cli)).encode('ASCII', 'ignore').decode('utf-8')
    pdf.cell(0, 8, f"CLIENTE: {cod_cli} - {n_limpo}", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(90, 8, "PRODUTO", border=1, fill=True)
    pdf.cell(40, 8, "FAMILIA", border=1, fill=True)
    w_p = 60 / len(periodos) if periodos else 20
    for p in periodos:
        p_name = p.replace('QTD', '').replace('P2026-', 'P-').strip()
        pdf.cell(w_p, 8, p_name, border=1, align='C', fill=True)
    pdf.ln()
    small_bags_encontrados = []
    for _, row in df_compras.iterrows():
        produto = unicodedata.normalize('NFKD', str(row['PRODUTO NOME'])).encode('ASCII', 'ignore').decode('utf-8')[:48]
        familia = unicodedata.normalize('NFKD', str(row.get(c_fam, ''))).encode('ASCII', 'ignore').decode('utf-8')[:20]
        cod_p = str(row.get(col_prod, '')).strip().replace('.0', '')
        is_small_bag = cod_p in SMALL_BAGS_CODES
        if is_small_bag:
            pdf.set_text_color(0, 102, 204) 
            pdf.set_font("Arial", 'B', 7)
            meses_comprados = []
            for p in todos_periodos:
                val = row.get(p, 0)
                if val > 0:
                    val_str = f"{int(val)}" if val == int(val) else f"{val:.2f}".replace('.', ',')
                    meses_comprados.append(f"Período {p.replace('QTD', '').replace('P2026-', '').strip()} (Qtd: {val_str})")
            if meses_comprados: small_bags_encontrados.append(f"- {produto} | Adquirido em: {', '.join(meses_comprados)}")
        else:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 7)
        pdf.cell(90, 8, produto, border=1)
        pdf.cell(40, 8, familia, border=1)
        for p in periodos:
            val = row.get(p, 0)
            if pd.isna(val): val = 0
            val_str = f"{int(val)}" if val == int(val) else f"{val:.2f}".replace('.', ',')
            pdf.cell(w_p, 8, val_str, border=1, align='C')
        pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    if small_bags_encontrados:
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(220, 38, 38)
        pdf.cell(0, 8, "OPORTUNIDADES DE LEITURA ENCONTRADAS (SMALL BAGS):", ln=True)
        pdf.set_font("Arial", '', 8)
        pdf.set_text_color(0, 0, 0)
        for sb in small_bags_encontrados: pdf.cell(0, 6, sb, ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(255, 230, 230)
    qtd_oportunidades = len(small_bags_encontrados)
    pdf.cell(0, 8, f"QUANTIDADE DE OPORTUNIDADES NESTE CLIENTE: {qtd_oportunidades}", ln=True, fill=True)
    
    # Retorna o PDF em bytes para o download em ambiente de nuvem
    return pdf.output(dest='S').encode('latin1')

def gerar_pdf_leituras(promotor, cidades_alvo, df_rot, df_vendas, periodos, c_fam, col_v, col_cli_nome, col_prod, pasta, todos_periodos, grupos_selecionados, grupos_cadastrados):
    cods_validos = []
    if grupos_selecionados:
        for g in grupos_selecionados:
            raw_cods = grupos_cadastrados.get(g, {}).get("codigos", [])
            if isinstance(raw_cods, str):
                cods_validos.extend([c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', raw_cods) if c.strip()])
            elif isinstance(raw_cods, list):
                for item in raw_cods:
                    cods_validos.extend([c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', str(item)) if c.strip()])
    cods_validos = list(set(cods_validos))
    
    if not cods_validos: return None

    pdf = FPDF()
    total_oportunidades_geral = 0
    col_cidade = next((c for c in df_rot.columns if 'CIDADE' in c), None)
    if not col_cidade: return None
    df_rot_prom = df_rot[df_rot[col_cidade].isin(cidades_alvo)]
    if df_rot_prom.empty: return None
    
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "ROTEIRO DE LEITURAS - GRUPOS SELECIONADOS", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Promotor: {unicodedata.normalize('NFKD', str(promotor)).encode('ASCII', 'ignore').decode('utf-8')}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    for cidade in sorted(df_rot_prom[col_cidade].unique()):
        df_cid = df_rot_prom[df_rot_prom[col_cidade] == cidade]
        clientes_com_oportunidade = []
        oportunidades_cidade = 0
        
        for cod_c in df_cid[col_v].unique():
            cli_info = df_cid[df_cid[col_v] == cod_c].iloc[0]
            nome_cli = str(cli_info.get(col_cli_nome, 'N/A'))
            endereco = str(cli_info.get(next((c for c in df_rot_prom.columns if 'ENDERE' in c), 'N/A'), 'N/A'))
            bairro = str(cli_info.get(next((c for c in df_rot_prom.columns if 'BAIRRO' in c), 'N/A'), 'N/A'))
            df_det = df_vendas[df_vendas[col_v] == cod_c]
            if df_det.empty: continue
            
            df_sb = df_det[df_det[col_prod].astype(str).str.replace('.0', '', regex=False).str.strip().isin(cods_validos)]
            if df_sb.empty: continue
            
            df_sb_grouped = df_sb.groupby([col_prod, 'PRODUTO NOME'])[todos_periodos].sum().reset_index()
            v_recentes = df_sb_grouped[df_sb_grouped[todos_periodos].sum(axis=1) > 0]
            
            if not v_recentes.empty:
                compras_formatadas = []
                grupos_encontrados = {}
                
                for _, row in v_recentes.iterrows():
                    p_nome = unicodedata.normalize('NFKD', str(row['PRODUTO NOME'])).encode('ASCII', 'ignore').decode('utf-8')[:45]
                    cod_p = str(row.get(col_prod, '')).strip().replace('.0', '')
                    meses = []
                    
                    for p in todos_periodos:
                        val = row.get(p, 0)
                        if val > 0:
                            val_str = f"{int(val)}" if val == int(val) else f"{val:.2f}".replace('.', ',')
                            per_nome = p.replace('QTD', '').replace('P2026-', '').strip()
                            meses.append(f"Período {per_nome} (Qtd: {val_str})")
                            
                            for g_nome in grupos_selecionados:
                                raw_g = grupos_cadastrados.get(g_nome, {}).get("codigos", [])
                                if isinstance(raw_g, str):
                                    g_cods = [c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', raw_g) if c.strip()]
                                else:
                                    g_cods = []
                                    for item in raw_g:
                                        g_cods.extend([c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', str(item)) if c.strip()])
                                        
                                if cod_p in g_cods:
                                    if g_nome not in grupos_encontrados:
                                        grupos_encontrados[g_nome] = set()
                                    grupos_encontrados[g_nome].add(per_nome)
                                    
                    if meses:
                        compras_formatadas.append({'str': f"  - {p_nome} | {', '.join(meses)}"})
                        
                qtd_ops = len(compras_formatadas)
                oportunidades_cidade += qtd_ops
                clientes_com_oportunidade.append({
                    'cod': cod_c, 
                    'nome': nome_cli, 
                    'end': f"{endereco} - {bairro}", 
                    'compras': compras_formatadas, 
                    'qtd_ops': qtd_ops,
                    'grupos_encontrados': grupos_encontrados
                })
                
        if clientes_com_oportunidade:
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255) 
            pdf.cell(0, 10, f"CIDADE: {cidade} (Lojas: {len(clientes_com_oportunidade)} | Oportunidades Locais: {oportunidades_cidade})", border=1, ln=True, fill=True)
            pdf.ln(3)
            total_oportunidades_geral += oportunidades_cidade
            
            for cli in clientes_com_oportunidade:
                pdf.set_font("Arial", 'B', 10)
                n_limpo = unicodedata.normalize('NFKD', str(cli['nome'])).encode('ASCII', 'ignore').decode('utf-8')
                pdf.cell(0, 6, f"Cliente: {cli['cod']} - {n_limpo}", ln=True)
                pdf.set_font("Arial", 'I', 9)
                end_limpo = unicodedata.normalize('NFKD', cli['end']).encode('ASCII', 'ignore').decode('utf-8')
                pdf.cell(0, 5, f"Endereço: {end_limpo}", ln=True)
                
                pdf.set_text_color(220, 38, 38)
                pdf.set_font("Arial", 'B', 9)
                for g_nome, periodos_set in cli['grupos_encontrados'].items():
                    per_str = ", ".join(sorted(list(periodos_set)))
                    msg = f"CLIENTE COMPROU {g_nome.upper()} EM ({per_str})"
                    msg_limpa = unicodedata.normalize('NFKD', msg).encode('ASCII', 'ignore').decode('utf-8')
                    pdf.cell(0, 6, msg_limpa, ln=True)
                
                for comp in cli['compras']:
                    pdf.cell(0, 5, comp['str'], ln=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 6, f"Oportunidades neste cliente: {cli['qtd_ops']}", ln=True)
                pdf.ln(3)
                
    if total_oportunidades_geral == 0: return None
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(255, 200, 200)
    pdf.cell(0, 12, f"TOTAL GERAL DE OPORTUNIDADES DO RELATORIO: {total_oportunidades_geral}", border=1, ln=True, align='C', fill=True)
    
    return pdf.output(dest='S').encode('latin1')

def gerar_pdf_relatorio_visitas(promotor, data_inicio, data_fim, df_v, df_e, col_v, col_e, col_nome, col_cid, promotores_dict, pasta):
    visitas = carregar_visitas()
    cidades_alvo = promotores_dict.get(promotor, [])
    registros = []
    
    dt_inicio = datetime.combine(data_inicio, datetime.min.time())
    dt_fim = datetime.combine(data_fim, datetime.max.time())
    
    for cod_c, datas in visitas.items():
        if isinstance(datas, str): datas = [datas]
        
        datas_validas = []
        for d_str in datas:
            try:
                dt_obj = datetime.strptime(d_str, "%d/%m/%Y %H:%M")
                if dt_inicio <= dt_obj <= dt_fim:
                    datas_validas.append((dt_obj, d_str))
            except: pass
        
        if not datas_validas: continue
        
        cidade_cli = "N/A"
        cli_end = df_e[df_e[col_e] == cod_c]
        if not cli_end.empty and col_cid and col_cid in cli_end.columns:
            cidade_cli = str(cli_end.iloc[0][col_cid]).upper()
            
        if cidades_alvo and cidade_cli not in cidades_alvo:
            continue
            
        nome_cli = "NÃO INFORMADO"
        cli_ven = df_v[df_v[col_v] == cod_c]
        if not cli_ven.empty and col_nome in cli_ven.columns:
            nome_cli = str(cli_ven.iloc[0][col_nome])
            
        for dt_obj, d_str in datas_validas:
            data_formatada = dt_obj.strftime("%d/%m/%Y")
            registros.append({
                'dt': dt_obj, 'str': data_formatada, 'cod': cod_c, 
                'nome': nome_cli, 'cid': cidade_cli
            })
            
    if not registros: return None
    
    registros.sort(key=lambda x: x['dt'])
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO DE VISITAS CONCLUIDAS", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    p_limpo = unicodedata.normalize('NFKD', str(promotor)).encode('ASCII', 'ignore').decode('utf-8')
    pdf.cell(0, 8, f"Promotor: {p_limpo}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(30, 8, "DATA", border=1, fill=True, align='C')
    pdf.cell(20, 8, "CODIGO", border=1, fill=True, align='C')
    pdf.cell(100, 8, "CLIENTE", border=1, fill=True)
    pdf.cell(40, 8, "CIDADE", border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    for r in registros:
        n_limpo = unicodedata.normalize('NFKD', r['nome']).encode('ASCII', 'ignore').decode('utf-8')[:55]
        c_limpo = unicodedata.normalize('NFKD', r['cid']).encode('ASCII', 'ignore').decode('utf-8')[:22]
        
        pdf.cell(30, 6, r['str'], border=1, align='C')
        pdf.cell(20, 6, r['cod'], border=1, align='C')
        pdf.cell(100, 6, n_limpo, border=1)
        pdf.cell(40, 6, c_limpo, border=1)
        pdf.ln()
        
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 255, 200)
    pdf.cell(0, 10, f" TOTAL DE VISITAS NO PERIODO: {len(registros)}", border=1, ln=True, fill=True)
    
    return pdf.output(dest='S').encode('latin1')

# --- 3. PROCESSAMENTO OTIMIZADO ---
@st.cache_data
def processar_bases(arq_vendas_content, arq_clientes_content, nome_v, nome_c):
    def ler_limpar(arq, nome):
        if nome.endswith('.csv'):
            try:
                df = pd.read_csv(arq, sep=';', encoding='latin1', on_bad_lines='skip')
                if len(df.columns) <= 1:
                    arq.seek(0)
                    df = pd.read_csv(arq, sep=',', encoding='latin1', on_bad_lines='skip')
            except:
                arq.seek(0)
                df = pd.read_csv(arq, sep=',', encoding='latin1', on_bad_lines='skip')
        else: df = pd.read_excel(arq)
        df.columns = df.columns.str.strip().str.upper()
        for col in df.columns:
            if any(k in col for k in ['CIDADE', 'CLIENTE', 'BAIRRO', 'ENDERE', 'FAMILIA']):
                df[col] = df[col].astype(str).str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.upper().str.strip()
        return df
    df_v = ler_limpar(arq_vendas_content, nome_v)
    df_e = ler_limpar(arq_clientes_content, nome_c)
    def achar_col(df, termos):
        for col in df.columns:
            if any(t in col for t in termos): return col
        return None
    c_v = achar_col(df_v, ['CLIENTE CODIGO', 'CLIENTE CÓDIGO', 'COD_CLI'])
    c_e = achar_col(df_e, ['CÓDIGO', 'CODIGO', 'ID_CLIENTE'])
    c_d = achar_col(df_e, ['DOCUMENTO', 'CNPJ', 'CPF'])
    c_forn = achar_col(df_v, ['FABRICANTE CODIGO', 'FABRICANTE CÓDIGO', 'FORNECEDOR CODIGO'])
    c_prod = achar_col(df_v, ['PRODUTO CODIGO', 'PRODUTO CÓDIGO', 'CODIGO PRODUTO', 'SKU'])
    if not c_prod:
        df_v['PROD_CODIGO_TEMP'] = 'N/A'
        c_prod = 'PROD_CODIGO_TEMP'
    c_fam = next((c for c in df_v.columns if any(k in c for k in ['FAMILIA NOME', 'FAMÍLIA NOME', 'CATEGORIA NOME', 'MARCA NOME'])), None)
    if not c_fam: c_fam = next((c for c in df_v.columns if any(k in c for k in ['FAMILIA', 'CATEGORIA', 'LINHA', 'MARCA']) and 'COD' not in c), None)
    if not c_fam: c_fam = achar_col(df_v, ['FAMILIA', 'FAMÍLIA', 'CATEGORIA', 'LINHA', 'GRUPO', 'MARCA', 'SEGMENTO'])
    if not c_fam:
        df_v['FAMILIA_PRODUTO'] = 'GERAL'
        c_fam = 'FAMILIA_PRODUTO'
    cols_vlr = [c for c in df_v.columns if 'VALOR' in c]
    for col in cols_vlr:
        if df_v[col].dtype == 'object':
            df_v[col] = df_v[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0)
    cols_qtd = [c for c in df_v.columns if 'QTD' in c]
    for col in cols_qtd:
        if df_v[col].dtype == 'object':
            df_v[col] = df_v[col].astype(str).str.replace(',', '.', regex=False)
            df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0)
    return df_v, df_e, c_v, c_e, c_d, c_forn, cols_vlr, c_fam, c_prod

# --- OBTEM O PERIODO ATUAL DO SISTEMA E EXIBE ---
periodo_atual, dt_inicio_p, dt_fim_p = obter_periodo_atual()
st.sidebar.markdown(f"<div style='background-color: #d1fae5; color: #065f46; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; border: 1px solid #34d399;'>📅 PERÍODO ATUAL: {periodo_atual}<br><span style='font-size: 12px; font-weight: normal;'>{dt_inicio_p.strftime('%d/%m')} até {dt_fim_p.strftime('%d/%m/%y')}</span></div>", unsafe_allow_html=True)

# --- 4. INTERFACE LATERAL ---
with st.sidebar:
    st.divider()
    config = carregar_config()
    
    with st.expander("👤 Gerenciar Promotores"):
        edit_lista = ["-- NOVO PROMOTOR --"] + list(config["promotores"].keys())
        selecionado = st.selectbox("Editar ou Novo:", edit_lista)
        default_nome = "" if selecionado == "-- NOVO PROMOTOR --" else selecionado
        default_cidades = "" if selecionado == "-- NOVO PROMOTOR --" else ", ".join(config["promotores"][selecionado])
        n_p = st.text_input("Nome do Promotor", value=default_nome)
        c_p = st.text_area("Cidades (separadas por vírgula)", value=default_cidades)
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Salvar Promotor"):
                if n_p and c_p:
                    if selecionado != "-- NOVO PROMOTOR --" and selecionado != n_p: del config["promotores"][selecionado]
                    config["promotores"][n_p] = [limpar_texto(c) for c in c_p.split(",")]
                    salvar_config(config); st.success("Salvo!"); time.sleep(1); st.rerun()
        with col_b2:
            if selecionado != "-- NOVO PROMOTOR --":
                if st.button("🗑️ Excluir Promotor", type="primary"):
                    del config["promotores"][selecionado]
                    salvar_config(config); st.warning("Removido!"); time.sleep(1); st.rerun()

    with st.expander("🏠 Cadastrar Casa do Promotor"):
        lista_p_casa = list(config["promotores"].keys())
        if lista_p_casa:
            p_casa_sel = st.selectbox("Promotor (Casa):", lista_p_casa)
            casa_info = config.get("casas", {}).get(p_casa_sel, {"end": "", "lat": "", "lon": ""})
            
            n_end = st.text_input("Endereço da Casa:", value=casa_info.get("end", ""))
            c_lat = st.text_input("Latitude (ex: -21.123):", value=str(casa_info.get("lat", "")))
            c_lon = st.text_input("Longitude (ex: -48.123):", value=str(casa_info.get("lon", "")))
            
            if st.button("💾 Salvar Casa"):
                if "casas" not in config: config["casas"] = {}
                config["casas"][p_casa_sel] = {"end": n_end, "lat": c_lat, "lon": c_lon}
                salvar_config(config)
                st.success(f"Casa salva!")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Cadastre os promotores primeiro.")

    with st.expander("📅 Frequência Fixa (Agenda)"):
        lista_p_freq = list(config["promotores"].keys())
        if lista_p_freq:
            p_freq_sel = st.selectbox("👤 Selecione o Promotor:", lista_p_freq, key="freq_prom_sel")
            cod_cli_freq = st.text_input("🔑 Código do Cliente:")
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            
            freq_db = carregar_frequencia()
            dias_atuais = freq_db.get(p_freq_sel, {}).get(cod_cli_freq.strip(), []) if cod_cli_freq else []
            
            dias_selecionados = st.multiselect("📆 Dias da semana para visitar:", dias_semana, default=dias_atuais)
            
            if st.button("💾 Salvar Agenda do Cliente"):
                if cod_cli_freq.strip():
                    if p_freq_sel not in freq_db:
                        freq_db[p_freq_sel] = {}
                    freq_db[p_freq_sel][cod_cli_freq.strip()] = dias_selecionados
                    salvar_frequencia(freq_db)
                    st.success(f"Agenda salva para o cliente {cod_cli_freq.strip()}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Digite o código do cliente.")
        else:
            st.warning("Cadastre promotores primeiro.")
                    
    with st.expander("🌍 Vincular Mapas por Cidade"):
        todas_cidades_cadastradas = set()
        for cids in config["promotores"].values():
            todas_cidades_cadastradas.update(cids)
        lista_cid_mapas = ["-- SELECIONE A CIDADE --"] + sorted(list(todas_cidades_cadastradas))
        cid_mapa_sel = st.selectbox("Selecione a Cidade:", lista_cid_mapas)
        link_atual_cid = config.get("mapas_cidades", {}).get(cid_mapa_sel, "") if cid_mapa_sel != "-- SELECIONE A CIDADE --" else ""
        novo_link_mapa_cid = st.text_input("🔗 Link Iframe do Mapa (Google):", value=link_atual_cid)
        if st.button("💾 Salvar Mapa da Cidade"):
            if cid_mapa_sel != "-- SELECIONE A CIDADE --":
                link_limpo_cid = extrair_link_iframe(novo_link_mapa_cid)
                config["mapas_cidades"][cid_mapa_sel] = link_limpo_cid
                salvar_config(config); st.success(f"Mapa salvo!"); time.sleep(1); st.rerun()

    st.divider()
    
    st.title("📍 Minassal Roteiro")
    vendas_f = st.file_uploader("1. Planilha de Vendas", type=["csv", "xlsx"])
    clientes_f = st.file_uploader("2. Planilha de Endereços", type=["csv", "xlsx"])
    
    lista_p = list(config["promotores"].keys())
    if not lista_p: st.stop()
    prom_ativo = st.selectbox("Selecione o Promotor:", lista_p)
    cids_p = config["promotores"].get(prom_ativo, [])
    cid_sel = st.selectbox("Filtrar por Cidade:", ["TODAS"] + cids_p)

# --- 5. LÓGICA PRINCIPAL ---
if vendas_f and clientes_f:
    df_vendas_total, df_end, col_v, col_e, col_d, col_f, col_vlr_todas, col_fam, col_prod = processar_bases(vendas_f, clientes_f, vendas_f.name, clientes_f.name)
    if not col_f: st.error("Coluna de CODIGO FABRICANTE não encontrada."); st.stop()
    df_vendas_total[col_f] = df_vendas_total[col_f].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    tab_dados, tab_mapa_google, tab_mapa_vivo, tab_roteirizador = st.tabs([
        "📋 Dashboard de Roteiro", 
        "🗺️ Mapa Clássico (Google)", 
        "📍 Mapa Vivo (Profissional)",
        "🚚 Roteirizador ROI"
    ])

    # ========================================================
    # ABA 2: MAPA CLÁSSICO DO GOOGLE
    # ========================================================
    with tab_mapa_google:
        if cid_sel != "TODAS" and config.get("mapas_cidades", {}).get(cid_sel):
            st.subheader(f"📍 Visualizando Mapa da Cidade: {cid_sel}")
            mapa_html = f'<iframe src="{config["mapas_cidades"][cid_sel]}" width="100%" height="600" style="border:0; border-radius: 8px;"></iframe>'
            components.html(mapa_html, height=620)
        else:
            st.info("👆 Selecione uma **Cidade** no menu esquerdo que tenha um mapa vinculado para visualizar as rotas.")

    # ========================================================
    # ABA 1: DADOS E ROTEIRIZAÇÃO
    # ========================================================
    with tab_dados:
        st.subheader("🎯 Filtros Estratégicos")
        filtro_forn = st.radio("Mostrar dados de:", ["Todos os Fabricantes", "Mars e Royal", "Somente Mars (4673)", "Somente Royal (15371)"], horizontal=True)

        if "Somente Mars" in filtro_forn: df_vendas_forn = df_vendas_total[df_vendas_total[col_f] == '4673'].copy()
        elif "Somente Royal" in filtro_forn: df_vendas_forn = df_vendas_total[df_vendas_total[col_f] == '15371'].copy()
        elif "Mars e Royal" in filtro_forn: df_vendas_forn = df_vendas_total[df_vendas_total[col_f].isin(['4673', '15371'])].copy()
        else: df_vendas_forn = df_vendas_total.copy()
        
        lista_familias = ["TODAS"] + sorted([str(x) for x in df_vendas_forn[col_fam].dropna().unique() if x != "NAN" and str(x).strip() != ""])
        filtro_familia = st.selectbox("Filtrar por Família de Produtos:", lista_familias)
        if filtro_familia != "TODAS": df_vendas_filtrado = df_vendas_forn[df_vendas_forn[col_fam] == filtro_familia].copy()
        else: df_vendas_filtrado = df_vendas_forn.copy()
        
        df_vendas_filtrado['POT_FILTRADO'] = df_vendas_filtrado['TOTAL VALOR']
        
        cols_end_merge = [col_e]
        for c_extra in ['DOCUMENTO', 'CNPJ', 'CPF', 'ENDEREÇO', 'ENDERECO', 'BAIRRO', 'CIDADE', 'LATITUDE', 'LONGITUDE', 'VISITAS']:
            col_encontrada = next((c for c in df_end.columns if c_extra in c), None)
            if col_encontrada and col_encontrada not in cols_end_merge: cols_end_merge.append(col_encontrada)
            
        df_vendas_filtrado[col_v] = df_vendas_filtrado[col_v].astype(str).str.replace('.0', '', regex=False).str.strip()
        df_end[col_e] = df_end[col_e].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        df_merge = pd.merge(df_vendas_filtrado, df_end[cols_end_merge], left_on=col_v, right_on=col_e, how='left')
        col_cidade_merge = next((c for c in df_merge.columns if 'CIDADE' in c), None)
        col_bairro_merge = next((c for c in df_merge.columns if 'BAIRRO' in c), None)
        col_lat = next((c for c in df_merge.columns if 'LATITUDE' in c), None)
        col_lon = next((c for c in df_merge.columns if 'LONGITUDE' in c), None)
        col_visitas = next((c for c in df_merge.columns if 'VISITAS' in c), None)
        
        if col_visitas:
            df_merge['META_VISITAS'] = pd.to_numeric(df_merge[col_visitas], errors='coerce').fillna(1).astype(int)
        else:
            df_merge['META_VISITAS'] = 1

        if col_cidade_merge:
            df_merge[col_cidade_merge] = df_merge[col_cidade_merge].fillna("N/A")
            if cid_sel == "TODAS": df_rot = df_merge[df_merge[col_cidade_merge].isin(cids_p)].copy()
            else: df_rot = df_merge[df_merge[col_cidade_merge] == cid_sel].copy()
        else: 
            st.warning("Coluna de CIDADE não encontrada."); df_rot = df_merge.copy()

        if col_bairro_merge:
            df_rot[col_bairro_merge] = df_rot[col_bairro_merge].fillna("N/A")
            bairros_disponiveis = sorted(list(df_rot[col_bairro_merge].unique()))
            bairros_selecionados = st.multiselect("📍 Restringir os resultados por Bairros (Micro-região):", bairros_disponiveis)
            if bairros_selecionados:
                df_rot = df_rot[df_rot[col_bairro_merge].isin(bairros_selecionados)].copy()

        col_end_exibir = next((c for c in df_rot.columns if 'ENDERE' in c), 'N/A')
        col_bairro_exibir = next((c for c in df_rot.columns if 'BAIRRO' in c), 'N/A')
        col_cliente_nome = 'N/A'
        for c in df_rot.columns:
            if c in ['CLIENTE NOME', 'RAZAO SOCIAL', 'RAZÃO SOCIAL', 'NOME FANTASIA']: col_cliente_nome = c; break
        if col_cliente_nome == 'N/A':
            for c in df_rot.columns:
                if 'CLIENTE' in c and 'NOME' in c: col_cliente_nome = c; break
                
        colunas_agrupamento = [col_v, col_cliente_nome, col_cidade_merge if col_cidade_merge else col_v, col_end_exibir, col_bairro_exibir]
        if col_lat: colunas_agrupamento.append(col_lat)
        if col_lon: colunas_agrupamento.append(col_lon)

        for c in colunas_agrupamento:
            if c not in df_rot.columns: df_rot[c] = "N/A"
            df_rot[c] = df_rot[c].fillna("N/A")

        with st.sidebar:
            st.divider()
            with st.expander("📘 Relatório de Leituras"):
                prom_relatorio = st.selectbox("👤 Promotor:", lista_p, key="sel_prom_leituras")
                cid_relatorio = st.selectbox("📍 Cidade:", ["TODAS"] + config["promotores"].get(prom_relatorio, []), key="sel_cid_leituras")
                
                grupos_cadastrados_rel = carregar_grupos()
                opcoes_grupos_rel = list(grupos_cadastrados_rel.keys())
                grupos_selecionados_rel = st.multiselect("🎯 Selecionar Grupos para Leitura:", opcoes_grupos_rel)
                
                # Fluxo de Geração Online (Botão de Download no Streamlit)
                v_cols = sorted([c for c in df_vendas_total.columns if 'QTD' in c and 'ABERTO' not in c and 'TOTAL' not in c])[-3:]
                todos_periodos = sorted([c for c in df_vendas_total.columns if 'QTD' in c and 'ABERTO' not in c and 'TOTAL' not in c])
                
                df_vendas_total_unf = df_vendas_total.copy()
                df_vendas_total_unf[col_v] = df_vendas_total_unf[col_v].astype(str).str.replace('.0', '', regex=False).str.strip()
                df_merge_unf = pd.merge(df_vendas_total_unf, df_end[cols_end_merge], left_on=col_v, right_on=col_e, how='left')
                if next((c for c in df_merge_unf.columns if 'CIDADE' in c), None):
                    df_merge_unf[next((c for c in df_merge_unf.columns if 'CIDADE' in c))] = df_merge_unf[next((c for c in df_merge_unf.columns if 'CIDADE' in c))].fillna("N/A")

                pdf_data_leituras = gerar_pdf_leituras(
                    prom_relatorio, 
                    [cid_relatorio] if cid_relatorio != "TODAS" else config["promotores"].get(prom_relatorio, []), 
                    df_merge_unf, 
                    df_vendas_total_unf, 
                    v_cols, 
                    col_fam, 
                    col_v, 
                    col_cliente_nome, 
                    col_prod, 
                    PASTA_SISTEMA, 
                    todos_periodos,
                    grupos_selecionados_rel,
                    grupos_cadastrados_rel
                )
                
                if pdf_data_leituras:
                    st.download_button(
                        label="📥 Baixar PDF de Leituras",
                        data=pdf_data_leituras,
                        file_name=f"Leituras_{prom_relatorio.replace(' ', '')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                elif grupos_selecionados_rel:
                    st.caption("Nenhuma oportunidade para os filtros selecionados.")
            
            with st.expander("📅 Relatório de Visitas (PDF)"):
                rel_vis_prom = st.selectbox("👤 Promotor:", lista_p, key="rel_vis_prom")
                c_dt1, c_dt2 = st.columns(2)
                with c_dt1: rel_dt_inicio = st.date_input("Data De:")
                with c_dt2: rel_dt_fim = st.date_input("Data Até:")
                
                col_cid_busca = next((c for c in df_end.columns if 'CIDADE' in c), None)
                pdf_data_vis = gerar_pdf_relatorio_visitas(
                    rel_vis_prom, rel_dt_inicio, rel_dt_fim, 
                    df_vendas_total, df_end, col_v, col_e, col_cliente_nome, col_cid_busca, 
                    config["promotores"], PASTA_SISTEMA
                )
                
                if pdf_data_vis:
                    st.download_button(
                        label="📥 Baixar Relatório de Visitas",
                        data=pdf_data_vis,
                        file_name=f"Relatorio_Visitas_{rel_vis_prom.replace(' ', '')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.caption("Nenhuma visita registrada no período.")

        t_filtro = df_rot['POT_FILTRADO'].sum()
        t_m = df_rot[df_rot[col_f] == '4673']['POT_FILTRADO'].sum()
        t_r = df_rot[df_rot[col_f] == '15371']['POT_FILTRADO'].sum()
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Filtro", f"R$ {t_filtro:,.2f}")
        c2.metric("Mars (4673)", f"R$ {t_m:,.2f}")
        c3.metric("Royal (15371)", f"R$ {t_r:,.2f}")

        colunas_agg = {'POT_FILTRADO': 'sum', 'META_VISITAS': 'max'}
        ranking = df_rot.groupby(colunas_agrupamento).agg(colunas_agg).reset_index().sort_values('POT_FILTRADO', ascending=False)
        
        status_ocultos = carregar_status()
        ranking_ativos = ranking[~ranking[col_v].astype(str).isin(status_ocultos.keys())].copy()
        ranking_ocultos = ranking[ranking[col_v].astype(str).isin(status_ocultos.keys())].copy()
        
        visitas = carregar_visitas()
        ranking_ativos['QTD_FEITAS'] = ranking_ativos[col_v].apply(lambda x: get_qtd_visitas_periodo(x, visitas, dt_inicio_p, dt_fim_p))
        pendentes = ranking_ativos[ranking_ativos['QTD_FEITAS'] < ranking_ativos['META_VISITAS']]

        busca = st.text_input("🔍 Buscar Cliente (Pendentes):")
        if busca:
            busca = limpar_texto(busca)
            pendentes = pendentes[pendentes[col_cliente_nome].astype(str).str.contains(busca, case=False, na=False) | pendentes[col_v].astype(str).str.contains(busca, na=False)]

        for idx, cli in pendentes.head(50).iterrows():
            cod_c = cli[col_v]
            nome_cli = str(cli.get(col_cliente_nome, 'NÃO INFORMADO'))
            meta = cli['META_VISITAS']
            feitas = cli['QTD_FEITAS']
            
            txt_visitas = f" | 🔄 Visita {feitas}/{meta}" if meta > 1 else ""
            
            with st.expander(f"🏢 {nome_cli} | CÓD: {cod_c} | 💰 R$ {cli['POT_FILTRADO']:,.2f}{txt_visitas}"):
                col1, col2 = st.columns([2, 1])
                v_cols = sorted([c for c in df_vendas_total.columns if 'QTD' in c and 'ABERTO' not in c and 'TOTAL' not in c])[-3:]
                todos_periodos = sorted([c for c in df_vendas_total.columns if 'QTD' in c and 'ABERTO' not in c and 'TOTAL' not in c])
                df_det = df_vendas_filtrado[df_vendas_filtrado[col_v] == cod_c]
                
                if not df_det.empty:
                    df_det_grouped = df_det.groupby([col_prod, 'PRODUTO NOME', col_fam])[todos_periodos].sum().reset_index()
                    cond_ultimos_3 = df_det_grouped[v_cols].sum(axis=1) > 0
                    cond_small = (df_det_grouped[col_prod].astype(str).str.replace('.0', '', regex=False).str.strip().isin(SMALL_BAGS_CODES)) & (df_det_grouped[todos_periodos].sum(axis=1) > 0)
                    v_recentes = df_det_grouped[cond_ultimos_3 | cond_small]
                else: v_recentes = pd.DataFrame()

                with col1:
                    st.write(f"**📍 Bairro:** {cli.get(col_bairro_exibir, 'N/A')} | **Endereço:** {cli.get(col_end_exibir, 'N/A')}")
                    if not v_recentes.empty:
                        col_mostrar = ['PRODUTO NOME', col_fam] + v_cols
                        st.dataframe(v_recentes[[c for c in col_mostrar if c in v_recentes.columns]], hide_index=True)
                    
                    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
                    with c_btn1:
                        btn_text = f"✅ Visita ({feitas + 1}/{meta})" if meta > 1 else "✅ Visita"
                        if st.button(btn_text, key=f"v_{cod_c}_{idx}", use_container_width=True):
                            registrar_visita(cod_c); st.rerun()
                    with c_btn2:
                        if st.button("🚫 Desprezar", key=f"desp_{cod_c}_{idx}", use_container_width=True):
                            registrar_visita(cod_c); st.rerun()
                    with c_btn3:
                        if st.button("👔 Funcionário", key=f"func_{cod_c}_{idx}", use_container_width=True):
                            registrar_status(cod_c, "FUNCIONARIO"); st.rerun()
                    with c_btn4:
                        if st.button("🛑 Não Aceita", key=f"naoac_{cod_c}_{idx}", use_container_width=True):
                            registrar_status(cod_c, "NAO_ACEITA"); st.rerun()
                            
                with col2:
                    if not v_recentes.empty:
                        pdf_bytes_cli = gerar_pdf_cliente_local(nome_cli, cod_c, v_recentes, v_cols, col_fam, col_prod, PASTA_SISTEMA, todos_periodos)
                        st.download_button(
                            label="📄 Baixar Histórico PDF",
                            data=pdf_bytes_cli,
                            file_name=f"Historico_{cod_c}.pdf",
                            mime="application/pdf",
                            key=f"dwn_pdf_{cod_c}_{idx}"
                        )

        with st.expander("✔️ Ver Visitados / Concluídos / Desprezados (Deste Período)"):
            visitados = ranking_ativos[ranking_ativos['QTD_FEITAS'] >= ranking_ativos['META_VISITAS']]
            if not visitados.empty:
                for idx, row in visitados.iterrows():
                    cod_v_c = row[col_v]
                    col_n1, col_n2 = st.columns([4, 1])
                    with col_n1:
                        txt_v = f" (Meta {row['META_VISITAS']} cumprida)" if row['META_VISITAS'] > 1 else ""
                        st.write(f"✅ {row[col_cliente_nome]} ({cod_v_c}){txt_v} - R$ {row['POT_FILTRADO']:,.2f}")
                    with col_n2:
                        if st.button("🔄 ESTORNAR", key=f"rev_{cod_v_c}_{idx}"):
                            remover_visita(cod_v_c); st.rerun()
                            
        with st.expander("🔒 Ver Clientes Ocultos (Funcionários / Não Aceitam)"):
            if not ranking_ocultos.empty:
                for idx, row in ranking_ocultos.iterrows():
                    cod_v_c = row[col_v]
                    motivo = status_ocultos.get(str(cod_v_c), "OCULTO")
                    icone = "👔" if motivo == "FUNCIONARIO" else "🛑"
                    col_n1, col_n2 = st.columns([4, 1])
                    with col_n1:
                        st.write(f"{icone} {row[col_cliente_nome]} ({cod_v_c}) - {motivo} - R$ {row['POT_FILTRADO']:,.2f}")
                    with col_n2:
                        if st.button("🔄 RESTAURAR", key=f"rest_st_{cod_v_c}_{idx}"):
                            remover_status(cod_v_c); st.rerun()
            else:
                st.write("Nenhum cliente oculto por status nesta filtragem.")

    # ========================================================
    # ABA 3: MAPA VIVO PROFISSIONAL
    # ========================================================
    with tab_mapa_vivo:
        st.subheader("📍 Mapa Vivo - Inteligência Geográfica")
        st.markdown("**Legenda:** 🟢 Concluído | 🟣 VIP (>15k) | 🔵 Ouro (>5k) | 🟠 Prata (>2.5k) | ⚪ Bronze")
        
        if col_lat and col_lon:
            df_coords = ranking_ativos.copy()
            df_coords[col_lat] = pd.to_numeric(df_coords[col_lat].astype(str).str.replace(',', '.'), errors='coerce')
            df_coords[col_lon] = pd.to_numeric(df_coords[col_lon].astype(str).str.replace(',', '.'), errors='coerce')
            df_coords = df_coords.dropna(subset=[col_lat, col_lon])
            
            if not df_coords.empty:
                centro_lat = df_coords[col_lat].mean()
                centro_lon = df_coords[col_lon].mean()
                
                m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13, tiles="CartoDB positron")
                
                for _, row in df_coords.iterrows():
                    pot = row['POT_FILTRADO']
                    cod_cliente = str(row[col_v])
                    nome_cli = str(row.get(col_cliente_nome, 'Cliente N/A'))
                    meta = row['META_VISITAS']
                    feitas = row['QTD_FEITAS']
                    
                    if feitas >= meta: cor_pino = 'green'
                    elif pot >= 15000: cor_pino = 'darkpurple'
                    elif pot >= 5000: cor_pino = 'blue'
                    elif pot >= 2500: cor_pino = 'orange'
                    else: cor_pino = 'lightgray'
                    
                    texto_freq = f"<br>Frequência: {feitas}/{meta} Visitas" if meta > 1 else ""
                    popup_html = f"<b>{nome_cli}</b><br>Cód: {cod_cliente}<br>Potencial: R$ {pot:,.2f}{texto_freq}"
                    
                    folium.Marker(
                        location=[row[col_lat], row[col_lon]],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=nome_cli,
                        icon=folium.Icon(color=cor_pino, icon='') 
                    ).add_to(m)
                
                st_folium(m, width="100%", height=600, returned_objects=[])
            else:
                st.info("Nenhuma coordenada válida encontrada para o filtro atual.")
        else:
            st.warning("As colunas 'LATITUDE' e 'LONGITUDE' não foram encontradas na Planilha de Endereços.")

    # ========================================================
    # ABA 4: ROTEIRIZADOR INTELIGENTE COM AGENDA FIXA
    # ========================================================
    with tab_roteirizador:
        st.subheader("🚚 Roteirizador Inteligente (ROI + Agenda)")
        
        data_roteiro = st.date_input("📅 Data planejada do Roteiro:", date.today())
        dias_pt = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
        dia_semana_atual = dias_pt[data_roteiro.weekday()]
        
        st.markdown(f"Gerando rota inteligente para **{dia_semana_atual}**, preenchendo as vagas com base em:")
        
        estrategia_rota = st.radio(
            "Estratégia de Preenchimento:", 
            ["💰 Por Retorno Financeiro (Foco em Vendas)", "📍 Por Proximidade Geográfica (Menor Distância)"], 
            horizontal=True, label_visibility="collapsed"
        )
        st.divider()

        grupos_cadastrados = carregar_grupos()
        opcoes_grupos = list(grupos_cadastrados.keys())
        grupos_selecionados = st.multiselect("🎯 Limitar visitas complementares a clientes que compram estes Grupos (Opcional):", opcoes_grupos)
        
        # --- BUSCA OS FIXOS ANTES PARA FURAR O BLOQUEIO DE VISITADOS ---
        freq_db = carregar_frequencia()
        codigos_fixos_hoje = []
        if prom_ativo in freq_db:
            for cod_cli_f, dias_lista in freq_db[prom_ativo].items():
                if dia_semana_atual in dias_lista:
                    codigos_fixos_hoje.append(str(cod_cli_f))
        
        # --- EXCLUSÃO DOS PULADOS NA BASE ANTES DE QUALQUER OPERAÇÃO ---
        ranking_filtrado_proxima = ranking_ativos[~ranking_ativos[col_v].astype(str).isin(st.session_state.ocultos_roteiro)].copy()
        
        cond_pendentes = ranking_filtrado_proxima['QTD_FEITAS'] < ranking_filtrado_proxima['META_VISITAS']
        cond_fixos = ranking_filtrado_proxima[col_v].astype(str).isin(codigos_fixos_hoje)
        
        df_pend_rot_base = ranking_filtrado_proxima[cond_pendentes | cond_fixos].copy()
        
        cods_grupo = []
        
        if grupos_selecionados:
            for g in grupos_selecionados:
                raw_g = grupos_cadastrados.get(g, {}).get("codigos", [])
                if isinstance(raw_g, str):
                    cods_grupo.extend([c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', raw_g) if c.strip()])
                else:
                    for item in raw_g:
                        cods_grupo.extend([c.strip().replace('.0', '') for c in re.split(r'[,\n\s]+', str(item)) if c.strip()])
            cods_grupo = list(set(cods_grupo))
            
            prod_limpo = df_vendas_filtrado[col_prod].astype(str).str.replace('.0', '', regex=False).str.strip()
            df_vendas_grupo = df_vendas_filtrado[prod_limpo.isin(cods_grupo)].copy()
            
            df_vendas_grupo_agg = df_vendas_grupo.groupby(col_v)['POT_FILTRADO'].sum().reset_index()
            df_vendas_grupo_agg.rename(columns={'POT_FILTRADO': 'POT_GRUPO'}, inplace=True)
            
            df_pend_rot_base = df_pend_rot_base.merge(df_vendas_grupo_agg, on=col_v, how='left')
            df_pend_rot_base['POT_GRUPO'] = df_pend_rot_base['POT_GRUPO'].fillna(0)
        else:
            df_pend_rot_base['POT_GRUPO'] = df_pend_rot_base['POT_FILTRADO']

        col_cid_rota = col_cidade_merge if col_cidade_merge else col_v
        cidades_pendentes = sorted(list(df_pend_rot_base[col_cid_rota].dropna().unique())) if not df_pend_rot_base.empty else []

        c_roi1, c_roi2, c_roi3 = st.columns(3)
        with c_roi1:
            valor_minimo_ancora = st.number_input("Valor mínimo para ser Âncora (R$):", min_value=0.0, value=1500.0, step=100.0)
            valor_minimo_visita = st.number_input("Valor mínimo para Visita (R$):", min_value=0.0, value=0.0, step=100.0)
            
        with c_roi2:
            max_visitas = st.number_input("Máximo de clientes no roteiro (por dia):", min_value=1, max_value=50, value=5, step=1)
        with c_roi3:
            cidade_dia_sel = st.selectbox("📍 Cidade do Roteiro de Hoje:", cidades_pendentes) if cidades_pendentes else None
        
        if col_lat and col_lon:
            df_pend_rot = df_pend_rot_base.copy()
            
            if cidade_dia_sel:
                df_pend_rot = df_pend_rot[df_pend_rot[col_cid_rota] == cidade_dia_sel]
                
            df_pend_rot[col_lat] = pd.to_numeric(df_pend_rot[col_lat].astype(str).str.replace(',', '.'), errors='coerce')
            df_pend_rot[col_lon] = pd.to_numeric(df_pend_rot[col_lon].astype(str).str.replace(',', '.'), errors='coerce')
            df_pend_rot = df_pend_rot.dropna(subset=[col_lat, col_lon])
            
            df_pend_rot['E_ANCORA'] = df_pend_rot['POT_FILTRADO'] >= valor_minimo_ancora
            
            if grupos_selecionados:
                df_pend_rot['E_VISITA'] = (df_pend_rot['POT_FILTRADO'] >= valor_minimo_visita) & (df_pend_rot['POT_GRUPO'] > 0)
            else:
                df_pend_rot['E_VISITA'] = df_pend_rot['POT_FILTRADO'] >= valor_minimo_visita
            
            if not df_pend_rot.empty:
                st.divider()
                
                df_fixos = df_pend_rot[df_pend_rot[col_v].astype(str).isin(codigos_fixos_hoje)].copy()
                df_restante = df_pend_rot[~df_pend_rot[col_v].astype(str).isin(codigos_fixos_hoje) & df_pend_rot['E_VISITA']].copy()
                
                rota_list = []
                
                for _, f_row in df_fixos.iterrows():
                    f_dict = f_row.to_dict()
                    f_dict['ANCORA'] = True 
                    f_dict['TXT_TIPO'] = "📌 COMPROMISSO FIXO DA AGENDA"
                    rota_list.append(pd.Series(f_dict))
                
                vagas_restantes = max_visitas - len(rota_list)
                
                if not rota_list and not df_restante.empty and vagas_restantes > 0:
                    df_restante['NOME_EXIBICAO_ANCORA'] = df_restante[col_v].astype(str) + " - " + df_restante[col_cliente_nome].astype(str)
                    lista_clientes_pendentes = ["-- AUTOMÁTICO (Maior Valor) --"] + df_restante['NOME_EXIBICAO_ANCORA'].tolist()
                    
                    c_anc1, c_anc2 = st.columns([2, 1])
                    with c_anc1:
                        ancora_manual = st.selectbox("📌 O dia não tem clientes fixos. Escolha a Âncora:", lista_clientes_pendentes)
                    with c_anc2:
                        ancora_codigo_direto = st.text_input("🔍 Ou digite o Código da Âncora:")
                    
                    if ancora_codigo_direto.strip():
                        ancora_match = df_restante[df_restante[col_v] == ancora_codigo_direto.strip()]
                        if not ancora_match.empty:
                            ancora_df = ancora_match.iloc[0]
                        else:
                            st.warning("Código não encontrado. Usando automático.")
                            ancora_df = df_restante.sort_values(by='POT_FILTRADO', ascending=False).iloc[0]
                    elif ancora_manual != "-- AUTOMÁTICO (Maior Valor) --":
                        ancora_df = df_restante[df_restante['NOME_EXIBICAO_ANCORA'] == ancora_manual].iloc[0]
                    else:
                        ancora_df = df_restante.sort_values(by='POT_FILTRADO', ascending=False).iloc[0]
                        
                    ancora_dict = ancora_df.to_dict()
                    ancora_dict['ANCORA'] = True
                    ancora_dict['TXT_TIPO'] = "⭐ ÂNCORA (Maior Retorno)"
                    rota_list.append(pd.Series(ancora_dict))
                    
                    df_restante = df_restante[df_restante[col_v] != ancora_dict[col_v]]
                    vagas_restantes -= 1

                if vagas_restantes > 0 and not df_restante.empty:
                    if "Proximidade" in estrategia_rota and len(rota_list) > 0:
                        current_lat = rota_list[-1][col_lat]
                        current_lon = rota_list[-1][col_lon]
                        
                        while len(rota_list) < max_visitas and not df_restante.empty:
                            df_restante['DIST_TEMP'] = df_restante.apply(lambda r: calcular_distancia(current_lat, current_lon, r[col_lat], r
