import streamlit as st
import pandas as pd
import os
import unicodedata
import smtplib
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="MARS - Oportunidades", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #001F3F; color: #FFD700; }
    div.stButton > button {
        height: 60px; font-size: 18px; font-weight: bold; border-radius: 10px;
        border: 3px solid #FF00FF; color: #001F3F; background-color: #FFD700;
        margin-bottom: 10px;
    }
    div.stButton > button:hover { background-color: #FF00FF; color: white; }
    .stSelectbox label, .stTextArea label { color: #FFD700 !important; font-weight: bold; }
    h1, h2, h3 { color: #FFD700 !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE AUXÍLIO ---
def obter_horario_brasil():
    return (datetime.now() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")

def limpar_texto(txt):
    if pd.isna(txt): return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFKD', txt) if not unicodedata.combining(c))

def converter_preco(valor):
    if pd.isna(valor) or str(valor).strip() == "": return 0.0
    try:
        v = str(valor).replace("R$", "").replace(" ", "").strip()
        if "," in v and "." in v: v = v.replace(".", "").replace(",", ".")
        elif "," in v: v = v.replace(",", ".")
        return float(v)
    except: return 0.0

def buscar_preco_na_tabela(arquivo, codigo_produto):
    diretorio_atual = os.path.dirname(__file__) if '__file__' in locals() else "."
    caminho_real = os.path.join(diretorio_atual, arquivo)
    if not os.path.exists(caminho_real): return 0.0
    try:
        df_p = pd.read_csv(caminho_real, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        df_p.columns = [str(c).strip().upper() for c in df_p.columns]
        row = df_p[df_p['CÓDIGO'].astype(str).str.strip() == str(codigo_produto).strip()]
        if not row.empty: return converter_preco(row.iloc[0]['PREÇO RECOMENDADO'])
    except: pass
    return 0.0

# --- CARREGAMENTO SIMPLIFICADO ---
@st.cache_data(ttl=60)
def carregar_vendas():
    # Procura qualquer arquivo que contenha 'VENDAS' no nome
    arquivos = [f for f in os.listdir(".") if 'VENDAS' in f.upper()]
    if not arquivos: return pd.DataFrame()
    
    # Lê o arquivo forçando o separador ';'
    df = pd.read_csv(arquivos[0], sep=';', encoding='utf-8-sig')
    # Remove espaços extras dos nomes das colunas e garante que sejam maiúsculas
    df.columns = [c.strip().upper() for c in df.columns]
    return df

# --- INTERFACE ---
st.markdown("<h1 style='text-align:center;'>🐾 SISTEMA DE OPORTUNIDADES MARS</h1>", unsafe_allow_html=True)

# Lógica principal que estava faltando no seu script
df_vendas = carregar_vendas()
if not df_vendas.empty:
    # AQUI ESTAVA O SEU ERRO: O Pandas não achava a coluna "CIDADE". 
    # Adicionei uma verificação de segurança:
    if 'CIDADE' in df_vendas.columns:
        df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
        # ... RESTANTE DO SEU CÓDIGO ORIGINAL AQUI ...
    else:
        st.error(f"Erro: Coluna 'CIDADE' não encontrada. Colunas disponíveis: {list(df_vendas.columns)}")
else:
    st.error("Planilha vazia ou não encontrada.")
