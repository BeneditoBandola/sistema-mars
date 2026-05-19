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

def salvar_nas_planilhas(resumo, detalhado):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Torre_de_Controle_Mars")
        spreadsheet.sheet1.append_row(resumo)
        aba_detalhe = spreadsheet.worksheet("oportunidades detalhadas")
        aba_detalhe.append_rows(detalhado, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return False

# --- DADOS ---
PRODUTOS_FOCAIS = {"99954": "FILEZITOS AD CARNE 60G", "98985": "CHAMP ADULTO 900G", "98679": "KITEKAT DRY 900G"} # Simplificado para teste
ROTAS_MARS = {
    "MADALLA": ["CONSELHEIRO LAFAIETE", "GUARANI", "GUIDOVAL", "MURIAE", "MURIAÉ", "PIRAUBA", "PIRAÚBA", "RIO POMBA", "TOCANTINS", "UBA", "UBÁ", "VICOSA", "VIÇOSA", "VISCONDE DO RIO BRANCO"],
    "PAMELA": ["POCOS DE CALDAS"]
}

# --- CARREGAMENTO FORÇADO ---
@st.cache_data(ttl=60)
def carregar_vendas():
    arquivos = [f for f in os.listdir(".") if 'VENDAS' in f.upper()]
    if not arquivos: return pd.DataFrame()
    
    df = pd.read_csv(arquivos[0], sep=';', encoding='utf-8-sig')
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

# --- INTERFACE ---
st.title("🐾 SISTEMA DE OPORTUNIDADES MARS")
promotor = st.selectbox("Selecione o Promotor", list(ROTAS_MARS.keys()))

if promotor:
    df_vendas = carregar_vendas()
    if df_vendas.empty:
        st.error("Planilha de vendas não encontrada ou vazia!")
    else:
        df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
        lojas = sorted(df_vendas['CLIENTE NOME'].unique())
        loja = st.selectbox("Selecione a Loja", ["--"] + lojas)
        
        if loja != "--":
            st.success(f"Dados carregados para: {loja}")
            # ... resto da sua lógica de exibição ...
