import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os
import json
import base64
import re
import time
from datetime import datetime, date, timedelta

# --- 1. CONFIGURAÇÕES E CONSTANTES ---
st.set_page_config(page_title="Minassal Performance V10.8", layout="wide", page_icon="🐾")

CONFIG_FILE = "config_metas_minassal.json"
PASTA_FOTOS = r'C:\Users\Benedito\OneDrive - Minassal\Área de Trabalho\TODOS OS MEUS SCRIPTS\AREA DE LEITURAS\fotos promotores'

DATA_INICIO_P2 = date(2026, 1, 25)
DATA_FIM_P2 = date(2026, 2, 21)
FERIADOS_P2 = [date(2026, 2, 16), date(2026, 2, 17)]

FILIAIS = [
    "Minassal Ltda - Pocos de Caldas", 
    "Minassal Ltda - Sao Joao da Boa Vista",
    "Minassal Ltda - Sao Jose do Rio Preto", 
    "Minassal Ltda - Juiz de Fora"
]

ITENS_P = ["Small Bags", "Ponto Extra de Sachês/Petiscos"]
ITENS_S = ["Combos Virtuais Sachês (KiteKat, Champ, Optimum)", "Reset Whiskas Sachês", "Combos Virtuais Petiscos"]
TODOS_ITENS = ITENS_P + ITENS_S

# ADICIONADO RIO POMBA PARA MADALLA
ROTAS_PROMOTORES_MAPA = {
    "Pamela": ["POCOS DE CALDAS", "POÇOS DE CALDAS", "ANDRADAS", "VARGINHA", "TRES CORACOES", "TRÊS CORAÇÕES", "TRES PONTAS", "TRÊS PONTAS", "ITAJUBA", "ITAJUBÁ", "POUSO ALEGRE"],
    "Fernanda": ["JUIZ DE FORA", "JUIZ DE FORA/MG"],
    "Madalla": ["TOCANTINS", "UBA", "UBÁ", "RIO POMBA"]
}

