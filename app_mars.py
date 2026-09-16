import streamlit as st
import pandas as pd
import os
import unicodedata
import smtplib
import gspread
import re
import zipfile
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURAÇÃO VISUAL (CLEAN EXECUTIVO) ---
st.set_page_config(page_title="MARS - Torre de Controle com Markup", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F4F6F9; color: #1F2937; }
    div.stButton > button {
        height: 55px; font-size: 15px; font-weight: bold; border-radius: 8px;
        border: 2px solid #1E3A8A; color: #FFFFFF; background-color: #1E3A8A;
        margin-bottom: 8px; width: 100%;
    }
    div.stButton > button:hover { background-color: #059669; border-color: #059669; color: white; }
    .stSelectbox label, .stTextArea label { color: #1E3A8A !important; font-weight: bold; }
    h1, h2, h3 { color: #1E3A8A !important; }
    textarea { background-color: #FFFFFF !important; color: #1F2937 !important; }
    </style>
""", unsafe_allow_html=True)

# --- DEFINIÇÃO DOS TIMES DE E-MAILS ---
EMAILS_TIME_SP = [
    "caio.poli@minassal.com.br",
    "poli@minassal.com.br",
    "daniel.santini@minassal.com.br",
    "paulo.ferreira@minassal.com.br",
    "fabio.dalava@minassal.com.br",
    "benedito.bandola@minassal.com.br"
]

EMAILS_TIME_MG = [
    "caio.poli@minassal.com.br",
    "poli@minassal.com.br",
    "daniel.santini@minassal.com.br",
    "rubens.porfirio@minassal.com.br",
    "fabio.dalava@minassal.com.br",
    "benedito.bandola@minassal.com.br"
]

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
    if not os.path.exists(caminho_real):
        caminho_real = arquivo if os.path.exists(arquivo) else None
    if not caminho_real: return 0.0
    try:
        df_p = pd.read_csv(caminho_real, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
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
        aba_detalhe.append_rows(detalhado, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return False

@st.cache_data(ttl=60)
def carregar_historico_gerencial():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Torre_de_Controle_Mars")
        dados = spreadsheet.sheet1.get_all_records()
        return pd.DataFrame(dados)
    except:
        return pd.DataFrame()

# --- CARREGAR BASE DE VENDAS ---
@st.cache_data(ttl=300)
def carregar_dados():
    diretorio_atual = os.path.dirname(__file__) if '__file__' in locals() else "."
    df_v = pd.DataFrame()
    nome_zip = "vendas somente mars de 2026 ate 15 de setembro.zip"
    caminho_zip = os.path.join(diretorio_atual, nome_zip)
    if not os.path.exists(caminho_zip):
        caminho_zip = nome_zip if os.path.exists(nome_zip) else None

    try:
        if caminho_zip and os.path.exists(caminho_zip):
            with zipfile.ZipFile(caminho_zip, 'r') as z:
                nomes_internos = [name for name in z.namelist() if name.endswith(('.xlsx', '.xls', '.csv'))]
                if nomes_internos:
                    nome_interno = nomes_internos[0]
                    with z.open(nome_interno) as f_zip:
                        if nome_interno.endswith('.csv'):
                            df_v = pd.read_csv(f_zip, sep=';', encoding='latin1', low_memory=False)
                        else:
                            df_v = pd.read_excel(f_zip)
            df_v.columns = [c.strip().upper() for c in df_v.columns]
            if 'DATA' in df_v.columns:
                df_v['DATA'] = pd.to_datetime(df_v['DATA'], errors='coerce')
    except Exception as e:
        st.error(f"Erro ao carregar base do zip: {e}")
    return df_v

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
    "CAROLINA": ["SAO CARLOS", "ARARAQUARA", "MATAO"], 
    "SARUETE": ["SAO JOSE DO RIO PRETO", "MIRASSOL", "CATANDUVA"], 
    "MADALLA": ["CONSELHEIRO LAFAIETE", "GUARANI", "GUIDOVAL", "MURIAE", "MURIAÉ", "PIRAUBA", "PIRAÚBA", "RIO POMBA", "TOCANTINS", "UBA", "UBÁ", "VICOSA", "VIÇOSA", "VISCONDE DO RIO BRANCO"], 
    "FERNANDA": ["JUIZ DE FORA"]
}

def gerar_pdf_mars(promotor, loja, cidade, df_audit, df_faltantes, feedback):
    loja_limpa = re.sub(r'[^\w\s-]', '', loja).strip().replace(' ', '_')
    nome_arquivo = f"Oportunidades_{loja_limpa}.pdf"

    doc = SimpleDocTemplate(nome_arquivo, pagesize=landscape(A4), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    elementos, estilos = [], getSampleStyleSheet()
    
    style_celula = ParagraphStyle('EstiloCelula', parent=estilos['Normal'], fontSize=8.5, leading=10, textColor=colors.HexColor('#1F2937'), alignment=1)
    style_celula_esq = ParagraphStyle('EstiloCelulaEsq', parent=estilos['Normal'], fontSize=8.5, leading=10, textColor=colors.HexColor('#1F2937'), alignment=0)
    style_celula_cabecalho = ParagraphStyle('EstiloCelulaCab', parent=estilos['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName="Helvetica-Bold", alignment=1)
    style_obs_titulo = ParagraphStyle('ObsTitulo', parent=estilos['Normal'], fontSize=11, leading=13, textColor=colors.HexColor('#991B1B'), fontName="Helvetica-Bold")
    style_obs_texto = ParagraphStyle('ObsTexto', parent=estilos['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#1F2937'), fontName="Helvetica")

    dt_pdf = obter_horario_brasil()
    elementos.append(Paragraph("<b>RELATÓRIO DE OPORTUNIDADES E MARKUP MARS</b>", estilos['Title']))
    elementos.append(Paragraph(f"<b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade} | <b>PROMOTOR:</b> {promotor}", estilos['Normal']))
    elementos.append(Paragraph(f"<b>DATA/HORA:</b> {dt_pdf}", estilos['Normal']))
    elementos.append(Spacer(1, 10))

    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS, FALTA E MARKUP</b>", estilos['Heading3']))
        data_audit = [[
            Paragraph("<b>PRODUTO</b>", style_celula_cabecalho),
            Paragraph("<b>PREÇO RECOMENDADO</b>", style_celula_cabecalho),
            Paragraph("<b>PREÇO PAGO ÚLTIMO PEDIDO</b>", style_celula_cabecalho),
            Paragraph("<b>PREÇO DE GONDOLA</b>", style_celula_cabecalho),
            Paragraph("<b>MARKUP PRATICADO</b>", style_celula_cabecalho),
            Paragraph("<b>FALTA</b>", style_celula_cabecalho)
        ]]
        
        table_styles = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]

        for i, row in enumerate(df_audit.to_dict('records')):
            p_rec = converter_preco(row.get('SUGERIDO', 0.0))
            p_loja = float(row.get('PREÇO GÔNDOLA', 0.0))
            p_pago_val = row.get('PREÇO PAGO', 0.0)
            is_falta = row.get('FALTA NA LOJA?', False)
            
            p_custo_ult = float(p_pago_val) if isinstance(p_pago_val, (int, float)) else 0.0
            
            if is_falta or p_loja == 0.0:
                markup_txt = "<b><font color='#DC2626'>FALTA</font></b>"
            elif p_custo_ult > 0:
                markup_praticado = ((p_loja - p_custo_ult) / p_custo_ult) * 100 if p_loja > 0 else 0.0
                markup_recomendado = ((p_rec - p_custo_ult) / p_custo_ult) * 100 if p_rec > 0 else 0.0
                
                if markup_praticado > 200:
                    cor_loja = "#7C3AED"
                elif markup_praticado > markup_recomendado:
                    cor_loja = "#991B1B"
                else:
                    cor_loja = "#059669"
                    
                markup_txt = f"<b><font color='{cor_loja}'>{markup_praticado:.0f}%</font></b>"
            else:
                markup_txt = "<b>N/D</b>"

            pago_str = f"R$ {p_custo_ult:.2f}" if p_custo_ult > 0 else str(p_pago_val)

            if not is_falta and p_loja > 0 and p_rec > 0 and p_loja < (p_rec - 0.50):
                table_styles.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#FEF3C7')))
            
            data_audit.append([
                Paragraph(str(row.get('PRODUTO', '')), style_celula_esq),
                Paragraph(f"R$ {p_rec:.2f}", style_celula),
                Paragraph(pago_str, style_celula),
                Paragraph(f"R$ {p_loja:.2f}", style_celula),
                Paragraph(markup_txt, style_celula),
                Paragraph("SIM" if is_falta else "NÃO", style_celula)
            ])

        t1 = Table(data_audit, colWidths=[250, 105, 115, 105, 110, 50])
        t1.setStyle(TableStyle(table_styles))
        elementos.append(t1)

    if df_faltantes:
        elementos.append(Spacer(1, 10))
        elementos.append(Paragraph("<b>2. PRODUTO NÃO ENCONTRADO NA LOJA / HISTÓRICO</b>", estilos['Heading3']))
        
        data_f = [[
            Paragraph("<b>Código</b>", style_celula_cabecalho),
            Paragraph("<b>Produto</b>", style_celula_cabecalho),
            Paragraph("<b>Histórico</b>", style_celula_cabecalho)
        ]]
        for f in df_faltantes:
            data_f.append([
                Paragraph(str(f[0]), style_celula),
                Paragraph(str(f[1]), style_celula_esq),
                Paragraph(str(f[2]), style_celula)
            ])
            
        t2 = Table(data_f, colWidths=[70, 415, 250])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        elementos.append(t2)

    if feedback and feedback.strip():
        elementos.append(Spacer(1, 12))
        tabela_obs = Table([
            [Paragraph("<b>🗣️ OBSERVAÇÕES / FEEDBACK DO CLIENTE:</b>", style_obs_titulo)],
            [Paragraph(feedback, style_obs_texto)]
        ], colWidths=[735])
        tabela_obs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF3C7')),
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#D97706')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        elementos.append(tabela_obs)

    doc.build(elementos)
    return nome_arquivo

def enviar_email(assunto, pdf, lista_destinatarios):
    rem, sen = "beneditobandola@gmail.com", "kfih ccqx cskn oito"
    msg = MIMEMultipart()
    msg['From'] = rem
    msg['To'] = ", ".join(lista_destinatarios)
    msg['Subject'] = assunto
    
    corpo_html = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #1F2937;">
        <h2 style="color: #1E3A8A;">🐾 Relatório de Oportunidades & Markup - Mars</h2>
        <p>Segue em anexo o relatório detalhado da auditoria realizada em campo.</p>
        <hr style="border: none; border-top: 1px solid #E5E7EB;">
        <p style="font-size: 12px; color: #6B7280;">Mensagem automática gerada pela Torre de Controle Minassal.</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(corpo_html, 'html'))
    
    try:
        with open(pdf, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf))
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf))
            msg.attach(part)
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(rem, sen)
        s.sendmail(rem, lista_destinatarios, msg.as_string())
        s.quit()
        return True
    except:
        return False

# --- INTERFACE PRINCIPAL ---
st.markdown("<h1 style='text-align:center;'>🐾 SISTEMA DE OPORTUNIDADES & MARKUP MARS</h1>", unsafe_allow_html=True)

if 'user_mars' not in st.session_state:
    st.subheader("Selecione o seu nome ou acesse o painel gerencial:")
    nomes_promotores = list(ROTAS_MARS.keys())
    col1, col2 = st.columns(2)
    
    for i, nome in enumerate(nomes_promotores):
        col_atual = col1 if i % 2 == 0 else col2
        if col_atual.button(nome, use_container_width=True): 
            st.session_state.user_mars = nome
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("👑 ACESSO GESTOR (BENEDITO)", use_container_width=True):
        st.session_state.solicitou_senha = True
        st.rerun()

    if st.session_state.get('solicitou_senha', False):
        st.markdown("---")
        st.subheader("🔐 Área Restrita - Gestor")
        senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
        if st.button("Confirmar Senha"):
            if senha_digitada == "@Maiden01":
                st.session_state.user_mars = "BENEDITO"
                del st.session_state.solicitou_senha
                st.rerun()
            else:
                st.error("❌ Senha incorreta!")

else:
    promotor = st.session_state.user_mars

    # --- PAINEL EXCLUSIVO DO BENEDITO (GESTOR) COM FILTRO DO MÊS ---
    if promotor == "BENEDITO":
        st.sidebar.markdown("### 👑 Gestor: Benedito")
        if st.sidebar.button("Sair do Painel"):
            del st.session_state.user_mars
            st.rerun()

        st.markdown("## 📊 Painel Gerencial - Torre de Controle")
        st.markdown("Histórico de auditorias registradas no **mês atual**.")

        df_hist = carregar_historico_gerencial()
        if not df_hist.empty:
            if 'DATA/HORA' in df_hist.columns:
                df_hist['DATA_DT'] = pd.to_datetime(df_hist['DATA/HORA'], format='%d/%m/%Y %H:%M', errors='coerce')
                mes_atual = datetime.now().month
                ano_atual = datetime.now().year
                df_hist = df_hist[(df_hist['DATA_DT'].dt.month == mes_atual) & (df_hist['DATA_DT'].dt.year == ano_atual)]
                df_hist = df_hist.drop(columns=['DATA_DT'])

            if df_hist.empty:
                st.info("Nenhum relatório registrado na planilha de controle para este mês.")
            else:
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                st.success("✅ O sistema está registrando todas as pesquisas do mês com segurança.")
        else:
            st.info("Nenhum relatório registrado na planilha de controle ainda.")

    else:
        # --- FLUXO NORMAL DOS PROMOTORES COM BOTÕES DE ESCOLHA DE ENVIO ---
        df_vendas = carregar_dados()
        if df_vendas.empty:
            st.error("Aguardando carregamento da base do cubo de vendas...")
            if st.button("Voltar"):
                del st.session_state.user_mars
                st.rerun()
            st.stop()

        if promotor == "PAMELA":
            f_label, arq_precos = "POÇOS DE CALDAS", "MINEIROS PREÇOS MARS COMPLETO.csv"
        elif promotor in ["RODRIGO", "CAROLINA"]:
            f_label, arq_precos = "SÃO JOÃO DA BOA VISTA", "PAULISTINHAS_MARS_PRECO_ATUALIZADO.csv"
        elif promotor in ["SARUETE"]:
            f_label, arq_precos = "SÃO JOSÉ DO RIO PRETO", "PAULISTINHAS_MARS_PRECO_ATUALIZADO.csv"
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

        df_vendas['CIDADE_BUSCA'] = df_vendas['CIDADE'].apply(limpar_texto)
        df_f = df_vendas[df_vendas['CIDADE_BUSCA'].isin([limpar_texto(c) for c in ROTAS_MARS[promotor]])]
        
        loja = st.selectbox("🏪 Selecione a Loja:", ["-- Selecione --"] + sorted(df_f['CLIENTE NOME'].unique()))

        if loja != "-- Selecione --":
            v_loja = df_f[df_f['CLIENTE NOME'] == loja]
            cidade_cliente = str(v_loja.iloc[0]['CIDADE']).strip()

            comp_cli = set(v_loja['PRODUTO CODIGO'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().unique())
            
            dados_audit_view, prod_faltantes = [], []
            for c, n in PRODUTOS_FOCAIS.items():
                historico_item = v_loja[v_loja['PRODUTO CODIGO'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == c].copy()
                
                preco_ultimo_pedido = 0.0
                tem_venda = False
                
                if not historico_item.empty and 'DATA' in historico_item.columns:
                    historico_item['DATA_DT'] = pd.to_datetime(historico_item['DATA'], errors='coerce')
                    historico_item = historico_item.sort_values(by='DATA_DT', ascending=False)
                    ultima_linha = historico_item.iloc[0]
                    
                    dt_ult = ultima_linha['DATA_DT']
                    qtd_ult = ultima_linha.get('TOTAL QTD', 0)
                    val_ult = ultima_linha.get('TOTAL VALOR', 0)
                    op_ult = str(ultima_linha.get('OPERACAO', 'VENDA')).strip()
                    
                    if pd.notna(qtd_ult) and qtd_ult > 0:
                        preco_ultimo_pedido = val_ult / qtd_ult
                        tem_venda = True

                    info_ultima_compra = f" (Última: {dt_ult.strftime('%d/%m/%Y') if pd.notna(dt_ult) else 'Desconhecida'} - {op_ult} - Qtd: {int(qtd_ult) if pd.notna(qtd_ult) else 0})"
                else:
                    info_ultima_compra = ""

                produto_nome_detalhado = f"{n}{info_ultima_compra}"
                preco_pago_exibicao = round(preco_ultimo_pedido, 2) if tem_venda else "Não foram encontradas vendas este ano"

                if c in comp_cli:
                    dados_audit_view.append({
                        "FALTA NA LOJA?": False, "CÓDIGO": c, "PRODUTO": produto_nome_detalhado, 
                        "PREÇO PAGO": preco_pago_exibicao, 
                        "PREÇO GÔNDOLA": 0.0, "SUGERIDO": f"R$ {buscar_preco_na_tabela(arq_precos, c):.2f}"
                    })
                else:
                    if not historico_item.empty:
                        status_hist = f"PRODUTO NÃO ENCONTRADO NA LOJA{info_ultima_compra}"
                    else:
                        status_hist = "PRODUTO NÃO ENCONTRADO NA LOJA (NÃO COMPRADO ESTE ANO)"
                    prod_faltantes.append([c, produto_nome_detalhado, status_hist])
            
            if dados_audit_view:
                df_para_editar = pd.DataFrame(dados_audit_view)
                df_para_exibir_tela = df_para_editar.drop(columns=["PREÇO PAGO"])
                
                df_edit_tela = st.data_editor(df_para_exibir_tela, use_container_width=True, hide_index=True, disabled=["CÓDIGO", "PRODUTO", "SUGERIDO"])
                
                df_edit = df_edit_tela.copy()
                df_edit["PREÇO PAGO"] = df_para_editar["PREÇO PAGO"].values
                
                st.markdown("### 📊 Auditoria de Markup (Recomendado vs Loja)")
                
                preview_markup = []
                for r in df_edit.to_dict('records'):
                    p_sug = converter_preco(r['SUGERIDO'])
                    p_loj = float(r['PREÇO GÔNDOLA'])
                    p_pago_item = r['PREÇO PAGO']
                    is_falta_tela = r['FALTA NA LOJA?']
                    
                    custo_base = float(p_pago_item) if isinstance(p_pago_item, (int, float)) else 0.0
                    
                    if is_falta_tela or p_loj == 0.0:
                        loja_str = "❌ FALTA"
                        status_markup = "🚨 Produto em Falta na Loja"
                    elif custo_base > 0:
                        mk_rec = ((p_sug - custo_base) / custo_base) * 100 if p_sug > 0 else 0.0
                        mk_loj = ((p_loj - custo_base) / custo_base) * 100 if p_loj > 0 else 0.0
                        
                        if mk_loj > 200:
                            status_markup = "🟣 Markup Elevado (> 200%)"
                        elif mk_loj > mk_rec:
                            status_markup = "⚠️ Acima do Recomendado"
                        else:
                            status_markup = "✅ Adequado (Igual ou Menor)"
                            
                        loja_str = f"R$ {p_loj:.2f} ({mk_loj:.1f}%)"
                    else:
                        loja_str = f"R$ {p_loj:.2f}"
                        status_markup = "Sem base de custo"

                    preview_markup.append({
                        "Produto": r['PRODUTO'],
                        "Preço Gôndola": loja_str,
                        "Status / Avaliação": status_markup
                    })

                df_prev = pd.DataFrame(preview_markup)
                st.dataframe(df_prev, use_container_width=True, hide_index=True)

                obs_text = st.text_area("🗣️ Observações:")
                
                # --- BOTÕES DE ESCOLHA DE DESTINO PARA OS PROMOTORES ---
                st.markdown("---")
                st.markdown("### 📤 Enviar Relatório para:")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🚀 ENVIAR PARA TIME SP", use_container_width=True):
                        tem_preco_zerado = any(float(r['PREÇO GÔNDOLA']) == 0.0 and not r['FALTA NA LOJA?'] for r in df_edit.to_dict('records'))
                        if tem_preco_zerado:
                            st.error("🚨 Há produtos com Preço Gôndola zerado sem estar marcado como falta.")
                        else:
                            horario_ref = obter_horario_brasil()
                            detalhado_rows = []
                            for r in df_edit.to_dict('records'):
                                status_val = "FALTA" if r['FALTA NA LOJA?'] or float(r['PREÇO GÔNDOLA']) == 0 else "TEM"
                                detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, r['CÓDIGO'], r['PRODUTO'], status_val, float(r['PREÇO GÔNDOLA']), converter_preco(r['SUGERIDO'])])
                            for f in prod_faltantes:
                                detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0])
                            
                            pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, df_edit, prod_faltantes, obs_text)
                            if enviar_email(f"🐾 OPORTUNIDADE & MARKUP (SP): {loja}", pdf_file, EMAILS_TIME_SP):
                                salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, obs_text], detalhado_rows)
                                st.success("Enviado com sucesso para o Time SP!"); st.balloons()

                with col2:
                    if st.button("🚀 ENVIAR PARA TIME MG", use_container_width=True):
                        tem_preco_zerado = any(float(r['PREÇO GÔNDOLA']) == 0.0 and not r['FALTA NA LOJA?'] for r in df_edit.to_dict('records'))
                        if tem_preco_zerado:
                            st.error("🚨 Há produtos com Preço Gôndola zerado sem estar marcado como falta.")
                        else:
                            horario_ref = obter_horario_brasil()
                            detalhado_rows = []
                            for r in df_edit.to_dict('records'):
                                status_val = "FALTA" if r['FALTA NA LOJA?'] or float(r['PREÇO GÔNDOLA']) == 0 else "TEM"
                                detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, r['CÓDIGO'], r['PRODUTO'], status_val, float(r['PREÇO GÔNDOLA']), converter_preco(r['SUGERIDO'])])
                            for f in prod_faltantes:
                                detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0])
                            
                            pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, df_edit, prod_faltantes, obs_text)
                            if enviar_email(f"🐾 OPORTUNIDADE & MARKUP (MG): {loja}", pdf_file, EMAILS_TIME_MG):
                                salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, obs_text], detalhado_rows)
                                st.success("Enviado com sucesso para o Time MG!"); st.balloons()

                with col3:
                    if st.button("🧪 TESTAR (SÓ PARA BENEDITO)", use_container_width=True):
                        tem_preco_zerado = any(float(r['PREÇO GÔNDOLA']) == 0.0 and not r['FALTA NA LOJA?'] for r in df_edit.to_dict('records'))
                        if tem_preco_zerado:
                            st.error("🚨 Há produtos com Preço Gôndola zerado sem estar marcado como falta.")
                        else:
                            horario_ref = obter_horario_brasil()
                            pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, df_edit, prod_faltantes, obs_text)
                            if enviar_email(f"🧪 [TESTE] OPORTUNIDADE & MARKUP: {loja}", pdf_file, ["benedito.bandola@minassal.com.br"]):
                                st.success("Enviado com sucesso apenas para o seu e-mail de teste!"); st.balloons()
            else:
                st.warning("🚨 Mix Zero!")
                obs_z_mix = st.text_area("🗣️ Justificativa Mix Zero:")
                
                col_mz1, col_mz2 = st.columns(2)
                with col_mz1:
                    if st.button("🚨 ENVIAR MIX ZERO (SP)", use_container_width=True):
                        horario_ref = obter_horario_brasil()
                        detalhado_rows = [[horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0] for f in prod_faltantes]
                        pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, pd.DataFrame(), prod_faltantes, obs_z_mix)
                        if enviar_email(f"🚨 MIX ZERO (SP): {loja}", pdf_file, EMAILS_TIME_SP):
                            salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, "MIX ZERO: "+obs_z_mix], detalhado_rows)
                            st.success("Mix Zero enviado para o Time SP!"); st.balloons()
                with col_mz2:
                    if st.button("🚨 ENVIAR MIX ZERO (MG)", use_container_width=True):
                        horario_ref = obter_horario_brasil()
                        detalhado_rows = [[horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0] for f in prod_faltantes]
                        pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, pd.DataFrame(), prod_faltantes, obs_z_mix)
                        if enviar_email(f"🚨 MIX ZERO (MG): {loja}", pdf_file, EMAILS_TIME_MG):
                            salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, "MIX ZERO: "+obs_z_mix], detalhado_rows)
                            st.success("Mix Zero enviado para o Time MG!"); st.balloons()

        st.markdown("---")
        st.markdown("### 📋 Histórico de Compras da Loja - Produtos Mars (Este Ano)")
        
        vendas_mars_loja = df_vendas[
            (df_vendas['CLIENTE NOME'] == loja) & 
            (df_vendas['FABRICANTE NOME'].astype(str).str.upper().str.contains("MARS", na=False))
        ].copy()
        
        if not vendas_mars_loja.empty:
            total_compras = len(vendas_mars_loja)
            soma_qtd = vendas_mars_loja['TOTAL QTD'].sum() if 'TOTAL QTD' in vendas_mars_loja.columns else 0
            
            st.info(f"📊 **Resumo Anual:** {total_compras} registros de pedidos encontrados | **Soma Total de Quantidade Comprada:** {soma_qtd:,.0f} unidades")

            if 'DATA' in vendas_mars_loja.columns:
                vendas_mars_loja['DATA_DT'] = pd.to_datetime(vendas_mars_loja['DATA'], errors='coerce')
                vendas_mars_loja['DATA_FORMATADA'] = vendas_mars_loja['DATA_DT'].dt.strftime('%d/%m/%Y')
            else:
                vendas_mars_loja['DATA_DT'] = pd.NaT
                vendas_mars_loja['DATA_FORMATADA'] = ""
                
            tabela_historico = vendas_mars_loja[['DATA_DT', 'DATA_FORMATADA', 'PRODUTO NOME', 'OPERACAO', 'TOTAL QTD']].dropna(subset=['PRODUTO NOME'])
            tabela_historico.columns = ['DATA_SORT', 'Data do Pedido', 'Produto Mars', 'Tipo de Operação', 'Qtd']
            tabela_historico = tabela_historico.sort_values(by='DATA_SORT', ascending=False)
            tabela_historico = tabela_historico.drop(columns=['DATA_SORT'])
            
            def colorir_operacao(val):
                v = str(val).upper()
                if "BONIF" in v:
                    return 'background-color: #FEF3C7; color: #92400E; font-weight: bold;'
                elif "DEVOL" in v:
                    return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
                return ''

            st.dataframe(tabela_historico.style.map(colorir_operacao, subset=['Tipo de Operação']), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de compra de produtos Mars encontrado para esta loja no período.")
