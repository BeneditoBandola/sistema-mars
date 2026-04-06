import streamlit as st
import pandas as pd
import os
import unicodedata
import smtplib
import gspread
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
    if not os.path.exists(arquivo): return 0.0
    try:
        df_p = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        df_p.columns = [c.strip().upper() for c in df_p.columns]
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
        try:
            aba_detalhe = spreadsheet.worksheet("oportunidades detalhadas")
        except:
            aba_detalhe = spreadsheet.get_worksheet(1)
        aba_detalhe.append_rows(detalhado)
        return True
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return False

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
    "RODRIGO": ["RIBEIRAO PRETO", "SERTÃOZINHO"], 
    "TIAGO": ["SAO CARLOS", "ARARAQUARA", "MATAO"], 
    "LUCIVANIA": ["MARILIA", "LINS", "TUPA"],
    "SARUETE": ["SAO JOSE DO RIO PRETO", "MIRASSOL", "CATANDUVA"], 
    "MADALLA": ["TOCANTINS","PIRAUBA","GUARANI","RIO POMBA","VISCONDE DO RIO BRANCO", "UBA", "RIO POMBA"], 
    "FERNANDA": ["JUIZ DE FORA"]
}

@st.cache_data
def carregar_vendas():
    try:
        df = pd.read_csv("Vendas_Mars.csv", sep=None, engine='python', encoding='utf-8-sig')
        df.columns = [c.strip().upper() for c in df.columns]
        if 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo Vendas_Mars.csv: {e}")
        return pd.DataFrame()

def gerar_pdf_mars(promotor, loja, cidade, df_audit, df_faltantes, feedback):
    nome_arquivo = f"Oportunidades_{loja.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos, estilos = [], getSampleStyleSheet()
    dt_pdf = obter_horario_brasil()
    elementos.append(Paragraph("<b>RELATÓRIO DE OPORTUNIDADES MARS</b>", estilos['Title']))
    elementos.append(Paragraph(f"<b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade} | <b>PROMOTOR:</b> {promotor}", estilos['Normal']))
    elementos.append(Paragraph(f"<b>DATA/HORA:</b> {dt_pdf}", estilos['Normal']))
    elementos.append(Spacer(1, 15))
    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS</b>", estilos['Heading3']))
        data_audit = [["PRODUTO", "REC. MARS", "PREÇO LOJA", "SITUAÇÃO", "FALTA?"]]
        row_colors = []
        for i, row in enumerate(df_audit.to_dict('records')):
            idx = i + 1
            p_rec = converter_preco(row.get('SUGERIDO', 0.0))
            p_loja = float(row.get('PREÇO GÔNDOLA', 0.0))
            if p_loja == 0 or row.get('FALTA NA LOJA?'):
                sit = "FALTA"; row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
            else:
                dif = ((p_loja - p_rec) / p_rec) * 100
                if p_loja > (p_rec + 0.01):
                    sit = f"ACIMA (+{dif:.1f}%)"; row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
                elif p_loja < (p_rec - 0.01):
                    sit = f"CORRETO ({dif:.1f}%)"; row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.green))
                else:
                    sit = "CORRETO"; row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.green))
            data_audit.append([row.get('PRODUTO', '')[:30], f"R$ {p_rec:.2f}", f"R$ {p_loja:.2f}", sit, "SIM" if row.get('FALTA NA LOJA?') else "NÃO"])
        t1 = Table(data_audit, colWidths=[190, 80, 80, 110, 55])
        t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.navy), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)] + row_colors))
        elementos.append(t1)
    elementos.append(Paragraph("<b>2. OPORTUNIDADES (ITENS NÃO COMERCIALIZADOS)</b>", estilos['Heading3']))
    data_f = [["Código", "Produto"]]
    for f in df_faltantes: data_f.append([f[0], f[1]])
    t2 = Table(data_f, colWidths=[80, 435])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elementos.append(t2)
    if feedback: elementos.append(Paragraph(f"<b>OBS:</b> {feedback}", estilos['Normal']))
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

# --- INTERFACE PRINCIPAL ---
st.markdown("<h1 style='text-align:center;'>🐾 SISTEMA DE OPORTUNIDADES MARS</h1>", unsafe_allow_html=True)

# 1. Desenha os botões de seleção de Promotor PRIMEIRO
if 'user_mars' not in st.session_state:
    st.subheader("Selecione o seu nome:")
    cols = st.columns(3)
    for i, nome in enumerate(ROTAS_MARS.keys()):
        if cols[i % 3].button(nome, use_container_width=True): 
            st.session_state.user_mars = nome
            st.rerun()