# --- LISTA MESTRA TOP REDES ---
TOP_40_REDES_DATA = [
    ("53869565000176", "Juiz de Fora", "BIGPETS BRASIL LTDA"), ("01986278000142", "Juiz de Fora", "BARBARA FELIPPE COMERCIAL LTDA"),
    ("09412225000120", "Juiz de Fora", "A F MARTINS COMERCIO DE PET SHOP LTDA"), ("32623953000100", "Juiz de Fora", "RACOES RIO BRANCO LTDA"),
    ("68546597000108", "Juiz de Fora", "PURIMAX COMERCIO DE RACOES LTDA"), ("57235001000132", "Juiz de Fora", "RODRIGO CASTRO FRIZZERO AGROPECUARIA LTDA"),
    ("31635090000110", "Juiz de Fora", "AGROPECUARIA RIANELLI E BONOTO LTDA"), ("17678897000100", "Juiz de Fora", "AGROTELA COMERCIAL LTDA"),
    ("21908494000187", "Juiz de Fora", "VETERINARIA MENDES ANDRADE LTDA"), ("43236258000102", "Juiz de Fora", "AGROPECUARIA E ELETRICA ROCHEDO COMERCIO LTDA"),
    ("02819934000185", "Pocos de Caldas", "DAVIDBEL ARTIGOS PARA ANIMAIS LTDA"), ("00842760000146", "Pocos de Caldas", "UNIAO AGROPECUARIA LTDA-CASA DO CRIADOR"),
    ("00423316000196", "Pocos de Caldas", "CREMILSON HENRIQUE FREITAS"), ("04162718000135", "Pocos de Caldas", "ADEMIR APARECIDO CONSTANTINO"),
    ("18946575000167", "Pocos de Caldas", "E-PET LTDA"), ("14526185000187", "Pocos de Caldas", "MARCOS CONSENTINO"),
    ("42921080000168", "Pocos de Caldas", "AGRO SANTO ANTONIO LTDA"), ("15865670000148", "Pocos de Caldas", "AGROPECUARIA SANTA EDWIGES COMERCIAL LTDA"),
    ("04795218000130", "Pocos de Caldas", "COMERCIAL MARITAN YANO LTDA"), ("47214882000151", "Pocos de Caldas", "ARMAZEM DAS RACOES LTDA"),
    ("10221584000189", "Sao Joao da Boa Vista", "MORAES & SILVA RACOES LTDA"), ("36667802000105", "Sao Joao da Boa Vista", "EES PET SHOP COM DE PRODS E ANIMAIS DE ESTIM LTDA"),
    ("02457700000135", "Sao Joao da Boa Vista", "CORRAL COMERCIO DE RACOES LTDA EPP"), ("13062215000189", "Sao Joao da Boa Vista", "AMOPETS LTDA"),
    ("30872481000196", "Sao Joao da Boa Vista", "CENTER SHOP DO ANIMAL LTDA"), ("05095810000192", "Sao Joao da Boa Vista", "ABBADE & REIS LTDA"),
    ("27543687000168", "Sao Joao da Boa Vista", "CASA DO BOI COMERCIAL DE PRODUTOS VETERINARIOS LTDA"), ("58913834000178", "Sao Joao da Boa Vista", "AGROMIL PRODUTOS VETERINARIOS LTDA"),
    ("07831582000105", "Sao Joao da Boa Vista", "BIVETER COMERCIO DE PRODUTOS AGROPECUARIOS LTDA"), ("03022826000140", "Sao Joao da Boa Vista", "AGRO CORBI SEMENTES RACOES LTDA"),
    ("26591656000110", "Sao Jose do Rio Preto", "A C DA SILVA RUIZ & CIA LTDA"), ("23124236000135", "Sao Jose do Rio Preto", "GROUP FUKUJU LTDA"),
    ("20809189000175", "Sao Jose do Rio Preto", "FRS FERREIRA RACOES"), ("31008497000118", "Sao Jose do Rio Preto", "NUTRIAL PET CENTER COMERCIO DE RACOES LTDA"),
    ("21711126000144", "Sao Jose do Rio Preto", "B H LISBOA DA ROCHA LTDA"), ("01781155000175", "Sao Jose do Rio Preto", "FAFER COM PROD P ANIMAIS E AVES LTDA"),
    ("39412328000150", "Sao Jose do Rio Preto", "AGROPET RACOES Rio PRETO LTDA"), ("14921961000143", "Sao Jose do Rio Preto", "PET CENTER REGISSOL LTDA"),
    ("10370253000100", "Sao Jose do Rio Preto", "DPET & UD COMERCIAL LTDA ME"), ("43602619000189", "Sao Jose do Rio Preto", "FRANCIELE DE OLIVEIRA TEIXEIRA 38870462854")
]

