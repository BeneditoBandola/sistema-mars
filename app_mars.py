# --- FUNÇÃO PDF ATUALIZADA (EXATAMENTE IGUAL À IMAGEM) ---
def gerar_pdf_mars(promotor, loja, cidade, df_audit, df_faltantes, feedback):
    nome_arquivo = f"Oportunidades_Mars_{loja.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Título Centralizado
    estilo_titulo = estilos['Title']
    estilo_titulo.alignment = 1 # Centralizado
    elementos.append(Paragraph(f"<b>RELATÓRIO DE OPORTUNIDADES MARS</b>", estilo_titulo))
    elementos.append(Spacer(1, 10))
    
    # Cabeçalho de Informações
    txt_cabecalho = f"""
    <b>LOJA:</b> {loja} | <b>CIDADE:</b> {cidade}<br/>
    <b>PROMOTOR:</b> {promotor} | <b>DATA:</b> {obter_horario_brasil()}
    """
    elementos.append(Paragraph(txt_cabecalho, estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    # 1. AUDITORIA DE PREÇOS E GÔNDOLA
    if not df_audit.empty:
        elementos.append(Paragraph("<b>1. AUDITORIA DE PREÇOS E GÔNDOLA</b>", estilos['Heading3']))
        elementos.append(Spacer(1, 5))
        
        data_audit = [["PRODUTO", "REC. MARS", "PREÇO LOJA", "SITUAÇÃO", "FALTA?"]]
        row_colors = []
        
        for i, r in enumerate(df_audit.itertuples()):
            idx = i + 1
            p_loja = float(r._5) 
            p_rec_val = float(str(r.SUGERIDO).replace("R$", "").strip())
            falta_status = "SIM" if r._4 else "NÃO"
            
            if p_loja == 0:
                sit = "FALTA"
                row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
            else:
                perc = ((p_loja - p_rec_val) / p_rec_val) * 100
                if p_loja > p_rec_val:
                    sit = f"ACIMA (+{perc:.1f}%)"
                    row_colors.append(('TEXTCOLOR', (3, idx), (3, idx), colors.red))
                else:
                    sit = f"CORRETO ({perc:.1f}%)"
            
            data_audit.append([r.PRODUTO[:30], r.SUGERIDO, f"R$ {p_loja:.2f}", sit, falta_status])
            
        t1 = Table(data_audit, colWidths=[190, 80, 80, 110, 55])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        if row_colors:
            t1.setStyle(TableStyle(row_colors))
        elementos.append(t1)
        elementos.append(Spacer(1, 20))

    # 2. OPORTUNIDADES (ITENS NÃO COMERCIALIZADOS)
    elementos.append(Paragraph("<b>2. OPORTUNIDADES (ITENS NÃO COMERCIALIZADOS)</b>", estilos['Heading3']))
    elementos.append(Spacer(1, 5))
    
    data_faltantes = [["Código", "Produto"]]
    for f in df_faltantes:
        data_faltantes.append([f[0], f[1]])
        
    t2 = Table(data_faltantes, colWidths=[80, 435])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkred),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elementos.append(t2)
    elementos.append(Spacer(1, 15))
    
    # Observações
    if feedback:
        elementos.append(Paragraph(f"<b>OBSERVAÇÕES DO PROMOTOR:</b>", estilos['Heading3']))
        elementos.append(Paragraph(feedback, estilos['Normal']))
    
    doc.build(elementos)
    return nome_arquivo
