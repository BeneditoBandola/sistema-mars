import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- CONFIGURAÇÕES DA MARS ---
PROMOTORES = ["PAMELA", "GABRIEL", "MARCOS", "ANA", "BRUNO"]
LOJAS = ["VILA NOVA", "SÃO JOSÉ", "CENTRO", "ZONA SUL", "SHOPPING"]
PRODUTOS_MARS = ["M&M's 148g", "Twix XB 80g", "Snickers 45g", "Skittles 38g", "Pedigree Sachê 100g"]

# Preços sugeridos para cálculo de status
PRECOS_RECOMENDADOS = {
    "M&M's 148g": 12.90,
    "Twix XB 80g": 5.50,
    "Snickers 45g": 3.90,
    "Skittles 38g": 4.20,
    "Pedigree Sachê 100g": 2.90
}

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Puxando dos Secrets do Streamlit
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # NOME DA SUA PLANILHA EXATAMENTE COMO ESTÁ NO DRIVE
    return client.open("Torre_de_Controle_Mars").sheet1

# --- FUNÇÃO PARA GERAR O PDF ---
def gerar_pdf(dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título
    elements.append(Paragraph(f"Relatório de Merchandising - Mars", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Cabeçalho do Relatório
    elements.append(Paragraph(f"<b>Promotor:</b> {dados['Promotor']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Loja:</b> {dados['Loja']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data:</b> {dados['Data']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Tabela de Preços e Status
    elements.append(Paragraph("<b>Monitoramento de Preços:</b>", styles['Heading2']))
    
    # Montando os dados da tabela
    tabela_dados = [["Produto", "Preço Atual", "Rec. Mars", "Status"]]
    for p in PRODUTOS_MARS:
        p_atual = dados.get(f"preco_{p}", 0.0)
        p_rec = PRECOS_RECOMENDADOS.get(p, 0.0)
        
        # Lógica do Status: Se preço atual <= recomendado, está dentro.
        if p_atual == 0:
            status = "N/I"
        elif p_atual <= p_rec:
            status = "DENTRO"
        else:
            status = "FORA"
            
        tabela_dados.append([p, f"R$ {p_atual:.2f}", f"R$ {p_rec:.2f}", status])

    t = Table(tabela_dados)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Campo de Observações
    elements.append(Paragraph(f"<b>Observações:</b> {dados['Observacao']}", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- INTERFACE DO APP (STREAMLIT) ---
st.set_page_config(page_title="Sistema Mars - Minassal", page_icon="🍫")
st.title("🍫 Monitoramento Mars - Minassal")

with st.form("form_pesquisa"):
    col1, col2 = st.columns(2)
    with col1:
        promotor = st.selectbox("Selecione o Promotor", PROMOTORES)
    with col2:
        loja = st.selectbox("Selecione a Loja", LOJAS)

    st.subheader("Pesquisa de Preços")
    precos_capturados = {}
    for p in PRODUTOS_MARS:
        precos_capturados[f"preco_{p}"] = st.number_input(f"Preço: {p}", min_value=0.0, step=0.01)

    obs = st.text_area("Observações / Ocorrências")
    
    submit = st.form_submit_button("Finalizar e Enviar")

if submit:
    try:
        sheet = conectar_planilha()
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Preparar linha para a planilha (Google Sheets)
        linha = [data_hoje, promotor, loja] + list(precos_capturados.values()) + [obs]
        sheet.append_row(linha)
        
        # Preparar dados para o PDF
        dados_relatorio = {
            "Promotor": promotor,
            "Loja": loja,
            "Data": data_hoje,
            "Observacao": obs
        }
        dados_relatorio.update(precos_capturados)

        pdf = gerar_pdf(dados_relatorio)
        
        st.success("✅ Dados enviados para a planilha com sucesso!")
        
        st.download_button(
            label="📩 Baixar Relatório em PDF",
            data=pdf,
            file_name=f"Relatorio_{promotor}_{loja}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
