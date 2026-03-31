import streamlit as st
import pandas as pd
import os
import unicodedata
import smtplib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import io
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
    .sidebar-info { background-color: #002d5c; padding: 10px; border-left: 5px solid #FF00FF; margin-top: 20px; font-size: 13px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE AUXÍLIO ---
def obter_horario_brasil():
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")

def limpar_texto(txt):
    if pd.isna(txt): return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFKD', txt) if not unicodedata.combining(c))

def buscar_preco_na_tabela(arquivo, codigo_produto):
    if not os.path.exists(arquivo): return 0.0
    try:
        df_p = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        row = df_p[df_p['CÓDIGO'].astype(str).str.strip() == str(codigo_produto).strip()]
        if not row.empty:
            v = str(row.iloc[0]['PREÇO RECOMENDADO']).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
            return float(v)
    except: pass
    return 0.0

def salvar_na_torre_de_controle(promotor, loja, total_focais, total_comprados, rupturas, tipo="PADRAO"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Torre_de_Controle_Mars").sheet1
        linha = [obter_horario_brasil(), promotor, loja, total_focais, total_comprados, rupturas, tipo]
        sheet.append_row(linha)
    except: pass 

# --- PRODUTOS E ROTAS ---
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
    "SARUETE": ["SAO JOSE DO RIO PRETO", "MIRASSOL", "CATANDUVA"], "MADALLA": ["TOCANTINS", "UBA"], "FERNANDA": ["JUIZ DE FORA"]
}

# --- FUNÇÃO PDF ---
def gerar_pdf_mars(promotor, loja, cidade, df_audit, df_faltantes, feedback):
    nome_arquivo = f"Oportunidades_Mars_{loja.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4)
    elementos = []
    estilos = getSampleStyleSheet()
    
    elementos.append(Paragraph(f"<b>RELATÓRIO DE OPORTUNIDADES MARS</b>", estilos['Title']))
    elementos.append(Paragraph(f"<b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade}", estilos['Normal']))
    elementos.append(Paragraph(f"<b>PROMOTOR:</b> {promotor} | <b>DATA:</b> {obter_horario_brasil()}", estilos['Normal']))
    elementos.append(Spacer(1, 15))
    
    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS E GÔNDOLA</b>", estilos['Heading3']))
        data_audit = [["PRODUTO", "REC. MARS", "PREÇO LOJA", "SITUAÇÃO", "FALTA?"]]
        row_colors = []
        
        for i, r in enumerate(df_audit.itertuples()):
            # Correção de índices: 0:Index, 1:CÓDIGO, 2:PRODUTO, 3:SUGERIDO, 4:FALTA, 5:PREÇO
            p_loja = float(r._5) 
            p_rec_val = float(str(r.SUGERIDO).replace("R$", "").strip())
            falta_status = "SIM" if r._4 else "NÃO"
            
            # Lógica da Situação e Porcentagem
            if p_loja == 0:
                sit = "N/I"
            else:
                perc = ((p_loja - p_rec_val) / p_rec_val) * 100
                if p_loja > p_rec_val:
                    sit = f"ACIMA (+{perc:.1f}%)"
                    row_colors.append(('TEXTCOLOR', (3, i+1), (3, i+1), colors.red))
                else:
                    sit = f"CORRETO ({perc:.1f}%)"
            
            data_audit.append([r.PRODUTO[:30], r.SUGERIDO, f"R$ {p_loja:.2f}", sit, falta_status])
            
        # Ajuste de larguras: REC. MARS e PREÇO LOJA menores para caber tudo
        t1 = Table(data_audit, colWidths=[180, 75, 75, 100, 50])
        estilo_t1 = [
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 8)
        ]
        estilo_t1.extend(row_colors)
        t1.setStyle(TableStyle(estilo_t1)); elementos.append(t1); elementos.append(Spacer(1, 15))

    elementos.append(Paragraph("<b>2. OPORTUNIDADES (ITENS NÃO COMERCIALIZADOS)</b>", estilos['Heading3']))
    data_faltantes = [["Código", "Produto"]]
    for f in df_faltantes: data_faltantes.append([f[0], f[1]])
    t2 = Table(data_faltantes, colWidths=[80, 400])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elementos.append(t2); elementos.append(Spacer(1, 15))
    
    elementos.append(Paragraph(f"<b>OBSERVAÇÕES DO PROMOTOR:</b>", estilos['Heading3']))
    elementos.append(Paragraph(feedback if feedback else "Sem observações.", estilos['Normal']))
    doc.build(elementos); return nome_arquivo

