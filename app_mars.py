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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURAÇÃO VISUAL (CLEAN EXECUTIVO) ---
st.set_page_config(page_title="MARS - Torre de Controle", page_icon="🐾", layout="wide")

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

# --- CARREGAR BASES DE VENDAS ---
@st.cache_data(ttl=300)
def carregar_dados():
    diretorio_atual = os.path.dirname(__file__) if '__file__' in locals() else "."
    df_v = pd.DataFrame()
    try:
        caminho_v = os.path.join(diretorio_atual, "VENDAS_ATUALIZADAS_2026.zip")
        if not os.path.exists(caminho_v): caminho_v = "VENDAS_ATUALIZADAS_2026.zip"
        df_v = pd.read_csv(caminho_v, sep=';', encoding='utf-8-sig', compression='zip')
        df_v.columns = [c.strip().upper() for c in df_v.columns]
        if 'DATA' in df_v.columns:
            df_v['DATA'] = pd.to_datetime(df_v['DATA'], errors='coerce')
    except Exception as e:
        st.error(f"Erro ao carregar vendas: {e}")
    return df_v

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

# --- ROTAS (Lucivania removida) ---
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

    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos, estilos = [], getSampleStyleSheet()
    
    style_celula = ParagraphStyle('EstiloCelula', parent=estilos['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1F2937'))
    style_celula_cabecalho = ParagraphStyle('EstiloCelulaCab', parent=estilos['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName="Helvetica-Bold")

    dt_pdf = obter_horario_brasil()
    elementos.append(Paragraph("<b>RELATÓRIO DE OPORTUNIDADES MARS</b>", estilos['Title']))
    elementos.append(Paragraph(f"<b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade} | <b>PROMOTOR:</b> {promotor}", estilos['Normal']))
    elementos.append(Paragraph(f"<b>DATA/HORA:</b> {dt_pdf}", estilos['Normal']))
    elementos.append(Spacer(1, 15))

    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS & OPORTUNIDADES</b>", estilos['Heading3']))
        data_audit = [[
            Paragraph("<b>PRODUTO</b>", style_celula_cabecalho),
            Paragraph("<b>REC. MARS</b>", style_celula_cabecalho),
            Paragraph("<b>PREÇO LOJA</b>", style_celula_cabecalho),
            Paragraph("<b>SITUAÇÃO</b>", style_celula_cabecalho),
            Paragraph("<b>FALTA?</b>", style_celula_cabecalho)
        ]]
        
        for i, row in enumerate(df_audit.to_dict('records')):
            p_rec = converter_preco(row.get('SUGERIDO', 0.0))
            p_loja = float(row.get('PREÇO GÔNDOLA', 0.0))
            
            if p_loja == 0 or row.get('FALTA NA LOJA?'):
                sit_html = "<b><font color='red'>FALTA</font></b>"
            else:
                dif = ((p_loja - p_rec) / p_rec) * 100
                if p_loja > (p_rec + 0.01):
                    sit_html = f"<b><font color='red'>ACIMA (+{dif:.1f}%)</font></b>"
                else:
                    sit_html = f"<b><font color='green'>CORRETO ({dif:.1f}%)</font></b>"
            
            data_audit.append([
                Paragraph(str(row.get('PRODUTO', '')), style_celula),
                Paragraph(f"R$ {p_rec:.2f}", style_celula),
                Paragraph(f"R$ {p_loja:.2f}", style_celula),
                Paragraph(sit_html, style_celula),
                Paragraph("SIM" if row.get('FALTA NA LOJA?') else "NÃO", style_celula)
            ])

        t1 = Table(data_audit, colWidths=[230, 65, 65, 95, 45])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        elementos.append(t1)

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
            Paragraph(str(f[1]), style_celula),
            Paragraph(str(f[2]), style_celula)
        ])
        
    t2 = Table(data_f, colWidths=[60, 260, 180])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    elementos.append(t2)

    if feedback: 
        elementos.append(Spacer(1, 10))
        elementos.append(Paragraph(f"<b>OBS:</b> {feedback}", estilos['Normal']))

    doc.build(elementos)
    return nome_arquivo

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

if 'user_mars' not in st.session_state:
    st.subheader("Selecione o seu nome:")
    
    # Exibir botões em 2 colunas para otimizar espaço no celular
    nomes_promotores = list(ROTAS_MARS.keys())
    col1, col2 = st.columns(2)
    
    for i, nome in enumerate(nomes_promotores):
        col_atual = col1 if i % 2 == 0 else col2
        if col_atual.button(nome, use_container_width=True): 
            st.session_state.user_mars = nome
            st.rerun()
