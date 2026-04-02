import streamlit as st
import pandas as pd
import os
import unicodedata
import smtplib
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Bibliotecas para a criação do PDF
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
    if not os.path.exists(arquivo): return 0.0
    try:
        df_p = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        row = df_p[df_p['CÓDIGO'].astype(str).str.strip() == str(codigo_produto).strip()]
        if not row.empty: return converter_preco(row.iloc[0]['PREÇO RECOMENDADO'])
    except: pass
    return 0.0

# --- LISTA MESTRA FOCAL ---
PRODUTOS_FOCAIS = {
    "99954": "FILEZITOS AD CARNE 60G", "99955": "FILEZITOS AD CHURRASCO 60G", "99956": "FILEZITOS AD FRANGO 60G", "100051": "FILEZITOS AD CHURRASCO 400G",
    "99798": "BISCROK AD RP BANANA 500G", "99799": "BISCROK AD RP MACA 500G",
    "98985": "CHAMP ADULTO CARNE & CEREAL 900G", "98980": "CHAMP FILHOTES 900G", "98679": "KITEKAT DRY AD MIX DE CARNES 900G",
    "99777": "PED TASTY BITES CARNE 130G", "99776": "PED TASTY BITES CARNE 40G", "99773": "PED TASTY BITES CARNE 80G", "99774": "PED TASTY BITES FRANGO 80G", "99775": "PED TASTY BITES LEITE 80G",
    "99830": "SHE CRE AT&SAL+FGO&CAM 4X12G", "99742": "SHE CRE ATUM 2X12G", "99743": "SHE CRE ATUM 4X12G", "99744": "SHE CRE ATUM&AT+CAM 4X12G", "99831": "SHE CRE FGO&SAL 2X12G", "99745": "SHE CRE FRG&FRG+PE 4X12G",
    "98989": "PED NUTRICAO ESSENCIAL AO LEITE 900G", "98982": "PED NUTRICAO ESSENCIAL CARNE 900G", "98933": "PEDIGREE AD CARNE&FRANG 2,7KG", "98934": "PEDIGREE AD CARNE&FRANG 900G",
    "98914": "PEDIGREE AD CARNE&VEG 2,7KG", "98915": "PEDIGREE AD CARNE&VEG 900G", "98911": "PEDIGREE AD RP 2,7KG", "98912": "PEDIGREE AD RP 900G",
    "98930": "PEDIGREE FIL 2,7KG", "98931": "PEDIGREE FIL 900G", "98899": "WHI AD CARNE 500G", "98898": "WHI AD CARNE 900G", "98941": "WHI AD FRANGO 900G",
    "98937": "WHI AD PEIXE 500G", "98936": "WHI AD PEIXE 900G", "98944": "WHI FILHOTES CARNE 500G", "98942": "WHI FILHOTES CARNE 900G",
    "98903": "WHI GATO CAST CARNE 500G", "98902": "WHI GATO CAST CARNE 900G", "98946": "WHI GATOS CAST PEIXE 900G"
}

ROTAS_MARS = {
    "PAMELA": ["POCOS DE CALDAS", "ANDRADAS", "GUAXUPE", "VARGINHA", "TRES CORACOES", "TRES PONTAS", "ITAJUBA", "ALFENAS", "POUSO ALEGRE"],
    "RODRIGO": ["RIBEIRAO PRETO", "SERTÃOZINHO"], "TIAGO": ["SAO CARLOS", "ARARAQUARA", "MATAO"], "LUCIVANIA": ["MARILIA", "LINS", "TUPA"],
    "SARUETE": ["SAO JOSE DO RIO PRETO", "MIRASSOL", "CATANDUVA"], "MADALLA": ["TOCANTINS","PIRAUBA","GUARANI","RIO POMBA","VISCONDE DO RIO BRANCO", "UBA", "RIO POMBA"], "FERNANDA": ["JUIZ DE FORA"]
}

@st.cache_data
def carregar_vendas():
    df = pd.read_csv("Vendas_Mars.csv", sep=None, engine='python', encoding='utf-8-sig')
    df.columns = [c.strip().upper() for c in df.columns]
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
    return df

