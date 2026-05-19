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

# --- CARREGAMENTO CORRIGIDO ---
@st.cache_data(ttl=60)
def carregar_vendas():
    try:
        arquivos = [f for f in os.listdir(".") if 'VENDAS' in f.upper()]
        if not arquivos: return pd.DataFrame()
        
        # Leitura forçada com utf-8-sig (remove o caractere invisível \ufeff)
        df = pd.read_csv(arquivos[0], sep=';', encoding='utf-8-sig')
        
        # Limpeza robusta das colunas
        df.columns = [str(c).strip().upper().replace('\ufeff', '') for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro na carga: {e}")
        return pd.DataFrame()

# --- DADOS E INTERFACE ---
ROTAS_MARS = {
    "MADALLA": ["CONSELHEIRO LAFAIETE", "GUARANI", "GUIDOVAL", "MURIAE", "MURIAÉ", "PIRAUBA", "PIRAÚBA", "RIO POMBA", "TOCANTINS", "UBA", "UBÁ", "VICOSA", "VIÇOSA", "VISCONDE DO RIO BRANCO"],
    "PAMELA": ["POCOS DE CALDAS"]
}

st.title("🐾 SISTEMA DE OPORTUNIDADES MARS")
df_vendas = carregar_vendas()

if df_vendas.empty:
    st.error("Planilha vazia ou não encontrada.")
else:
    # A verificação que estava dando erro
    if 'CIDADE' in df_vendas.columns:
        df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
        promotor = st.selectbox("Selecione o Promotor", list(ROTAS_MARS.keys()))
        if promotor:
            lojas = sorted(df_vendas[df_vendas['CIDADE_BUSCA'].isin([limpar_texto(c) for c in ROTAS_MARS[promotor]])]['CLIENTE NOME'].unique())
            loja = st.selectbox("Selecione a Loja", ["--"] + lojas)
            if loja != "--":
                st.write(f"Trabalhando na loja: {loja}")
    else:
        st.error(f"Erro: A coluna 'CIDADE' não foi encontrada. Colunas lidas: {list(df_vendas.columns)}")