else:
    df_vendas = carregar_dados()
    if df_vendas.empty:
        st.error("Aguardando carregamento da base de vendas...")
        if st.button("Voltar"):
            del st.session_state.user_mars
            st.rerun()
        st.stop()

    promotor = st.session_state.user_mars
    
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
            
            info_ultima_compra = ""
            if not historico_item.empty and 'DATA' in historico_item.columns:
                historico_item['DATA_DT'] = pd.to_datetime(historico_item['DATA'], errors='coerce')
                idx_mais_recente = historico_item['DATA_DT'].idxmax()
                if pd.notna(idx_mais_recente):
                    ultima_linha = historico_item.loc[idx_mais_recente]
                    dt_ult = ultima_linha['DATA_DT']
                    qtd_ult = ultima_linha.get('TOTAL QTD', 0)
                    op_ult = str(ultima_linha.get('OPERACAO', 'VENDA')).strip()
                    if pd.notna(dt_ult):
                        info_ultima_compra = f" (Última: {dt_ult.strftime('%d/%m/%Y')} - {op_ult} - Qtd: {int(qtd_ult) if pd.notna(qtd_ult) else 0})"

            produto_nome_detalhado = f"{n}{info_ultima_compra}"

            if c in comp_cli:
                dados_audit_view.append({
                    "FALTA NA LOJA?": False, "CÓDIGO": c, "PRODUTO": produto_nome_detalhado, 
                    "PREÇO GÔNDOLA": 0.0, "SUGERIDO": f"R$ {buscar_preco_na_tabela(arq_precos, c):.2f}"
                })
            else:
                if not historico_item.empty:
                    status_hist = f"PRODUTO NÃO ENCONTRADO NA LOJA{info_ultima_compra}"
                else:
                    status_hist = "PRODUTO NÃO ENCONTRADO NA LOJA (NÃO COMPRADO ESTE ANO)"
                prod_faltantes.append([c, produto_nome_detalhado, status_hist])
        
        if dados_audit_view:
            df_edit = st.data_editor(pd.DataFrame(dados_audit_view), use_container_width=True, hide_index=True, disabled=["CÓDIGO", "PRODUTO", "SUGERIDO"])
            obs_text = st.text_area("🗣️ Observações:")
            if st.button("🚀 ENVIAR RELATÓRIO"):
                horario_ref = obter_horario_brasil()
                detalhado_rows = []
                for r in df_edit.to_dict('records'):
                    status_val = "FALTA" if r['FALTA NA LOJA?'] or float(r['PREÇO GÔNDOLA']) == 0 else "TEM"
                    p_sugerido_limpo = converter_preco(r['SUGERIDO'])
                    detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, r['CÓDIGO'], r['PRODUTO'], status_val, float(r['PREÇO GÔNDOLA']), p_sugerido_limpo])
                for f in prod_faltantes:
                    detalhado_rows.append([horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0])
                
                pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, df_edit, prod_faltantes, obs_text)
                if enviar_email(f"🐾 OPORTUNIDADE: {loja}", pdf_file):
                    salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, obs_text], detalhado_rows)
                    st.success("Enviado com sucesso!"); st.balloons()
        else:
            st.warning("🚨 Mix Zero!")
            obs_z_mix = st.text_area("🗣️ Justificativa Mix Zero:")
            if st.button("🚨 ENVIAR MIX ZERO"):
                horario_ref = obter_horario_brasil()
                detalhado_rows = [[horario_ref, promotor, loja, cidade_cliente, f[0], f[1], f[2], 0.0, 0.0] for f in prod_faltantes]
                pdf_file = gerar_pdf_mars(promotor, loja, cidade_cliente, pd.DataFrame(), prod_faltantes, obs_z_mix)
                if enviar_email(f"🚨 MIX ZERO: {loja}", pdf_file):
                    salvar_nas_planilhas([horario_ref, promotor, loja, cidade_cliente, "MIX ZERO: "+obs_z_mix], detalhado_rows)
                    st.success("Mix Zero registrado com sucesso!"); st.balloons()

        # --- HISTÓRICO DE COMPRAS DA MARS NO RODAPÉ ---
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

            st.dataframe(tabela_historico.style.applymap(colorir_operacao, subset=['Tipo de Operação']), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de compra de produtos Mars encontrado para esta loja no período.")