# --- FUNÇÃO PDF AJUSTADA ---
def gerar_pdf_mars(promotor, loja, cidade, df_audit, df_faltantes, feedback):
    nome_arquivo = f"Oportunidades_Mars_{loja.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()
    
    elementos.append(Paragraph("<b>RELATÓRIO DE OPORTUNIDADES MARS</b>", estilos['Title']))
    elementos.append(Paragraph(f"<b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade}", estilos['Normal']))
    elementos.append(Paragraph(f"<b>PROMOTOR:</b> {promotor} | <b>DATA:</b> {obter_horario_brasil()}", estilos['Normal']))
    elementos.append(Spacer(1, 15))
    
    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS E GÔNDOLA</b>", estilos['Heading3']))
        data_audit = [["PRODUTO", "REC. MARS", "PREÇO LOJA", "SITUAÇÃO", "FALTA?"]]
        row_colors = []
        
        for i, row in enumerate(df_audit.to_dict('records')):
            idx = i + 1
            p_rec_val = converter_preco(row.get('SUGERIDO', 0.0))
            p_loja_val = float(row.get('PREÇO GÔNDOLA', 0.0))
            falta_status = "SIM" if row.get('FALTA NA LOJA?', False) else "NÃO"
            
            if p_loja_val == 0:
                sit = "FALTA"
                row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
            else:
                dif = ((p_loja_val - p_rec_val) / p_rec_val) * 100
                if p_loja_val > (p_rec_val + 0.01):
                    sit = f"ACIMA (+{dif:.1f}%)"
                    row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
                elif p_loja_val < (p_rec_val - 0.01):
                    # Novo ajuste: Mostra a porcentagem negativa se estiver mais barato
                    sit = f"CORRETO ({dif:.1f}%)"
                    row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.green))
                else:
                    sit = "CORRETO"
                    row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.green))
            
            data_audit.append([row.get('PRODUTO', '')[:30], f"R$ {p_rec_val:.2f}", f"R$ {p_loja_val:.2f}", sit, falta_status])
            
        t1 = Table(data_audit, colWidths=[190, 80, 80, 110, 55])
        estilo_t1 = [('BACKGROUND', (0,0), (-1,0), colors.navy), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ALIGN', (1,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 9)]
        estilo_t1.extend(row_colors); t1.setStyle(TableStyle(estilo_t1)); elementos.append(t1); elementos.append(Spacer(1, 15))
        
    elementos.append(Paragraph("<b>2. OPORTUNIDADES (ITENS NÃO COMERCIALIZADOS)</b>", estilos['Heading3']))
    data_f = [["Código", "Produto"]]
    for f in df_faltantes: data_f.append([f[0], f[1]])
    t2 = Table(data_f, colWidths=[80, 435])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elementos.append(t2)
    
    if feedback:
        elementos.append(Spacer(1, 15)); elementos.append(Paragraph(f"<b>OBSERVAÇÕES:</b> {feedback}", estilos['Normal']))
    
    doc.build(elementos); return nome_arquivo

def enviar_email(assunto, pdf):
    rem, sen, dest = "beneditobandola@gmail.com", "kfih ccqx cskn oito", "benedito.bandola@minassal.com.br"
    msg = MIMEMultipart(); msg['From'], msg['To'], msg['Subject'] = rem, dest, assunto
    try:
        with open(pdf, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf))
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf)); msg.attach(part)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(rem, sen); s.sendmail(rem, dest, msg.as_string()); s.quit(); return True
    except: return False

# --- INTERFACE ---
df_vendas = carregar_vendas()
if 'user_mars' not in st.session_state:
    st.subheader("👤 Selecione o Promotor:")
    cols = st.columns(3)
    for i, nome in enumerate(ROTAS_MARS.keys()):
        if cols[i % 3].button(nome, use_container_width=True): st.session_state.user_mars = nome; st.rerun()
else:
    promotor = st.session_state.user_mars
    st.sidebar.title(f"Promotor: {promotor}")
    if st.sidebar.button("Sair"): del st.session_state.user_mars; st.rerun()

    df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
    cidades_auth = [limpar_texto(c) for c in ROTAS_MARS[promotor]]
    df_f = df_vendas[df_vendas['CIDADE_BUSCA'].isin(cidades_auth)]
    loja = st.selectbox("🏪 Selecione a Loja:", ["-- Selecione --"] + sorted(df_f['CLIENTE NOME'].unique()))

    if loja != "-- Selecione --":
        vendas_loja = df_f[df_f['CLIENTE NOME'] == loja]
        unidade_txt = str(vendas_loja.iloc[0, 0]).upper()
        cidade_loja = vendas_loja.iloc[0]['CIDADE']
        arquivo_preco = "MINEIROS PREÇOS MARS COMPLETO.csv" if (unidade_txt.startswith("1") or unidade_txt.startswith("4")) else "PAULISTINHAS MARS PREÇO.csv"
        
        compras_cliente = set(vendas_loja['PRODUTO CODIGO'].astype(str).unique())
        dados_audit, faltantes = [], []
        for cod, nome in PRODUTOS_FOCAIS.items():
            if cod in compras_cliente:
                p_s = buscar_preco_na_tabela(arquivo_preco, cod)
                dados_audit.append({"CÓDIGO": cod, "PRODUTO": nome, "SUGERIDO": f"R$ {p_s:.2f}", "FALTA NA LOJA?": False, "PREÇO GÔNDOLA": 0.0})
            else: 
                faltantes.append([cod, nome])

        if dados_audit:
            df_edit = st.data_editor(pd.DataFrame(dados_audit), use_container_width=True, hide_index=True, disabled=["CÓDIGO", "PRODUTO", "SUGERIDO"])
            feedback = st.text_area("🗣️ Observações:")
            if st.button("🚀 ENVIAR RELATÓRIO"):
                pdf = gerar_pdf_mars(promotor, loja, cidade_loja, df_edit, faltantes, feedback)
                if enviar_email(f"🐾 OPORTUNIDADE MARS: {loja}", pdf):
                    st.success("Relatório enviado!"); st.balloons()