# --- 2. FUNÇÕES DE BACKEND ---
@st.cache_data
def carregar_dados(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
        if len(df.columns) < 2:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8')
        df.columns = df.columns.str.strip().str.title()
        mapa = {'Filial': 'Distribuidor', 'Promotor': 'Usuario', 'Pergunta': 'Item', 'Resposta': 'Status', 'Question': 'Item', 'Answer': 'Status', 'User': 'Usuario'}
        df.rename(columns=mapa, inplace=True)
        if 'Item' in df.columns:
            df['Item'] = df['Item'].replace({'Rebaixa Whiskas sache': 'Reset Whiskas Sachês', 'Reset Whiskas Sache': 'Reset Whiskas Sachês', 'rebaixa whiskas sache': 'Reset Whiskas Sachês'})
        return df
    except Exception as e:
        st.error(f"Erro ao ler CSV: {e}")
        return None

def limpar_cnpj(v):
    if pd.isna(v): return ""
    return re.sub(r'\D', '', str(v).upper().replace("CNPJ", "")).zfill(14)

def calcular_dias_uteis_restantes():
    hoje = date.today()
    if hoje < DATA_INICIO_P2: data_ref = DATA_INICIO_P2
    elif hoje > DATA_FIM_P2: return 0
    else: data_ref = hoje
    dias = 0; c = data_ref
    while c <= DATA_FIM_P2:
        if c.weekday() < 5 and c not in FERIADOS_P2: dias += 1
        c += timedelta(days=1)
    return dias

def carregar_configuracoes():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("metas", {})
        except: return {}
    return {}

def salvar_configuracoes(metas):
    try:
        dados_atuais = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: dados_atuais = json.load(f)
            except: pass
        dados_atuais["metas"] = metas
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(dados_atuais, f, indent=4)
    except Exception as e: st.error(f"Erro ao salvar: {e}")

def obter_foto_promotor(nome):
    if not os.path.exists(PASTA_FOTOS): return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    if not isinstance(nome, str): return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    nome_limpo = nome.strip()
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
        teste = os.path.join(PASTA_FOTOS, nome_limpo + ext)
        if os.path.exists(teste): return Image.open(teste)
    return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"

# --- 3. ESTILOS CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #e2e8f0; }
    [data-testid="stHeader"] { background-color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #cbd5e1; }
    h1, h2, h3, h4, p, label, strong, b { color: #000000 !important; font-family: 'Segoe UI', sans-serif; }
    div[data-baseweb="select"] > div { background-color: #ffffff !important; color: #000000 !important; }
    .profile-card { background-color: white; padding: 20px; border-radius: 15px; text-align: center; border-top: 5px solid #2563eb; color: #000; }
    .item-box { background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #cbd5e1; margin-bottom: 10px; color: #000; }
    .pill-ok { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
    .pill-pend { background-color: #ffedd5; color: #9a3412; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
    .pill-zero { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
    .row-whiskas { display: flex; align-items: center; background: white; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 4px solid #8b5cf6; color: #000; }
    .num-whiskas { margin-left: auto; display: flex; gap: 8px; align-items: center; }
    .filial-header { background-color: #1e3a8a; color: white !important; padding: 10px 20px; border-radius: 10px 10px 0 0; margin-top: 20px; font-size: 18px; font-weight: bold; }
    .filial-stats { background-color: white; border: 1px solid #cbd5e1; border-top: none; padding: 15px; border-radius: 0 0 10px 10px; margin-bottom: 10px; display: flex; justify-content: space-around; }
    .stat-box { text-align: center; }
    .stat-label { font-size: 12px; color: #64748b; font-weight: bold; text-transform: uppercase; }
    .stat-value { font-size: 20px; font-weight: bold; color: #1e293b; }
    .promo-row { display: flex; align-items: center; background: white; padding: 8px; margin-bottom: 5px; border-radius: 8px; border: 1px solid #e2e8f0; color: #000; }
</style>
""", unsafe_allow_html=True)

# --- 4. INTERFACE PRINCIPAL ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2328/2328966.png", width=50)
    st.title("Minassal Pro")
    pagina = st.radio("Navegação:", [
        "👥 Painel Detalhado (Cards)", 
        "📊 Visão Geral (Gráficos)", 
        "📉 Análise Whiskas Sache", 
        "🎯 Metas por Item (Detelhado)", 
        "🏆 Ranking Consolidado (Geral)", 
        "📊 Aprovado e Pendente vs Meta",
        "📍 Leituras Clientes TOP REDES"
    ])
    st.markdown("---")
    st.header("📂 Arquivo")
    arquivo = st.file_uploader("Carregar CSV", type=["csv"])
    st.markdown("---")
    st.subheader("🎯 Metas")
    metas_dict = carregar_configuracoes()
    
    with st.expander("Editar Metas", expanded=False):
        filial_meta_sel = st.selectbox("Filial:", FILIAIS)
        metas_f = metas_dict.get(filial_meta_sel, {})
        with st.form("form_metas"):
            st.write(f"**Editando: {filial_meta_sel.split('-')[-1]}**")
            novas_metas = {}
            for item in TODOS_ITENS:
                key_unique = f"in_{filial_meta_sel}_{item}" 
                val = st.number_input(f"{item}", value=int(metas_f.get(item, 0)), min_value=0, step=1, key=key_unique)
                novas_metas[item] = val
            submitted = st.form_submit_button("💾 SALVAR METAS", type="primary")
            if submitted:
                metas_dict[filial_meta_sel] = novas_metas
                salvar_configuracoes(metas_dict)
                st.toast("✅ Metas salvas com sucesso!")
                time.sleep(0.5)
                st.rerun()

if arquivo:
    df = carregar_dados(arquivo)
    if df is not None:
        col_filial, col_promotor, col_item, col_status = 'Distribuidor', 'Usuario', 'Item', 'Status'
        df[col_status] = df[col_status].fillna("")
        
        if pagina == "👥 Painel Detalhado (Cards)":
            c1, c2 = st.columns([3,1])
            c1.markdown("## 🚀 Painel de Execução")
            c2.markdown(f"**Dias Úteis Restantes: {calcular_dias_uteis_restantes()}**")
            filial_sel = st.selectbox("Selecione a Filial:", FILIAIS)
            st.markdown("---")
            df_f = df[df[col_filial].str.contains(filial_sel.split('-')[-1].strip(), case=False, na=False)]
            metas_f = metas_dict.get(filial_sel, {})
            tot_apr = len(df_f[df_f[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)])
            tot_pen = len(df_f[df_f[col_status].str.contains('Pendente', case=False, na=False)])
            meta_tot = sum(metas_f.values())
            falta = max(0, meta_tot - tot_apr)
            k1, k2, k3, k4 = st.columns(4)
            def kpi(col, lbl, val, color="#3b82f6"):
                col.markdown(f"<div style='background:white;padding:15px;border-radius:10px;border-bottom:4px solid {color};text-align:center;'><div>{lbl}</div><div style='font-size:24px;font-weight:bold;color:{color}'>{val}</div></div>", unsafe_allow_html=True)
            kpi(k1, "Meta Filial", meta_tot); kpi(k2, "Realizado", tot_apr, "#16a34a"); kpi(k3, "Pendente", tot_pen, "#d97706"); kpi(k4, "Falta Equipe", falta, "#dc2626")
            resumo_dados = []
            falta_item = {}
            for it in TODOS_ITENS:
                m = metas_f.get(it, 0)
                r = len(df_f[(df_f[col_item]==it) & (df_f[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False))])
                p = len(df_f[(df_f[col_item]==it) & (df_f[col_status].str.contains('Pendente', case=False, na=False))])
                f_val = max(0, m - r)
                falta_item[it] = f_val
                resumo_dados.append({"Item": it, "Meta": m, "Realizado (Apr)": r, "Pendente": p, "Falta": f_val})
            st.dataframe(pd.DataFrame(resumo_dados), use_container_width=True, hide_index=True)
            st.markdown("---")
            promotores = df_f[col_promotor].unique()
            for promotor in promotores:
                df_p = df_f[df_f[col_promotor] == promotor]
                col_perfil, col_grid = st.columns([1, 4])
                with col_perfil:
                    st.image(obter_foto_promotor(promotor), width=100)
                    p_apr = len(df_p[df_p[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)])
                    p_pen = len(df_p[df_p[col_status].str.contains('Pendente', case=False, na=False)])
                    st.markdown(f"<div class='profile-card'><b>{promotor}</b><br>✅ {p_apr} | ⚠️ {p_pen}</div>", unsafe_allow_html=True)
                with col_grid:
                    cols_itens = st.columns(3)
                    for i, item in enumerate(TODOS_ITENS):
                        with cols_itens[i % 3]:
                            d_i = df_p[df_p[col_item] == item]
                            q_ok = len(d_i[d_i[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)])
                            q_pd = len(d_i[d_i[col_status].str.contains('Pendente', case=False, na=False)])
                            f_eq = falta_item.get(item, 0)
                            html_status = f"<span class='pill-ok'>OK: {q_ok}</span>" if q_ok > 0 else f"<span class='pill-zero'>Zerado</span>"
                            html_status += f" <span class='pill-pend'>Pend: {q_pd}</span>"
                            meta_style = "background-color:#eff6ff;color:#2563eb" if f_eq > 0 else "background-color:#f0fdf4;color:#16a34a"
                            meta_txt = f"🎯 FALTA: {f_eq}" if f_eq > 0 else "🎉 META BATIDA!"
                            st.markdown(f"<div class='item-box'><b>{item}</b><br>{html_status}<div style='margin-top:5px;padding:3px;border-radius:5px;text-align:center;font-size:12px;font-weight:bold;{meta_style}'>{meta_txt}</div></div>", unsafe_allow_html=True)
                st.markdown("---")

        elif pagina == "📊 Visão Geral (Gráficos)":
            st.markdown("## 📊 Comparativo Visual")
            st.markdown("---")
            c1, c2 = st.columns(2); c3, c4 = st.columns(2); grids = [c1, c2, c3, c4]
            for idx, fil in enumerate(FILIAIS):
                with grids[idx] if idx < 4 else st.container():
                    nome_f = fil.split('-')[-1].strip()
                    st.markdown(f"### {nome_f}")
                    df_g = df[df[col_filial].str.contains(nome_f, case=False, na=False)]
                    mt_g = metas_dict.get(fil, {})
                    x_ax, y_mt, y_rl, y_pe = [], [], [], []
                    for it in TODOS_ITENS:
                        x_ax.append(it[:10]+".."); y_mt.append(mt_g.get(it,0))
                        y_rl.append(len(df_g[(df_g[col_item]==it) & (df_g[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False))]))
                        y_pe.append(len(df_g[(df_g[col_item]==it) & (df_g[col_status].str.contains('Pendente', case=False, na=False))]))
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=x_ax, y=y_mt, name='Meta', marker_color='#93c5fd'))
                    fig.add_trace(go.Bar(x=x_ax, y=y_rl, name='Aprovados', marker_color='#15803d'))
                    fig.add_trace(go.Bar(x=x_ax, y=y_pe, name='Pendentes', marker_color='#d97706'))
                    fig.update_layout(height=250, margin=dict(t=10,b=10,l=10,r=10), barmode='group'); st.plotly_chart(fig, use_container_width=True)
                    st.markdown("---")

        elif pagina == "📉 Análise Whiskas Sache":
            st.markdown("## 📉 Detalhe: Whiskas Sachê")
            itens_unicos = df[col_item].unique(); idx_w = list(itens_unicos).index("Reset Whiskas Sachês") if "Reset Whiskas Sachês" in itens_unicos else 0
            item_selecionado = st.selectbox("Selecione o Item:", itens_unicos, index=idx_w)
            st.markdown("---")
            df_w = df[df[col_item] == item_selecionado]
            if df_w.empty: st.warning("Nenhum dado encontrado.")
            else:
                c_graf, c_rank = st.columns([3, 2])
                with c_graf:
                    df_soma_filial = df_w[df_w[col_status].str.contains('Aprovado|Pendente|Conforme|Sim', case=False, na=False)]
                    if not df_soma_filial.empty:
                        soma_filial = df_soma_filial.groupby(col_filial).size().reset_index(name='TOTAL')
                        soma_filial[col_filial] = soma_filial[col_filial].str.replace('Minassal Ltda - ', '', regex=False)
                        st.dataframe(soma_filial, use_container_width=True, hide_index=True)
                    df_fil = df_w.groupby([col_filial, col_status]).size().reset_index(name='Qtd')
                    df_fil = df_fil[df_fil[col_status].str.contains('Aprovado|Pendente|Sim|Conforme', case=False, na=False)]
                    fig = px.bar(df_fil, x=col_filial, y='Qtd', color=col_status, barmode='group'); st.plotly_chart(fig, use_container_width=True)
                with c_rank:
                    df_rank = df_w.groupby([col_promotor, col_status]).size().unstack(fill_value=0)
                    for promotor, row in df_rank.iterrows():
                        qtd_ok = sum([val for col, val in row.items() if re.search('Aprovado|Conforme|Sim', str(col), re.IGNORECASE)])
                        qtd_pend = sum([val for col, val in row.items() if re.search('Pendente', str(col), re.IGNORECASE)])
                        if qtd_ok == 0 and qtd_pend == 0: continue
                        foto_p = obter_foto_promotor(promotor); c_im, c_tx = st.columns([1, 4])
                        with c_im: st.image(foto_p, width=50)
                        with c_tx: st.markdown(f"<div class='row-whiskas'><b>{promotor}</b><div class='num-whiskas'>✅{int(qtd_ok)} ⚠️{int(qtd_pend)}</div></div>", unsafe_allow_html=True)

        elif pagina == "🎯 Metas por Item (Detelhado)":
            st.markdown("## 🎯 Detalhamento de Metas por Item")
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["👜 Small Bags", "➕ Ponto Extra Sachê", "🐱 Sache Rebaixa (CV)", "🦴 Petisco Rebaixa (CV)", "📉 Rebaixa Whiskas (Reset)"])
            def render_meta_item(item_nome, tab_context):
                with tab_context:
                    st.markdown(f"### {item_nome}")
                    for filial in FILIAIS:
                        metas_f = metas_dict.get(filial, {}); meta_val = int(metas_f.get(item_nome, 0))
                        nome_f = filial.split('-')[-1].strip(); df_fil = df[df[col_filial].str.contains(nome_f, case=False, na=False)]
                        df_item = df_fil[df_fil[col_item] == item_nome]
                        apr = len(df_item[df_item[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)])
                        pen = len(df_item[df_item[col_status].str.contains('Pendente', case=False, na=False)])
                        st.markdown(f"<div class='filial-header'>{nome_f}</div><div class='filial-stats'><div class='stat-box'><div class='stat-label'>Meta</div><div class='stat-value' style='color:#3b82f6'>{meta_val}</div></div><div class='stat-box'><div class='stat-label'>Real+Pend</div><div class='stat-value' style='color:#16a34a'>{apr + pen}</div></div></div>", unsafe_allow_html=True)
                        if not df_item.empty:
                            df_prom = df_item.groupby(col_promotor).apply(lambda x: pd.Series({'Apr': len(x[x[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)]), 'Pend': len(x[x[col_status].str.contains('Pendente', case=False, na=False)])})).sort_values('Apr', ascending=False)
                            for promotor, row in df_prom.iterrows():
                                if row['Apr'] == 0 and row['Pend'] == 0: continue
                                foto = obter_foto_promotor(promotor); c_img, c_info = st.columns([1, 4])
                                with c_img: st.image(foto, width=40)
                                with c_info: st.markdown(f"<div class='promo-row'><div style='flex:1; font-weight:bold; font-size:14px;'>{promotor}</div><div style='margin-right:10px;'><span class='pill-ok'>{int(row['Apr'])}</span> <span class='pill-pend'>{int(row['Pend'])}</span></div></div>", unsafe_allow_html=True)
                        else: st.info("Sem dados.")
                        st.markdown("---")
            render_meta_item("Small Bags", tab1); render_meta_item("Ponto Extra de Sachês/Petiscos", tab2)
            render_meta_item("Combos Virtuais Sachês (KiteKat, Champ, Optimum)", tab3); render_meta_item("Combos Virtuais Petiscos", tab4)
            render_meta_item("Reset Whiskas Sachês", tab5)

        elif pagina == "🏆 Ranking Consolidado (Geral)":
            st.markdown("## 🏆 Ranking Consolidado de Promotores")
            df_consolidado = df[df[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)].copy()
            if not df_consolidado.empty:
                ranking_geral = df_consolidado.groupby([col_promotor, col_filial, col_item]).size().unstack(fill_value=0).reset_index()
                for it in TODOS_ITENS:
                    if it not in ranking_geral.columns: ranking_geral[it] = 0
                ranking_geral['TOTAL'] = ranking_geral[TODOS_ITENS].sum(axis=1)
                ranking_geral = ranking_geral.sort_values('TOTAL', ascending=False).reset_index(drop=True)
                ranking_geral[col_filial] = ranking_geral[col_filial].str.replace('Minassal Ltda - ', '', regex=False)
                cols_display = [col_promotor, col_filial] + TODOS_ITENS + ['TOTAL']; ranking_geral = ranking_geral[cols_display]
                ranking_geral.columns = ['Promotor', 'Filial'] + TODOS_ITENS + ['TOTAL GERAL']; st.dataframe(ranking_geral, use_container_width=True, hide_index=True)
            else: st.warning("Nenhum dado aprovado encontrado.")

        elif pagina == "📊 Aprovado e Pendente vs Meta":
            st.markdown("## 📊 APROVADO E PENDENTE VERSUS META"); dados_quadro = []
            for filial in FILIAIS:
                nome_curto = filial.split('-')[-1].strip(); df_filial = df[df[col_filial].str.contains(nome_curto, case=False, na=False)]
                metas_f = metas_dict.get(filial, {}); for it in TODOS_ITENS:
                    meta_item = int(metas_f.get(it, 0)); df_item = df_filial[df_filial[col_item] == it]
                    aprovados = len(df_item[df_item[col_status].str.contains('Aprovado|Conforme|Sim', case=False, na=False)])
                    pendentes = len(df_item[df_item[col_status].str.contains('Pendente', case=False, na=False)])
                    dados_quadro.append({"Filial": nome_curto, "Item": it, "Meta": meta_item, "Aprovados": aprovados, "Pendentes": pendentes, "Apr + Pend": aprovados+pendentes, "Falta": max(0, meta_item-aprovados)})
            df_quadro = pd.DataFrame(dados_quadro); item_filtro = st.selectbox("🎯 Filtrar:", ["Todos"] + TODOS_ITENS)
            df_exibicao = df_quadro if item_filtro == "Todos" else df_quadro[df_quadro["Item"] == item_filtro]
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        elif pagina == "📍 Leituras Clientes TOP REDES":
            st.markdown("## 📍 Leituras Clientes TOP REDES")
            cnpj_col = next((c for c in df.columns if 'Cnpj' in c or 'Documento' in c or 'Cpf' in c or 'Cnpjcpfpdv' in c), None)
            if cnpj_col:
                df['Cnpj_Clean'] = df[cnpj_col].apply(limpar_cnpj)
                for f_nome in ["Juiz de Fora", "Pocos de Caldas", "Sao Joao da Boa Vista", "Sao Jose do Rio Preto"]:
                    st.markdown(f"<div class='filial-header'>🏢 FILIAL: {f_nome.upper()}</div><br>", unsafe_allow_html=True)
                    clientes_f = [c for c in TOP_40_REDES_DATA if c[1] == f_nome]; dados_tabela = []
                    tot_sb_apr, tot_sb_pen, tot_wh_apr, tot_wh_pen = 0, 0, 0, 0
                    for cnpj, _, razao in clientes_f:
                        df_c = df[(df['Cnpj_Clean'] == cnpj)]
                        sb_apr = len(df_c[(df_c[col_item] == "Small Bags") & (df_c[col_status].str.contains('Aprovado|Sim|Conforme', case=False, na=False))])
                        sb_pen = len(df_c[(df_c[col_item] == "Small Bags") & (df_c[col_status].str.contains('Pendente', case=False, na=False))])
                        wh_apr = len(df_c[(df_c[col_item] == "Reset Whiskas Sachês") & (df_c[col_status].str.contains('Aprovado|Sim|Conforme', case=False, na=False))])
                        wh_pen = len(df_c[(df_c[col_item] == "Reset Whiskas Sachês") & (df_c[col_status].str.contains('Pendente', case=False, na=False))])
                        tot_sb_apr += sb_apr; tot_sb_pen += sb_pen; tot_wh_apr += wh_apr; tot_wh_pen += wh_pen
                        dados_tabela.append({"Razão Social": razao, "CNPJ": cnpj, "Small Bags Aprovados": sb_apr, "Small Bags Pendentes": sb_pen, "Whiskas Rebaixa Aprovados": wh_apr, "Whiskas Rebaixa Pendentes": wh_pen, "Total": (sb_apr + sb_pen + wh_apr + wh_pen)})
                    st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, hide_index=True)
                    c1, c2 = st.columns(2); c1.markdown(f"**Total SB ({f_nome}):** ✅ {tot_sb_apr} | ⚠️ {tot_sb_pen}"); c2.markdown(f"**Total WH ({f_nome}):** ✅ {tot_wh_apr} | ⚠️ {tot_wh_pen}"); st.markdown("---")
            else: st.error("Coluna de documento não encontrada.")
else: st.info("👆 Carregue o CSV ao lado para iniciar.")