else:
    # 2. Se um promotor foi selecionado, carrega os dados e mostra a tela de trabalho
    df_vendas = carregar_vendas()
    
    if df_vendas.empty:
        st.error("Erro crítico: Não foi possível carregar os dados de vendas.")
        if st.button("Voltar ao Início"):
            del st.session_state.user_mars
            st.rerun()
        st.stop()

    promotor = st.session_state.user_mars
    
    # --- MAPEAMENTO DE FILIAL E TABELA POR PROMOTOR ---
    if promotor == "PAMELA":
        f_label, arq_precos = "POÇOS DE CALDAS", "MINEIROS PREÇOS MARS COMPLETO.csv"
    elif promotor in ["RODRIGO", "TIAGO"]:
        f_label, arq_precos = "SÃO JOÃO DA BOA VISTA", "PAULISTINHAS MARS PREÇO.csv"
    elif promotor in ["SARUETE", "LUCIVANIA"]:
        f_label, arq_precos = "SÃO JOSÉ DO RIO PRETO", "PAULISTINHAS MARS PREÇO.csv"
    elif promotor in ["FERNANDA", "MADALLA"]:
        f_label, arq_precos = "JUIZ DE FORA", "MINEIROS PREÇOS MARS COMPLETO.csv"
    else:
        f_label, arq_precos = "FILIAL NÃO MAPEADA", "MINEIROS PREÇOS MARS COMPLETO.csv"

    st.sidebar.markdown(f"### 👤 Promotor: {promotor}")
    st.sidebar.info(f"🏢 Filial: {f_label}")
    st.sidebar.caption(f"📊 Tabela: {arq_precos}")
    
    if st.sidebar.button("Trocar Promotor"):
        del st.session_state.user_mars
        st.rerun()

    # Filtro de Lojas
    df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
    df_f = df_vendas[df_vendas['CIDADE_BUSCA'].isin([limpar_texto(c) for c in ROTAS_MARS[promotor]])]
    
    loja = st.selectbox("🏪 Selecione a Loja:", ["-- Selecione --"] + sorted(df_f['CLIENTE NOME'].unique()))

    if loja != "-- Selecione --":
        v_loja = df_f[df_f['CLIENTE NOME'] == loja]
        cidade_l = v_loja.iloc[0]['CIDADE']
        comp_cli = set(v_loja['PRODUTO CODIGO'].astype(str).unique())
        
        dados_audit_view, prod_faltantes = [], []
        for c, n in PRODUTOS_FOCAIS.items():
            if c in comp_cli:
                dados_audit_view.append({
                    "FALTA NA LOJA?": False, "CÓDIGO": c, "PRODUTO": n, 
                    "PREÇO GÔNDOLA": 0.0, "SUGERIDO": f"R$ {buscar_preco_na_tabela(arq_precos, c):.2f}"
                })
            else: prod_faltantes.append([c, n])
        
        if dados_audit_view:
            df_edit = st.data_editor(pd.DataFrame(dados_audit_view), use_container_width=True, hide_index=True, disabled=["CÓDIGO", "PRODUTO", "SUGERIDO"])
            obs_text = st.text_area("🗣️ Observações:")
            if st.button("🚀 ENVIAR RELATÓRIO"):
                horario_ref = obter_horario_brasil()
                detalhado_rows = []
                for r in df_edit.to_dict('records'):
                    status_val = "FALTA" if r['FALTA NA LOJA?'] or float(r['PREÇO GÔNDOLA']) == 0 else "TEM"
                    detalhado_rows.append([horario_ref, promotor, loja, cidade_l, r['CÓDIGO'], r['PRODUTO'], status_val])
                for f in prod_faltantes:
                    detalhado_rows.append([horario_ref, promotor, loja, cidade_l, f[0], f[1], "NÃO COMERCIALIZA"])
                pdf_file = gerar_pdf_mars(promotor, loja, cidade_l, df_edit, prod_faltantes, obs_text)
                if enviar_email(f"🐾 OPORTUNIDADE: {loja}", pdf_file):
                    salvar_nas_planilhas([horario_ref, promotor, loja, cidade_l, obs_text], detalhado_rows)
                    st.success("Enviado com sucesso!"); st.balloons()
        else:
            st.warning("🚨 Mix Zero!")
            obs_z_mix = st.text_area("🗣️ Justificativa Mix Zero:")
            if st.button("🚨 ENVIAR MIX ZERO"):
                horario_ref = obter_horario_brasil()
                detalhado_rows = [[horario_ref, promotor, loja, cidade_l, f[0], f[1], "MIX ZERO"] for f in prod_faltantes]
                pdf_file = gerar_pdf_mars(promotor, loja, cidade_l, pd.DataFrame(), prod_faltantes, obs_z_mix)
                if enviar_email(f"🚨 MIX ZERO: {loja}", pdf_file):
                    salvar_nas_planilhas([horario_ref, promotor, loja, cidade_l, "MIX ZERO: "+obs_z_mix], detalhado_rows)
                    st.success("Mix Zero registrado com sucesso!"); st.balloons()