def enviar_email(assunto, pdf):
    rem, sen, dest = "beneditobandola@gmail.com", "kfih ccqx cskn oito", "benedito.bandola@minassal.com.br"
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = rem, dest, assunto
    try:
        with open(pdf, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf)}"'
            msg.attach(part)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(rem, sen)
        s.sendmail(rem, dest, msg.as_string()); s.quit(); return True
    except: return False

# --- INTERFACE ---
try:
    df_vendas = pd.read_csv("Vendas_Mars.csv", sep=None, engine='python', encoding='utf-8-sig')
    df_vendas.columns = [c.strip().upper() for c in df_vendas.columns]
    df_vendas['DATA'] = pd.to_datetime(df_vendas['DATA'], errors='coerce')
except:
    st.error("Erro ao carregar Vendas_Mars.csv"); st.stop()

if 'user_mars' not in st.session_state:
    st.title("🐾 RELATÓRIOS DE OPORTUNIDADES")
    cols = st.columns(3)
    for i, nome in enumerate(ROTAS_MARS.keys()):
        if cols[i % 3].button(nome, use_container_width=True):
            st.session_state.user_mars = nome; st.rerun()
else:
    promotor = st.session_state.user_mars
    st.sidebar.title(f"👤 {promotor}")
    if st.sidebar.button("Sair"): del st.session_state.user_mars; st.rerun()

    df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
    cidades_auth = [limpar_texto(c) for c in ROTAS_MARS[promotor]]
    df_f = df_vendas[df_vendas['CIDADE_BUSCA'].isin(cidades_auth)]
    
    loja = st.selectbox("🏪 Selecione a Loja:", ["-- Selecione --"] + sorted(df_f['CLIENTE NOME'].unique()))

    if loja != "-- Selecione --":
        vendas_loja = df_f[df_f['CLIENTE NOME'] == loja]
        cidade_loja = vendas_loja.iloc[0]['CIDADE']
        unidade_txt = str(vendas_loja.iloc[0, 0]).upper()
        arquivo_preco = "MINEIROS PREÇOS MARS COMPLETO.csv" if (unidade_txt.startswith("1") or unidade_txt.startswith("4")) else "PAULISTINHAS MARS PREÇO.csv"
        
        st.sidebar.markdown(f"""<div class="sidebar-info"><b>📍 FILIAL:</b> {unidade_txt}<br><b>📁 TABELA:</b> {arquivo_preco}</div>""", unsafe_allow_html=True)

        compras_cliente = set(vendas_loja['PRODUTO CODIGO'].astype(str).unique())
        dados_audit, faltantes = [], []
        for cod, nome in PRODUTOS_FOCAIS.items():
            if cod in compras_cliente:
                p_s = buscar_preco_na_tabela(arquivo_preco, cod)
                # Adicionado coluna de FALTA no data_editor
                dados_audit.append({"CÓDIGO": cod, "PRODUTO": nome, "SUGERIDO": f"R$ {p_s:.2f}", "FALTA NA LOJA?": False, "PREÇO GÔNDOLA": 0.0})
            else:
                faltantes.append([cod, nome])

        if dados_audit:
            st.write(f"### Auditoria - {loja} ({cidade_loja})")
            df_edit = st.data_editor(pd.DataFrame(dados_audit), use_container_width=True, hide_index=True, disabled=["CÓDIGO", "PRODUTO", "SUGERIDO"])
            feedback = st.text_area("🗣️ Observações do Promotor:")
            if st.button("🚀 FINALIZAR E ENVIAR RELATÓRIO", use_container_width=True):
                with st.spinner("Enviando..."):
                    pdf = gerar_pdf_mars(promotor, loja, cidade_loja, df_edit, faltantes, feedback)
                    enviar_email(f"🐾 OPORTUNIDADE MARS: {loja}", pdf)
                    salvar_na_torre_de_controle(promotor, loja, len(PRODUTOS_FOCAIS), len(dados_audit), len(faltantes))
                    st.success("Enviado com sucesso!"); st.balloons()
        else:
            st.error("🚨 CLIENTE NÃO COMPROU NENHUMA VERSÃO DE SMALL BAGS NEM DE INOVAÇÕES EM 2026")
            feedback_cr = st.text_area("🗣️ Justificativa da Falta de Mix:")
            if st.button("🚨 ENVIAR CRÍTICA DE MIX COMPLETO", use_container_width=True):
                pdf = gerar_pdf_mars(promotor, loja, cidade_loja, pd.DataFrame(), faltantes, feedback_cr)
                enviar_email(f"🚨 CRÍTICA MIX: {loja}", pdf)
                salvar_na_torre_de_controle(promotor, loja, len(PRODUTOS_FOCAIS), 0, len(PRODUTOS_FOCAIS), "CRÍTICA TOTAL")
                st.success("Crítica enviada!"); st.balloons()
