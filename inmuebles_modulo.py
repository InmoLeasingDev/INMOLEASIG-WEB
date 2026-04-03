import streamlit as st
import pandas as pd
import time
import urllib.parse
import re
from fpdf import FPDF
import supabase
import plotly.express as px
# --- NUESTRA LIBRERÍA MAESTRA ---
from herramientas import log_accion, enviar_reporte_correo, generar_excel_bytes, panel_reportes_y_compartir, panel_gestor_galeria


# =========================================
# 1. MOTOR PDF PROPIEDADES
# =========================================
def generar_pdf_propiedades(df, titulo_empresa="INMOLEASING"):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"{titulo_empresa} - DIRECTORIO DE PROPIEDADES", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    # Ajustamos anchos: quitamos ID y agregamos MONEDA
    cw = [65, 35, 45, 25, 55, 45] 
    headers = ["NOMBRE", "TIPO", "CIUDAD", "MONEDA", "ASEGURADORA", "POLIZA"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        textos = [
            str(row.get('NOMBRE', '')), str(row.get('TIPO', '')),
            str(row.get('CIUDAD', '')), str(row.get('MONEDA', '')), 
            str(row.get('ASEGURADORA', '')), str(row.get('numero_poliza', ''))
        ]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 190: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. MOTOR PDF UNIDADES (CON TOTALIZADOR)
# ==========================================
def generar_pdf_unidades(df, titulo_empresa="INMOLEASING"):
    pdf = FPDF(orientation="L") # Horizontal (Landscape)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"{titulo_empresa} - DIRECTORIO DE UNIDADES", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    
    # Anchos para: PROPIEDAD, UNIDAD, TIPO, ESTADO, ÁREA, PRECIO
    cw = [65, 45, 40, 30, 25, 40] 
    headers = ["PROPIEDAD", "UNIDAD", "TIPO", "ESTADO", "ÁREA (m2)", "PRECIO"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    
    # Variables maestras para el cálculo del total
    total_precio = 0.0
    simbolo = ""
    
    for _, row in df.iterrows():
        # 1. Extraer y limpiar el precio para poder sumarlo
        precio_str = str(row.get('PRECIO', '')).strip()
        if precio_str and precio_str != "None" and precio_str != "-":
            # Detectar la moneda automáticamente
            if not simbolo:
                if "€" in precio_str: simbolo = "€"
                elif "$" in precio_str: simbolo = "$"
            
            # Quitar símbolos y comas para que Python pueda hacer matemáticas
            num_str = precio_str.replace("€", "").replace("$", "").replace(",", "").strip()
            try:
                total_precio += float(num_str)
            except ValueError:
                pass # Si hay algún error de texto, lo ignora y sigue

        # 2. Dibujar la fila normal
        # 💡 SOLUCIÓN: Cambiamos el símbolo '€' por 'EUR' solo para el texto del PDF
        precio_pdf = precio_str.replace("€", "EUR")
        
        textos = [
            str(row.get('PROPIEDAD', '')), 
            str(row.get('UNIDAD', '')), 
            str(row.get('TIPO', '')),
            str(row.get('ESTADO', '')),
            str(row.get('ÁREA (m2)', '')),
            precio_pdf
        ]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        
        if pdf.get_y() + h_fila > 190: 
            pdf.add_page()
            
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
        
    # --- 3. DIBUJAR LA GRAN FILA DEL TOTAL ---
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 230, 240) # Un sombreado gris claro muy elegante
    
    # Unificamos todas las columnas menos la última para hacer espacio
    ancho_previo = sum(cw[:-1]) 
    pdf.cell(ancho_previo, 8, "TOTAL PRECIO BASE DE LAS UNIDADES:", 1, 0, "R", True)
    
    # 💡 SOLUCIÓN: Si la moneda original era '€', imprimimos 'EUR' en el totalizador
    simbolo_pdf = "EUR" if simbolo == "€" else simbolo
    pdf.cell(cw[-1], 8, f"{simbolo_pdf} {total_precio:,.2f}", 1, 0, "L", True)
    pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1')
        
    # --- 3. DIBUJAR LA GRAN FILA DEL TOTAL ---
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 230, 240) # Un sombreado gris claro muy elegante
    
    # Unificamos todas las columnas menos la última para hacer espacio
    ancho_previo = sum(cw[:-1]) 
    pdf.cell(ancho_previo, 8, "TOTAL PRECIO BASE DE LAS UNIDADES:", 1, 0, "R", True)
    
    # Imprimimos el total con su respectiva moneda y comas
    pdf.cell(cw[-1], 8, f"{simbolo} {total_precio:,.2f}", 1, 0, "L", True)
    pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. MOTOR PDF MANDATOS / CONTRATOS
# ==========================================
def generar_pdf_mandatos(df, titulo_empresa="INMOLEASING"):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"{titulo_empresa} - DIRECTORIO DE MANDATOS Y CONTRATOS", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    
    # Anchos: INMUEBLE, TITULAR, % COBRO, RENTA, FINANZAS
    cw = [80, 70, 25, 40, 45] 
    headers = ["INMUEBLE", "TITULAR", "% COBRO", "RENTA GARANTIZADA", "ESTADO FINANZAS"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        # Limpiamos el texto para evitar errores de codificación
        textos = [
            str(row.get('INMUEBLE', '')), 
            str(row.get('TITULAR', '')), 
            str(row.get('% COBRO', '')),
            str(row.get('RENTA', '')),
            str(row.get('FINANZAS', ''))
        ]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        
        if pdf.get_y() + h_fila > 190: 
            pdf.add_page()
            
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# 4. MOTOR PDF FICHA DETALLADA DE MANDATO
# ==========================================
def generar_pdf_ficha_mandato(df, titulo_empresa="INMOLEASING"):
    # 💡 EL TRUCO: Extraemos la única fila del DataFrame y la volvemos diccionario
    datos = df.iloc[0].to_dict()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 15)

    pdf.cell(0, 10, f"{titulo_empresa} - FICHA TECNICA DE CONTRATO", ln=True, align="C")
    pdf.ln(5)

    def limpiar(texto):
        return str(texto).encode('latin-1', 'ignore').decode('latin-1')

    def seccion(titulo):
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(41, 128, 185) # Azul corporativo elegante
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 7, limpiar(titulo), 0, 1, "L", True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def fila(etiqueta, valor):
        pdf.set_font("Arial", "B", 9)
        pdf.cell(50, 6, limpiar(f"{etiqueta}:"), 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 6, limpiar(valor))

    # --- 1. TITULARIDAD ---
    seccion("1. TITULARIDAD Y VINCULACION")
    fila("Propiedad / Unidad", datos.get('inmueble', 'N/A'))
    fila("Titular Principal", f"{datos.get('propietario_1', 'N/A')} (% Propiedad: {datos.get('porc_prop_1', 0)}% | % Cobro: {datos.get('porc_pago_1', 0)}%)")
    fila("IBAN Principal", datos.get('iban_1', 'N/A'))
    if datos.get('porc_prop_2', 0) > 0:
        fila("Titular Secundario", f"Registrado (% Propiedad: {datos.get('porc_prop_2', 0)}% | % Cobro: {datos.get('porc_pago_2', 0)}%)")
        fila("IBAN Secundario", datos.get('iban_2', 'N/A'))

    pdf.ln(3)
    # --- 2. CRONOGRAMA ---
    seccion("2. CRONOGRAMA LEGAL (SMART DATES)")
    fila("Fecha Suscripcion", datos.get('f_suscripcion', 'N/A'))
    fila("Fecha Entrega Llaves", datos.get('f_entrega', 'N/A'))
    fila("Inicio de Pagos", datos.get('f_pagos', 'N/A'))
    fila("Vencimiento", datos.get('f_vence', 'N/A'))
    fila("Limite de Preaviso", datos.get('f_aviso', 'N/A'))

    pdf.ln(3)
    # --- 3. FINANZAS ---
    seccion("3. ACUERDO FINANCIERO")
    fila("Renta Garantizada", f"{datos.get('renta', 0)} (Actualizacion: {datos.get('actualizacion', 'N/A')})")
    fila("Fianza Acordada", str(datos.get('fianza', 0)))
    fila("Penalizacion", f"{datos.get('tipo_ind', 'N/A')} - Base: {datos.get('monto_ind', 0)}")
    fila("Estado Actual", datos.get('estado_fin', 'N/A'))

    pdf.ln(3)
    # --- 4. BÓVEDA DOCUMENTAL (LINKS ACTIVOS) ---
    seccion("4. ENLACES A BOVEDA DE DOCUMENTOS")
    pdf.set_font("Arial", "U", 9)

    def link_doc(nombre, url):
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(50, 6, limpiar(nombre), 0, 0)
        
        if url and str(url) != "None" and str(url).strip() != "":
            pdf.set_text_color(0, 0, 255) # Azul Link
            pdf.set_font("Arial", "U", 9)
            pdf.cell(0, 6, limpiar("Click aqui para abrir documento en la nube"), 0, 1, link=str(url))
        else:
            pdf.set_font("Arial", "", 9)
            pdf.cell(0, 6, "Pendiente de subir", 0, 1)

    link_doc("Contrato Firmado:", datos.get('url_c'))
    link_doc("Empadronamiento:", datos.get('url_e'))
    link_doc("Acta Inventario:", datos.get('url_i'))
    link_doc("Suministros:", datos.get('url_s'))

    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# 5. MOTOR PDF HISTORIAL DE MANDATO
# ==========================================
def generar_pdf_historial_mandato(df, titulo_empresa="INMOLEASING"):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"{titulo_empresa} - HISTORIAL DE AUDITORIA DEL CONTRATO", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(200, 220, 255)
    cw = [35, 190, 45] # FECHA, ACCION, USUARIO
    headers = ["FECHA", "ACCION REGISTRADA", "USUARIO"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        textos = [str(row.get('FECHA', '')), str(row.get('ACCION REGISTRADA', '')), str(row.get('USUARIO', ''))]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 190: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# 6. MOTOR PDF ACTIVOS (INVENTARIO)
# ==========================================
def generar_pdf_activos(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE ACTIVOS FIJOS", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    cw = [25, 60, 30, 35, 55, 25, 25]
    headers = ["CODIGO", "ACTIVO", "CATEGORIA", "DUENO", "UBICACION", "ESTADO", "VALOR"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    total_valor = 0.0
    simbolo = "EUR"
    for _, row in df.iterrows():
        val_str = str(row.get('VALOR', '0')).replace("€", "").replace("$", "").replace(",", "").strip()
        try: total_valor += float(val_str)
        except: pass
        
        textos = [str(row.get('CÓDIGO', '')), str(row.get('ACTIVO', '')), str(row.get('CATEGORÍA', '')), str(row.get('DUEÑO', '')), str(row.get('UBICACIÓN', '')), str(row.get('ESTADO', '')), str(row.get('VALOR', '')).replace("€", "EUR")]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 190: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 230, 240)
    pdf.cell(sum(cw[:-1]), 8, "TOTAL INVERSION (SEGÚN FILTRO):", 1, 0, "R", True)
    pdf.cell(cw[-1], 8, f"{simbolo} {total_valor:,.2f}", 1, 0, "L", True)
    pdf.ln()
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# 6B. MOTOR PDF CONTROL DE GARANTÍAS
# ==========================================
def generar_pdf_garantias(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - CONTROL DE GARANTIAS DE ACTIVOS", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    cw = [25, 65, 45, 45, 35, 35]
    headers = ["CODIGO", "ACTIVO", "DUENO", "UBICACION", "FECHA COMPRA", "VENCE GARANTIA"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        textos = [str(row.get('CÓDIGO', '')), str(row.get('ACTIVO', '')), str(row.get('DUEÑO', '')), str(row.get('UBICACIÓN', '')), str(row.get('COMPRA', '')), str(row.get('FIN GARANTÍA', ''))]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 190: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# 7. MOTOR PDF MOVIMIENTOS Y TRAZABILIDAD
# ==========================================
def generar_pdf_movimientos(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - HISTORIAL LOGISTICO DE ACTIVOS", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    cw = [25, 45, 40, 40, 80, 45]
    headers = ["FECHA", "ACTIVO", "ORIGEN", "DESTINO", "MOTIVO", "USUARIO"]
    for i, h in enumerate(headers): pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()
    pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        textos = [str(row.get('FECHA', '')), str(row.get('ACTIVO', '')), str(row.get('ORIGEN', '')), str(row.get('DESTINO', '')), str(row.get('MOTIVO', '')), str(row.get('USUARIO', ''))]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 190: pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# MÓDULO PRINCIPAL: INMUEBLES
# ==========================================
def mostrar_modulo_inmuebles(supabase):
    st.header("🏢 Gestión de Inmuebles y Activos")
    MOD_VERSION = "v4.5  )"
    st.caption(f"⚙️ Módulo Inmuebles {MOD_VERSION} | Control de Propiedades, Unidades, Mandatos e Inventarios.")

    # --- Identificar al usuario para los logs ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    # 🛡️ DEFINIR LA MONEDA DE LA SESIÓN (El blindaje que faltaba)
    moneda_sesion = st.session_state.get("moneda_usuario", "EUR")
    # --- NAVEGACIÓN PRINCIPAL DEL MÓDULO (Pestañas) ---
    tab_dash, tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "🏢 Propiedades", 
        "🚪 Unidades", 
        "📜 Mandatos",
        "🛋️ Activos Fijos"
    ])
    #========================================================
    # 📊 DASHBOARD OPERATIVO Y CAPACIDAD INSTALADA (PRO MINIMALISTA)
    # =========================================================
    with tab_dash:
        # --- 🎨 1. CSS ULTRA-MINIMALISTA Y COMPACTO ---
        st.markdown("""
        <style>
            .pro-card {
                background: linear-gradient(145deg, #181824, #1f1f2e);
                border-radius: 8px;
                border: 1px solid rgba(131, 56, 236, 0.15);
                padding: 10px 14px; /* Aún más compacto */
                margin-bottom: 2px;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            .pro-card:hover {
                transform: translateY(-2px);
                border-color: rgba(131, 56, 236, 0.6);
            }
            .pro-metric-title { color: #8a8a9e; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
            .pro-metric-value { color: #ffffff; font-size: 22px; font-weight: 600; margin-bottom: 0px; line-height: 1.1; }
            .pro-metric-delta { font-size: 10px; font-weight: 500; }
            .pro-metric-delta.positive { color: #10b981; }
            .pro-metric-delta.negative { color: #ef4444; }
            .pro-metric-delta.neutral { color: #6b7280; }
            
            /* Títulos de sección ultra-compactos */
            .sec-title {
                font-size: 14px;
                font-weight: 600;
                color: #4a4a5e;
                margin-top: 4px;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        </style>
        """, unsafe_allow_html=True)

        # Título nativo de Streamlit (sin huecos)
        #st.caption("📊 Dashboard Operativo (Calculado On-The-Fly)")
        
        simbolo_mon = "€" if moneda_sesion == "EUR" else "$"
        
        # ---- 2. EXTRACCIÓN DE DATOS ----
        with st.spinner("Calculando métricas..."):
            try:
                res_inm = supabase.table("inmuebles").select("id, estado").eq("moneda", moneda_sesion).execute()
                df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
                
                res_uni = supabase.table("unidades").select("id, estado, id_inmueble").execute()
                df_uni = pd.DataFrame(res_uni.data) if res_uni.data else pd.DataFrame()
                
                res_man = supabase.table("mandatos").select("id, estado_contrato, fecha_terminacion").eq("moneda", moneda_sesion).execute()
                df_man = pd.DataFrame(res_man.data) if res_man.data else pd.DataFrame()
                
                res_act = supabase.table("activos").select("id, estado, valor_compra, origen, ubicacion_tipo, propiedad").eq("moneda", moneda_sesion).execute()
                df_act = pd.DataFrame(res_act.data) if res_act.data else pd.DataFrame()
            except Exception as e:
                st.error(f"Error base de datos: {e}")
                df_inm, df_uni, df_man, df_act = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # --- 3. CÁLCULO DE KPIS ---
        inm_totales = len(df_inm)
        inm_activos = len(df_inm[df_inm['estado'] == 'ACTIVO']) if not df_inm.empty else 0
        inm_inactivos = inm_totales - inm_activos
        
        uni_totales = len(df_uni)
        uni_ocupadas = len(df_uni[df_uni['estado'] == 'OCUPADA']) if not df_uni.empty else 0
        uni_disponibles = len(df_uni[df_uni['estado'].isin(['DISPONIBLE', 'LIBRE'])]) if not df_uni.empty else 0
        ocupacion_pct = (uni_ocupadas / uni_totales * 100) if uni_totales > 0 else 0.0
        
        man_activos, man_vencer, man_vencidos = 0, 0, 0
        if not df_man.empty:
            df_man['fecha_terminacion'] = pd.to_datetime(df_man['fecha_terminacion'], errors='coerce')
            hoy = pd.Timestamp.now().normalize()
            man_activos = len(df_man[df_man['estado_contrato'] != 'FINALIZADO'])
            man_vencidos = len(df_man[(df_man['fecha_terminacion'] < hoy) & (df_man['estado_contrato'] != 'FINALIZADO')])
            limite_60d = hoy + pd.Timedelta(days=60)
            man_vencer = len(df_man[(df_man['fecha_terminacion'] >= hoy) & (df_man['fecha_terminacion'] <= limite_60d) & (df_man['estado_contrato'] != 'FINALIZADO')])

        act_totales, val_total, val_bodega, act_bodega = len(df_act), 0.0, 0.0, 0
        act_buenos, act_malos = 0, 0
        if not df_act.empty:
            df_empresa = df_act[df_act['propiedad'] == 'Empresa'].copy()
            df_empresa['valor_compra'] = pd.to_numeric(df_empresa['valor_compra'], errors='coerce').fillna(0)
            val_total = df_empresa['valor_compra'].sum()
            act_buenos = len(df_act[df_act['estado'].isin(['Nuevo', 'Bueno'])])
            act_malos = len(df_act[df_act['estado'].isin(['Deteriorado', 'En reparación', 'Punto Limpio'])])
            df_bodega = df_act[(df_act['ubicacion_tipo'] == 'Bodega') | (df_act['estado'] == 'En bodega')]
            act_bodega = len(df_bodega)
            val_bodega = df_bodega[df_bodega['propiedad'] == 'Empresa']['valor_compra'].astype(float).sum() if not df_bodega.empty else 0.0

        # --- 4. FUNCIÓN CREADORA DE TARJETAS ---
        def create_pro_card(title, value, delta, is_negative=False):
            delta_class = "negative" if is_negative else ("positive" if "↑" in delta or "%" in delta else "neutral")
            st.markdown(f"""
            <div class="pro-card">
                <div class="pro-metric-title">{title}</div>
                <div class="pro-metric-value">{value}</div>
                <div class="pro-metric-delta {delta_class}">{delta}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- SECCIÓN 1 ---
        st.markdown("<div class='sec-title' style='margin-top: -30px;'>Capacidad Instalada</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: create_pro_card("Propiedades Activas", f"{inm_activos}", f"{inm_inactivos} inactivas")
        with c2: create_pro_card("Unidades Totales", f"{uni_totales}", "")
        with c3: create_pro_card("Mandatos Activos", f"{man_activos}", "")
        with c4: create_pro_card("Ocupación Global", f"{ocupacion_pct:.1f}%", f"{uni_ocupadas} ocupadas", is_negative=(ocupacion_pct < 80))

        # --- SECCIÓN 2 ---
        st.markdown("<div class='sec-title'>Riesgo y Activos</div>", unsafe_allow_html=True)
        ca1, ca2, ca3, ca4 = st.columns(4)
        status_man_vencidos = f"{man_vencidos}" if man_vencidos > 0 else "0"
        with ca1: create_pro_card("Mandatos Vencidos", status_man_vencidos, "Crítico" if man_vencidos > 0 else "Al día", is_negative=(man_vencidos > 0))
        with ca2: create_pro_card("Por Vencer (60d)", f"{man_vencer}", "Atención" if man_vencer > 0 else "Estable", is_negative=(man_vencer > 0))
        with ca3: create_pro_card("Activos Físicos", f"{act_totales}", f"{act_buenos} sanos")
        with ca4: create_pro_card("Capital en Bodega", f"{simbolo_mon} {val_bodega:,.0f}", f"{act_bodega} ítems", is_negative=(val_bodega > 0))

        st.write("") # Pequeño respiro antes de los gráficos        
        # --- 5. GRÁFICOS COMPACTOS ---
        if not df_act.empty:
            # 1. Usamos la misma clase de título pequeña que arriba en lugar del ####
            st.markdown("<div class='sec-title'>Distribución Financiera</div>", unsafe_allow_html=True)
            
            cg1, cg2 = st.columns(2)
            colores_pro = ['#3a86ff', '#8338ec', '#ff006e', '#fb5607', '#ffbe0b']

            with cg1:
                origen_counts = df_act['origen'].value_counts()
                fig_origen = px.pie(names=origen_counts.index, values=origen_counts.values, hole=0.7, color_discrete_sequence=colores_pro)
                fig_origen.update_traces(textposition='inside', textinfo='percent')
                fig_origen.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    # Margen superior a 0 y altura reducida a 170px
                    margin=dict(l=0, r=0, t=0, b=0), showlegend=True, height=170, 
                    legend=dict(orientation="v", yanchor="auto", y=0.5, xanchor="right", x=1)
                )
                st.plotly_chart(fig_origen, use_container_width=True, key="plotly_origen_min")
            
            with cg2:
                estado_counts = df_act['estado'].value_counts()
                fig_estado = px.area(x=estado_counts.index, y=estado_counts.values, color_discrete_sequence=['#8338ec'])
                fig_estado.update_traces(fill='tozeroy', fillcolor='rgba(131, 56, 236, 0.2)', line=dict(width=2, color='#8338ec'))
                fig_estado.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    xaxis=dict(title=None, showgrid=False, tickfont=dict(size=10)), 
                    yaxis=dict(title=None, showgrid=True, tickfont=dict(size=10)), 
                    # Margen superior casi a 0 y altura reducida a 170px
                    margin=dict(l=0, r=0, t=5, b=0), height=170
                )
                st.plotly_chart(fig_estado, use_container_width=True, key="plotly_estado_min")

    # ==========================================
    # TAB 1: PROPIEDADES (CRUD + REPORTES)
    # ==========================================
    with tab1:
        # 1. Inicializador de estado para los paneles
        if 'modo_propiedad' not in st.session_state:
            st.session_state.modo_propiedad = "NADA"

        # 2. Lógica dinámica de región (La movemos arriba)
        moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
        if moneda_sesion == "EUR": 
            opciones_tipo = ["PISO", "OFICINA", "LOCAL", "NAVE", "BODEGA"]
            opciones_moneda = ["EUR"]
            label_catastro = "Referencia Catastral"
        elif moneda_sesion == "COP": 
            opciones_tipo = ["APARTAMENTO", "OFICINA", "LOCAL", "NAVE", "BODEGA"]
            opciones_moneda = ["COP"]
            label_catastro = "Matrícula Inmobiliaria"
        else: 
            opciones_tipo = ["PISO", "APARTAMENTO", "OFICINA", "LOCAL", "NAVE", "BODEGA"]
            opciones_moneda = ["EUR", "COP"]
            label_catastro = "Ref. Catastral / Matrícula"

        # 3. Cargar Operadores FILTRADOS POR REGIÓN (Para reportes)
        try:
            q_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO")
            if moneda_sesion != "ALL":
                q_ops = q_ops.eq("moneda", moneda_sesion)
            res_ops = q_ops.execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()
        # --- LECTURA DE DATOS (LA CUADRÍCULA) ---
        query = supabase.table("inmuebles").select("*").eq("estado", "ACTIVO")
        if moneda_sesion != "ALL": query = query.eq("moneda", moneda_sesion)
        res_inm = query.execute()
        df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
        
        st.write("") # Pequeño respiro visual
        
        if not df_inm.empty:
            df_inm = df_inm.sort_values(by=['moneda', 'nombre'], ascending=[True, True])
        #if not df_inm.empty:
        #    df_inm = df_inm.sort_values(by=['nombre'], ascending=[True])    
            # 1. Lógica para el Icono de Fotos en Propiedades
            def indicador_fotos_inm(fotos_array):
                if isinstance(fotos_array, list) and len(fotos_array) > 0:
                    return f"📸 {len(fotos_array)}"
                return "➖"
                
            df_inm['FOTOS'] = df_inm['fotos'].apply(indicador_fotos_inm)
            
            # 2. Preparamos el DataFrame de vista (Quitamos 'moneda', añadimos 'FOTOS')
            df_display = df_inm[['id', 'nombre', 'tipo', 'ciudad', 'referencia_catastral', 'FOTOS']].copy()
            df_display.rename(columns={
                'nombre': 'NOMBRE', 
                'tipo': 'TIPO', 
                'ciudad': 'CIUDAD', 
                'referencia_catastral': label_catastro.upper()
            }, inplace=True)
            
            st.dataframe(df_display.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            # 🛡️ ESCUDO CORREGIDO: Permitir crear la primera propiedad
            if st.session_state.modo_propiedad != "CREAR":
                st.session_state.modo_propiedad = "NADA"
            st.info("ℹ️ Aún no hay propiedades registradas o activas en tu región.")            

        # ==========================================
        # 🛠️ BARRA DE HERRAMIENTAS (MODO PRO - 5 BOTONES)
        # ==========================================
        t_c1, t_c2, t_c3, t_c4, t_c5, t_c6 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2.5]) 
        
        if t_c1.button("➕ Nueva", key="btn_nueva_prop", use_container_width=True):
            st.session_state.modo_propiedad = "CREAR"
            st.rerun()
            
        if not df_inm.empty:        
            if t_c2.button("⚙️ Gestionar", key="btn_edit_prop", use_container_width=True):
                st.session_state.modo_propiedad = "EDITAR"
                st.rerun()
                
            if t_c3.button("📸 Galería", key="btn_gal_prop", use_container_width=True):
                st.session_state.modo_propiedad = "GALERIA"
                st.rerun()
                
            if t_c4.button("📁 Plano", key="btn_doc_prop", use_container_width=True):
                st.session_state.modo_propiedad = "DOCUMENTOS"
                st.rerun()
                
            if t_c5.button("📊 Reportes", key="btn_rep_prop", use_container_width=True):
                st.session_state.modo_propiedad = "REPORTES"
                st.rerun()
        # ==========================================
        # 🗂️ PANELES DINÁMICOS
        # ==========================================
        
        # --- PANEL: CREAR NUEVA PROPIEDAD ---
        if st.session_state.modo_propiedad == "CREAR":
            st.markdown("---")
            with st.form("form_nueva_propiedad", clear_on_submit=True):
                st.markdown("**✨ Añadir Nueva Propiedad**")
                c1, c2 = st.columns(2)
                n_nom = c1.text_input("Nombre / Dirección Principal *", placeholder="Ej: Piso 2B Calle Mayor")
                n_tip = c2.selectbox("Tipo de Propiedad *", opciones_tipo)
                
                c3, c4, c5 = st.columns(3)
                n_ciu = c3.text_input("Ciudad *")
                n_mon = c4.selectbox("Región / Moneda *", opciones_moneda)
                n_cat = c5.text_input(label_catastro)
                
                st.write("**Datos del Seguro (Opcional)**")
                c6, c7, c8 = st.columns(3)
                n_ase = c6.text_input("Aseguradora")
                n_pol = c7.text_input("Número de Póliza")
                n_tel_ase = c8.text_input("Teléfono Aseguradora")
                
                st.write("**Documento Físico (Opcional)**")
                doc_croquis = st.file_uploader("Plano o Croquis del Inmueble", type=["pdf", "jpg", "png"], key="croquis_crear")
                
                st.markdown("---")
                # Botonera Minimalista
                col_b1, col_b2, col_esp = st.columns([1.5, 1.2, 7.3])
                
                if col_b1.form_submit_button("💾 Guardar"):
                    if n_nom and n_ciu:
                        with st.spinner("Guardando propiedad..."):
                            url_croquis_final = None
                            if doc_croquis:
                                ext = doc_croquis.name.split('.')[-1].lower()
                                tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                n_nube = f"croquis_{int(time.time())}.{ext}"
                                supabase.storage.from_("documentos_propiedades").upload(n_nube, doc_croquis.getvalue(), file_options={"content-type": tipo_mime})
                                url_croquis_final = supabase.storage.from_("documentos_propiedades").get_public_url(n_nube)

                            datos_insert = {
                                "nombre": n_nom.strip().upper(), "tipo": n_tip, "ciudad": n_ciu.strip().upper(),
                                "moneda": n_mon, "referencia_catastral": n_cat.strip().upper(),
                                "aseguradora": n_ase.strip().upper(), "numero_poliza": n_pol.strip().upper(), 
                                "telefono_aseguradora": n_tel_ase.strip(), "estado": "ACTIVO",
                                "url_croquis": url_croquis_final
                            }
                            supabase.table("inmuebles").insert(datos_insert).execute()                        
                        log_accion(supabase, usuario_actual, "CREAR PROPIEDAD", n_nom.strip().upper())
                        st.session_state.modo_propiedad = "NADA"
                        st.success("✅ Propiedad registrada.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ Faltan campos obligatorios (*).")
                        
                if col_b2.form_submit_button("❌ Cerrar"):
                    st.session_state.modo_propiedad = "NADA" 
                    st.rerun()

        # --- PANEL: GESTIONAR PROPIEDAD ---
        elif st.session_state.modo_propiedad == "EDITAR" and not df_inm.empty:
            st.markdown("---")
            st.markdown("**⚙️ Gestionar Propiedad**")
            
            prop_sel = st.selectbox("Seleccione la propiedad:", df_display['NOMBRE'].tolist())
            if prop_sel:
                datos_p = df_inm[df_inm['nombre'] == prop_sel].iloc[0]
                p_id = str(datos_p['id'])
                
                with st.form(key=f"form_editar_prop_{p_id}"):
                    e_c1, e_c2 = st.columns(2)
                    e_nom = e_c1.text_input("Nombre", datos_p['nombre'])
                    e_ciu = e_c2.text_input("Ciudad", datos_p['ciudad'])
                    
                    e_c3, e_c4 = st.columns(2)
                    idx_mon = 0 if datos_p.get('moneda') == 'EUR' else (1 if datos_p.get('moneda') == 'COP' else 0)
                    e_mon = e_c3.selectbox("Moneda", ["EUR", "COP"] if moneda_sesion == "ALL" else [moneda_sesion], index=idx_mon if moneda_sesion == "ALL" else 0)
                    e_cat = e_c4.text_input(label_catastro, str(datos_p.get('referencia_catastral', '')))
                    
                    e_c5, e_c6 = st.columns(2)
                    e_ase = e_c5.text_input("Aseguradora", str(datos_p.get('aseguradora', '')))
                    e_pol = e_c6.text_input("Número Póliza", str(datos_p.get('numero_poliza', '')))
                    
                    st.write("**Actualizar Documento Físico (Opcional)**")
                    st.caption("Solo sube un archivo si deseas reemplazar el plano/croquis actual.")
                    edit_croquis = st.file_uploader("Nuevo Plano o Croquis", type=["pdf", "jpg", "png"], key=f"croquis_edit_{p_id}")
                    
                    st.markdown("---")
                    # Botonera Minimalista de Gestión
                    col_b1, col_b2, col_esp = st.columns([1.5, 1.2, 7.3])
                    
                    if col_b1.form_submit_button("💾 Guardar"):
                        with st.spinner("Actualizando propiedad..."):
                            url_croquis_actualizado = datos_p.get('url_croquis')
                            
                            if edit_croquis:
                                ext = edit_croquis.name.split('.')[-1].lower()
                                tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                n_nube = f"croquis_edit_{p_id}_{int(time.time())}.{ext}"
                                supabase.storage.from_("documentos_propiedades").upload(n_nube, edit_croquis.getvalue(), file_options={"content-type": tipo_mime})
                                url_croquis_actualizado = supabase.storage.from_("documentos_propiedades").get_public_url(n_nube)

                            datos_upd = {
                                "nombre": e_nom.strip().upper(), "ciudad": e_ciu.strip().upper(),
                                "moneda": e_mon, "referencia_catastral": e_cat.strip().upper(),
                                "aseguradora": e_ase.strip().upper(), "numero_poliza": e_pol.strip().upper(),
                                "url_croquis": url_croquis_actualizado
                            }
                            supabase.table("inmuebles").update(datos_upd).eq("id", int(p_id)).execute()                        
                        log_accion(supabase, usuario_actual, "EDITAR PROPIEDAD", e_nom.strip().upper())
                        st.session_state.modo_propiedad = "NADA"
                        st.success("✅ Actualizado.")
                        time.sleep(1)
                        st.rerun()
                        
                    if col_b2.form_submit_button("❌ Cerrar"):
                        st.session_state.modo_propiedad = "NADA" 
                        st.rerun()
                        
                # Zona de eliminación fuera del form
                st.write("")
                c_del1, c_del2 = st.columns([7, 3])
                confirmar_baja = c_del1.checkbox("⚠️ Confirmo que deseo dar de baja esta propiedad.", key=f"del_chk_p_{p_id}")
                if c_del2.button("🚫 Eliminar Propiedad", disabled=not confirmar_baja, key=f"del_btn_p_{p_id}"):
                    supabase.table("inmuebles").update({"estado": "INACTIVO"}).eq("id", int(p_id)).execute()
                    log_accion(supabase, usuario_actual, "ELIMINAR PROPIEDAD", datos_p['nombre'])
                    st.success("✅ Propiedad dada de baja.")
                    st.session_state.modo_propiedad = "NADA" 
                    time.sleep(1)
                    st.rerun()
        # --- PANEL: DOCUMENTOS (CROQUIS/PLANOS) ---
        elif st.session_state.modo_propiedad == "DOCUMENTOS" and not df_inm.empty:
            st.markdown("---")
            st.markdown("Bóveda de Documentos (Planos y Croquis)")
            prop_sel = st.selectbox("Selecciona la propiedad:", df_display['NOMBRE'].tolist(), key="sel_doc_prop")
            if prop_sel:
                datos_p = df_inm[df_inm['nombre'] == prop_sel].iloc[0]
                url_croquis = datos_p.get('url_croquis')
                
                with st.container(border=True):
                    st.write(f"**Documentos de {prop_sel}**")
                    if url_croquis and str(url_croquis).strip() != "None" and str(url_croquis).strip() != "":
                        st.success("✅ Plano / Croquis Registrado")
                        st.markdown(f"📄 **[Clic aquí para abrir o descargar el documento]({url_croquis})**")
                    else:
                        st.warning("❌ No hay plano o croquis registrado para esta propiedad. Súbelo desde '⚙️ Gestionar' o al crear una nueva.")
                    
            st.markdown("---")
            if st.button("❌ Cerrar Bóveda"): 
                st.session_state.modo_propiedad = "NADA"
                st.rerun()

        # --- PANEL: GALERÍA DE FOTOS (NUEVO) ---
        elif st.session_state.modo_propiedad == "GALERIA" and not df_inm.empty:
            st.markdown("---")
            prop_sel = st.selectbox("Seleccione la propiedad para ver/editar su galería:", df_display['NOMBRE'].tolist())
            if prop_sel:
                datos_p = df_inm[df_inm['nombre'] == prop_sel].iloc[0]
                p_id = str(datos_p['id'])
                fotos_array = datos_p.get('fotos', [])
                
                # ¡LLAMAMOS A NUESTRA HERRAMIENTA MAESTRA!
                panel_gestor_galeria(
                    supabase=supabase,
                    usuario_actual=usuario_actual,
                    tabla_db="inmuebles",
                    bucket_storage="fotos_inmuebles",
                    id_registro=p_id,
                    nombre_registro=prop_sel,
                    fotos_actuales=fotos_array,
                    clave_estado_cerrar="modo_propiedad",
                    prefijo_ruta="inm"
                )
    # --- PANEL: REPORTES INTEGRADOS ---
        elif st.session_state.modo_propiedad == "REPORTES" and not df_inm.empty:
            st.markdown("---")
            # 🛡️ Lógica para el título del PDF
            titulo_encabezado = "INMOLEASING"
            if not df_ops.empty and len(df_ops) == 1:
                titulo_encabezado = str(df_ops.iloc[0]['nombre']).upper()
                
            # Llamamos a nuestra super herramienta de reportes
            panel_reportes_y_compartir(
                df_datos=df_display.drop(columns=['id']), 
                nombre_base=f"propiedades_activas",
                modulo_origen="Propiedades",
                funcion_pdf=lambda df: generar_pdf_propiedades(df, titulo_encabezado),
                df_operadores=df_ops,
                supabase=supabase,
                usuario_actual=usuario_actual,
                clave_estado_cerrar="modo_propiedad" 
            )
    # ==========================================
    # TAB 2: UNIDADES (Subdivisión de Propiedades)
    # ==========================================
    with tab2:
        # Inicializador de estado para la Barra de Herramientas
        if 'modo_unidad' not in st.session_state:
            st.session_state.modo_unidad = "NADA"

        
        # 0. Obtener moneda de sesión primero
        moneda_sesion = st.session_state.get("moneda_usuario", "ALL")

        # --- Cargar Operadores (para uso de reportes, filtrados por región) ---
        try:
            q_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO")
            if moneda_sesion != "ALL":
                q_ops = q_ops.eq("moneda", moneda_sesion)
            res_ops = q_ops.execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()

        # 1. Traer los inmuebles activos CON SU MONEDA
        query_inm = supabase.table("inmuebles").select("id, nombre, moneda").eq("estado", "ACTIVO")
        if moneda_sesion != "ALL": query_inm = query_inm.eq("moneda", moneda_sesion)
        res_prop = query_inm.order("nombre").execute()

        df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        
        if df_prop.empty:
            st.warning("⚠️ Primero debes crear una Propiedad Base (Tab 1).")
        else:
            opciones_prop = ["-- Seleccione --"] + df_prop['nombre'].tolist()
            
                
            # --- SELECTOR MAESTRO ---
            st.write("") 
            prop_maestra = st.selectbox("🏢 Elige la propiedad sobre la que deseas trabajar:", opciones_prop, key="sel_maestra_prop")
            
            # 🛡️ ESCUDO 1: Si vuelve a "Seleccione", cerramos paneles y reseteamos.
            if prop_maestra == "-- Seleccione --":
                st.session_state.modo_unidad = "NADA"
            
            if prop_maestra != "-- Seleccione --":
                # Extraemos la moneda dinámicamente
                prop_data = df_prop[df_prop['nombre'] == prop_maestra].iloc[0]
                id_prop_maestra = prop_data['id']
                moneda_prop = prop_data.get('moneda', 'EUR') 
                simbolo_mon = "€" if moneda_prop == "EUR" else "$"
                
                res_uni = supabase.table("unidades").select("*").eq("estado", "ACTIVO").eq("id_inmueble", int(id_prop_maestra)).execute()
                df_uni = pd.DataFrame(res_uni.data) if res_uni.data else pd.DataFrame()
                
                # 🛡️ ESCUDO 2: Inicializamos la variable siempre para que nunca de error
                df_uni_display = pd.DataFrame()
                
                # 🛡️ ESCUDO 3: Corregido para permitir crear la primera unidad
                if df_uni.empty and st.session_state.modo_unidad != "CREAR":
                    st.session_state.modo_unidad = "NADA"
                # --- LA CUADRÍCULA (Grid siempre visible) ---
                if not df_uni.empty:
                    emoji_map = {"DISPONIBLE": "🟢 DISP.", "OCUPADA": "🔴 OCUP.", "EN REPARACIÓN": "🟡 REP."}
                    df_uni['ESTADO'] = df_uni['disponibilidad'].map(lambda x: emoji_map.get(str(x).upper(), "⚪ DESC."))
                    
                    # Formateo visual
                    df_uni['area_m2'] = pd.to_numeric(df_uni['area_m2']).fillna(0).apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
                    df_uni['PRECIO'] = pd.to_numeric(df_uni['precio_base']).fillna(0).apply(lambda x: f"{simbolo_mon} {x:,.2f}" if x > 0 else "-")
                    
                    # Lógica para el Icono de Fotos
                    def indicador_fotos(fotos_array):
                        if isinstance(fotos_array, list) and len(fotos_array) > 0:
                            return f"📸 {len(fotos_array)}"
                        return "➖"
                        
                    df_uni['FOTOS'] = df_uni['fotos'].apply(indicador_fotos)
                    
                    df_uni_display = df_uni[['nombre', 'tipo', 'ESTADO', 'area_m2', 'PRECIO', 'FOTOS']].copy()
                    df_uni_display.rename(columns={'nombre': 'UNIDAD', 'tipo': 'TIPO', 'area_m2': 'ÁREA (m2)'}, inplace=True)
                    df_uni_display = df_uni_display.sort_values(by=['UNIDAD'])
                    
                    st.dataframe(df_uni_display, use_container_width=True, hide_index=True)
                else:
                    st.info(f"ℹ️ El edificio {prop_maestra} aún no tiene unidades. Usa la barra de herramientas para añadir la primera.")

                # ==========================================
                # 🛠️ BARRA DE HERRAMIENTAS (MODO PRO - 4 BOTONES)
                # ==========================================
                t_c1, t_c2, t_c3, t_c4, t_c5 = st.columns([1.5, 1.5, 1.5, 1.5, 4.0]) 
                
                if t_c1.button("➕ Nueva", key="btn_nueva_uni", use_container_width=True):
                    st.session_state.modo_unidad = "CREAR"
                    st.rerun()
                    
                if not df_uni.empty:
                    if t_c2.button("⚙️ Gestionar", key="btn_edit_uni", use_container_width=True):
                        st.session_state.modo_unidad = "EDITAR"
                        st.rerun()
                        
                    if t_c3.button("📸 Galería", key="btn_gal_uni", use_container_width=True):
                        st.session_state.modo_unidad = "GALERIA"
                        st.rerun()
                        
                    if t_c4.button("📊 Reportes", key="btn_rep_uni", use_container_width=True):
                        st.session_state.modo_unidad = "REPORTES"
                        st.rerun()

                # ==========================================
                # 🗂️ PANELES DINÁMICOS
                # ==========================================
                
                # --- PANEL: CREAR NUEVA UNIDAD ---
                if st.session_state.modo_unidad == "CREAR":
                    with st.form("form_nueva_unidad", clear_on_submit=True):
                        st.markdown("**✨ Añadir Nueva Unidad**")
                        c1, c2 = st.columns(2)
                        u_nom = c1.text_input("Nombre de la Unidad *", placeholder="Ej: Habitación 1, PH 2")
                        u_tip = c2.selectbox("Tipo *", ["HABITACIÓN", "SUITE", "OFICINA", "PROPIEDAD COMPLETA", "PARQUEADERO", "OTRO"])
                        
                        c3, c4 = st.columns(2)
                        u_area = c3.number_input("Área (m2)", min_value=0.0, step=1.0)
                        u_precio = c4.number_input(f"Precio Base ({simbolo_mon})", min_value=0.0, step=100.0)
                        
                        st.markdown("---")
                        col_b1, col_b2 = st.columns([2, 8])
                        
                        if col_b1.form_submit_button("💾 Guardar"):
                            if u_nom:
                                datos_u = {
                                    "id_inmueble": int(id_prop_maestra), "nombre": u_nom.strip().upper(),
                                    "tipo": u_tip, "estado": "ACTIVO", "disponibilidad": "DISPONIBLE",
                                    "area_m2": u_area, "precio_base": u_precio, "fotos": []
                                }
                                supabase.table("unidades").insert(datos_u).execute()
                                log_accion(supabase, usuario_actual, "CREAR UNIDAD", f"{u_nom.upper()} en {prop_maestra}")
                                st.session_state.modo_unidad = "NADA"
                                st.success("✅ Unidad registrada.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Debes darle un nombre a la unidad.")
                                
                        if col_b2.form_submit_button("❌ Cancelar"):
                            st.session_state.modo_unidad = "NADA" 
                            st.rerun()

                # --- PANEL: GESTIONAR UNIDAD (SIN FOTOS) ---
                elif st.session_state.modo_unidad == "EDITAR" and not df_uni.empty:
                    st.markdown("---")
                    st.markdown("**⚙️ Gestionar Unidad**")
                    
                    uni_sel = st.selectbox("Selecciona la unidad:", df_uni['nombre'].sort_values().tolist())
                    
                    if uni_sel:
                        datos_u_edit = df_uni[df_uni['nombre'] == uni_sel].iloc[0]
                        u_id = str(datos_u_edit['id'])
                        
                        with st.form(key=f"form_editor_dinamico_{u_id}", clear_on_submit=True):
                            st.write("**Detalles Básicos**")
                            e_c1, e_c2 = st.columns([2, 1])
                            e_nom = e_c1.text_input("Nombre *", datos_u_edit['nombre'])
                            
                            lista_tipos = ["HABITACIÓN", "SUITE", "OFICINA", "PROPIEDAD COMPLETA", "PARQUEADERO", "OTRO"]
                            idx_tip = lista_tipos.index(datos_u_edit['tipo']) if datos_u_edit['tipo'] in lista_tipos else 0
                            e_tip = e_c2.selectbox("Tipo *", lista_tipos, index=idx_tip)
                            
                            e_c3, e_c4, e_c5 = st.columns(3)
                            val_disp = str(datos_u_edit.get('disponibilidad', 'DISPONIBLE')).upper()
                            e_c3.text_input("Estado (Auto)", val_disp, disabled=True)
                            
                            res_crudo = supabase.table("unidades").select("area_m2, precio_base").eq("id", int(u_id)).execute()
                            val_area = float(res_crudo.data[0].get('area_m2') or 0.0) if res_crudo.data else 0.0
                            val_precio = float(res_crudo.data[0].get('precio_base') or 0.0) if res_crudo.data else 0.0
                            
                            e_area = e_c4.number_input("Área (m2)", min_value=0.0, step=1.0, value=val_area)
                            e_precio = e_c5.number_input(f"Precio ({simbolo_mon})", min_value=0.0, step=100.0, value=val_precio)
                            
                            st.markdown("---")
                            # ---- FILA DE ACCIONES COMPACTA (AJUSTE PERFECTO) ----
                            col_btn1, col_btn2, col_espacio = st.columns([2.0, 1.5, 6.5])
                            btn_guardar = col_btn1.form_submit_button("💾 Guardar Cambios")
                            btn_cerrar = col_btn2.form_submit_button("❌ Cerrar")
                            
                            if btn_cerrar:
                                st.session_state.modo_unidad = "NADA"
                                st.rerun()

                            elif btn_guardar:
                                datos_upd = {
                                    "nombre": e_nom.strip().upper(), "tipo": e_tip, 
                                    "area_m2": e_area, "precio_base": e_precio
                                }
                                supabase.table("unidades").update(datos_upd).eq("id", int(u_id)).execute()
                                log_accion(supabase, usuario_actual, "EDITAR UNIDAD", e_nom.strip().upper())
                                st.success("✅ Guardado.")
                                st.session_state.modo_unidad = "NADA" 
                                time.sleep(1)
                                st.rerun()

                    # Eliminar Unidad (fuera del form)
                    st.write("")
                    c_del1, c_del2 = st.columns([7, 3])
                    confirmar_baja = c_del1.checkbox("⚠️ Confirmo que deseo dar de baja esta unidad.", key=f"del_chk_{u_id}")
                    if c_del2.button("🚫 Eliminar Unidad", disabled=not confirmar_baja, key=f"del_btn_{u_id}"):
                        supabase.table("unidades").update({"estado": "INACTIVO"}).eq("id", int(u_id)).execute()
                        st.success("✅ Unidad dada de baja.")
                        st.session_state.modo_unidad = "NADA" 
                        time.sleep(1)
                        st.rerun()

                # --- PANEL: GALERÍA DE FOTOS UNIDADES (NUEVO) ---
                elif st.session_state.modo_unidad == "GALERIA" and not df_uni.empty:
                    st.markdown("---")
                    uni_sel = st.selectbox("Seleccione la unidad para ver/editar su galería:", df_uni['nombre'].sort_values().tolist(), key="sel_gal_uni_panel")
                    if uni_sel:
                        datos_u = df_uni[df_uni['nombre'] == uni_sel].iloc[0]
                        u_id = str(datos_u['id'])
                        fotos_array = datos_u.get('fotos', [])
                        
                        # ¡LA MAGIA DE LA HERRAMIENTA UNIVERSAL!
                        panel_gestor_galeria(
                            supabase=supabase,
                            usuario_actual=usuario_actual,
                            tabla_db="unidades",
                            bucket_storage="fotos_unidades",
                            id_registro=u_id,
                            nombre_registro=f"{uni_sel} ({prop_maestra})",
                            fotos_actuales=fotos_array,
                            clave_estado_cerrar="modo_unidad",
                            prefijo_ruta="uni"
                        )    
               # --- PANEL: REPORTES (MÓDULO COMPARTIR CENTRALIZADO) ---
                elif st.session_state.modo_unidad == "REPORTES": 
                    st.markdown("---")
                    st.markdown("**🔍 Configuración del Reporte**")
                    
                    # 1. Filtro de Alcance (Propiedades)
                    alcance = st.radio(
                        "1. Alcance geográfico:", 
                        [f"Solo {prop_maestra}", "Todas las propiedades activas"], 
                        horizontal=True
                    )
                    
                    # 2. Filtro de Estado (Unidades)
                    filtro_estado = st.radio(
                        "2. Estado de las unidades:", 
                        ["TODAS", "🟢 DISP.", "🔴 OCUP.", "🟡 REP."], 
                        horizontal=True
                    )
                   
                 
                    # --- PASO A: CONSTRUIR LA BASE SEGÚN EL ALCANCE ---
                    if alcance == "Todas las propiedades activas":
                        with st.spinner("Recopilando inventario global..."):
                            # Traer TODAS las unidades activas de la base de datos
                            res_all = supabase.table("unidades").select("*").eq("estado", "ACTIVO").execute()
                            df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
                            
                            if not df_all.empty and not df_prop.empty:
                                df_cruce = df_all.merge(df_prop[['id', 'nombre', 'moneda']], left_on='id_inmueble', right_on='id', how='left')
                                
                                # 🛡️ BLINDAJE: Filtrar el cruce global para que solo queden las de la moneda actual
                                moneda_sesion_actual = st.session_state.get("moneda_usuario", "ALL")
                                if moneda_sesion_actual != "ALL":
                                    df_cruce = df_cruce[df_cruce['moneda'] == moneda_sesion_actual]    
                                # Aplicar formatos visuales
                                df_cruce['ESTADO'] = df_cruce['disponibilidad'].map(lambda x: emoji_map.get(str(x).upper(), "⚪ DESC."))
                                df_cruce['ÁREA (m2)'] = pd.to_numeric(df_cruce['area_m2']).fillna(0).apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
                                
                                # Formato de precio inteligente (detecta si el edificio es EUR o COP)
                                def formatear_precio_global(row):
                                    val = pd.to_numeric(row.get('precio_base', 0))
                                    if pd.isna(val) or val <= 0: return "-"
                                    simb = "€" if row.get('moneda', 'EUR') == "EUR" else "$"
                                    return f"{simb} {val:,.2f}"
                                    
                                df_cruce['PRECIO'] = df_cruce.apply(formatear_precio_global, axis=1)
                                
                                # Organizar columnas finales
                                df_base = df_cruce[['nombre_y', 'nombre_x', 'tipo', 'ESTADO', 'ÁREA (m2)', 'PRECIO']].copy()
                                df_base.rename(columns={'nombre_y': 'PROPIEDAD', 'nombre_x': 'UNIDAD', 'tipo': 'TIPO'}, inplace=True)
                                df_base = df_base.sort_values(by=['PROPIEDAD', 'UNIDAD'])
                                
                                etiqueta_prop = "GLOBAL"
                            else:
                                df_base = pd.DataFrame()
                                etiqueta_prop = "Vacio"
                    else:
                        # Si es solo la propiedad actual, usamos la tabla visual que ya está en pantalla
                        df_base = df_uni_display.copy()
                        df_base.insert(0, 'PROPIEDAD', prop_maestra)
                        etiqueta_prop = prop_maestra.replace(' ', '_')
                        
                    # --- PASO B: APLICAR FILTRO DE ESTADO A LA BASE ---
                    if not df_base.empty:
                        if filtro_estado != "TODAS":
                            df_final = df_base[df_base['ESTADO'] == filtro_estado].copy()
                            etiqueta_est = filtro_estado.split(" ")[1].lower().replace(".", "")
                        else:
                            df_final = df_base.copy()
                            etiqueta_est = "todas"
                            
                        # Si tras filtrar queda vacía, avisamos
                        if df_final.empty:
                            st.warning(f"⚠️ No hay unidades con estado '{filtro_estado}' para este alcance.")
                            if st.button("❌ Cerrar Panel"):
                                st.session_state.modo_unidad = "NADA"
                                st.rerun()
                        else:
                            # 🛡️ Lógica para el título del PDF
                            titulo_encabezado = "INMOLEASING"
                            if not df_ops.empty and len(df_ops) == 1:
                                titulo_encabezado = str(df_ops.iloc[0]['nombre']).upper()

                            # 🚀 LÁNZALO A NUESTRO MOTOR CENTRAL
                            panel_reportes_y_compartir(
                                df_datos=df_final, 
                                nombre_base=f"unidades_{etiqueta_prop}_{etiqueta_est}",
                                modulo_origen=f"Unidades",
                                funcion_pdf=lambda df: generar_pdf_unidades(df, titulo_encabezado),
                                df_operadores=df_ops,
                                supabase=supabase,
                                usuario_actual=st.session_state.usuario.get("nombre", "ADMIN"),
                                clave_estado_cerrar="modo_unidad"
                            )
                    else:
                        st.info("No hay datos registrados en el sistema para exportar.")
                        if st.button("❌ Cerrar Panel"):
                            st.session_state.modo_unidad = "NADA"
                            st.rerun()


    # ========================================
    # TAB 3: MANDATOS (Contratos y Finanzas)
    # ========================================
    with tab3:
        if 'modo_mandato' not in st.session_state:
            st.session_state.modo_mandato = "NADA"

        # 🛡️ BLINDAJE DE MONEDA ESTRICTO
        moneda_sesion = st.session_state.get("moneda_usuario", "EUR")
        simbolo_mon = "€" if moneda_sesion == "EUR" else "$"

        st.write("CONTRATO DE MANDATO")
                    
        # --- 1. CARGA DE DATOS BASE (¡FILTRADA POR REGIÓN!) ---
        try:
            res_inm = supabase.table("inmuebles").select("id, nombre, moneda").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
            df_inm_m = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
            
            res_prop = supabase.table("propietarios").select("id, nombre, cuenta_banco").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
            df_prop_m = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
            
            # MAGIA: .eq("moneda", moneda_sesion)
            res_man = supabase.table("mandatos").select("*, inmuebles(nombre), propietarios!mandatos_id_propietario_fkey(nombre)").neq("estado_contrato", "FINALIZADO").eq("moneda", moneda_sesion).execute()
            df_man = pd.DataFrame(res_man.data) if res_man.data else pd.DataFrame()
        except Exception as e:
            df_inm_m, df_prop_m, df_man = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            st.warning(f"⚠️ Cargando datos: {e}")

        # --- 2. GRID DE MANDATOS ---
        if not df_man.empty and not df_inm_m.empty and not df_prop_m.empty:
            df_view_display = df_man.copy()
            df_view_display['INMUEBLE'] = df_view_display['inmuebles'].apply(lambda x: x['nombre'] if isinstance(x, dict) else "N/A")
            df_view_display['TITULAR'] = df_view_display['propietarios'].apply(lambda x: x['nombre'] if isinstance(x, dict) else "N/A")
            
            def visor_docs(row):
                iconos = []
                if row.get('url_contrato'): iconos.append("📄")
                if row.get('url_empadronamiento'): iconos.append("🏠")
                if row.get('url_inventario'): iconos.append("📦")
                if row.get('url_suministros'): iconos.append("💧")
                return " ".join(iconos) if iconos else "➖"

            df_view_display['DOCS'] = df_view_display.apply(visor_docs, axis=1)
            df_view_display['RENTA'] = pd.to_numeric(df_view_display['ingreso_garantizado']).fillna(0).apply(lambda x: f"{simbolo_mon} {x:,.2f}")
            df_view_display.rename(columns={'porcentaje_pago_1': '% COBRO', 'estado_financiero': 'FINANZAS'}, inplace=True)
            
            st.dataframe(df_view_display[['INMUEBLE', 'TITULAR', '% COBRO', 'RENTA', 'FINANZAS', 'DOCS']], use_container_width=True, hide_index=True)
        else:
            st.info(f"ℹ️ No hay mandatos vigentes en el entorno {moneda_sesion}.")

# --- 3. BARRA DE HERRAMIENTAS ---
        st.markdown("---")
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns([1.5, 1.5, 1.5, 1.6, 1.5, 1.5])
        
        if m_c1.button("➕ Nuevo", key="btn_nuevo_man", use_container_width=True): st.session_state.modo_mandato = "CREAR"; st.rerun()
        if not df_man.empty:
            if m_c2.button("⚙️ Gestionar", key="btn_edit_man", use_container_width=True): st.session_state.modo_mandato = "EDITAR"; st.rerun()
            if m_c3.button("📄 Contrato", key="btn_gen_doc_man", use_container_width=True): st.session_state.modo_mandato = "GENERAR_CONTRATO"; st.rerun()
            if m_c4.button("📁 Documentos", key="btn_docs_man", use_container_width=True): st.session_state.modo_mandato = "DOCUMENTOS"; st.rerun()
            if m_c5.button("📜 Historial", key="btn_hist_man", use_container_width=True): st.session_state.modo_mandato = "HISTORIAL"; st.rerun()
            if m_c6.button("📊 Reportes", key="btn_rep_man", use_container_width=True): st.session_state.modo_mandato = "REPORTES"; st.rerun()        # --- 4. PANEL CREAR ---
        if st.session_state.modo_mandato == "CREAR":
            from dateutil.relativedelta import relativedelta
            st.markdown("---")
            with st.form("form_nuevo_mandato_pro", clear_on_submit=False):
                st.markdown("**Nuevo Contrato de Gestión**")
                
                if df_inm_m.empty or df_prop_m.empty:
                    st.error(f"Necesitas crear al menos una propiedad y un propietario en {moneda_sesion} antes de crear un mandato.")
                else:
                    st.write("**1. Titularidad y Propiedad**")
                    col_inm, col_op = st.columns(2)
                    m_inm_sel = col_inm.selectbox("Propiedad a gestionar *", df_inm_m['nombre'].tolist())
                    id_inm = df_inm_m[df_inm_m['nombre'] == m_inm_sel].iloc[0]['id']
                    
                    # 💡 SOLUCIÓN: El operador ahora se selecciona directamente para el mandato, auto-asignando si solo hay uno
                    try:
                        res_ops_man = supabase.table("operadores").select("id, nombre").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
                        df_ops_man = pd.DataFrame(res_ops_man.data) if res_ops_man.data else pd.DataFrame()
                        
                        if len(df_ops_man) == 1:
                            nom_op = df_ops_man.iloc[0]['nombre']
                            id_op_heredado = int(df_ops_man.iloc[0]['id'])
                            #col_op.info(f"🏢 **Operador:** {nom_op} (Auto-asignado)")
                        elif len(df_ops_man) > 1:
                            m_op_sel = col_op.selectbox("Operador que facturará *", df_ops_man['nombre'].tolist())
                            id_op_heredado = int(df_ops_man[df_ops_man['nombre'] == m_op_sel].iloc[0]['id'])
                            nom_op = m_op_sel
                        else:
                            col_op.warning("No hay operadores activos en esta región.")
                            id_op_heredado = None
                            nom_op = "No definido"
                    except:
                        id_op_heredado = None
                        nom_op = "No definido"
                    st.write("**Titular 1 (Principal)**")
                    c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 4.6])
                    m_prop_sel_1 = c1.selectbox("Propietario 1 *", df_prop_m['nombre'].tolist(), key="p1")
                    iban_db = df_prop_m[df_prop_m['nombre'] == m_prop_sel_1].iloc[0]['cuenta_banco'] or ""
                    m_porc_prop_1 = c2.number_input("% Legal", 0.0, 100.0, 100.0, key="pp1")
                    m_porc_pago_1 = c3.number_input("% Cobro", 0.0, 100.0, 100.0, key="pg1")
                    m_iban_1 = c4.text_input("IBAN / Cuenta Pago 1 *", value=iban_db, key="ib1")
                    
                    st.write("**Titular 2 (Opcional)**")
                    c5, c6, c7, c8 = st.columns([3, 1.2, 1.2, 4.6])
                    opciones_p2 = ["-- Ninguno --"] + df_prop_m['nombre'].tolist()
                    m_prop_sel_2 = c5.selectbox("Propietario 2", opciones_p2, key="p2")
                    m_porc_prop_2 = c6.number_input("% Legal 2", 0.0, 100.0, 0.0, key="pp2")
                    m_porc_pago_2 = c7.number_input("% Cobro 2", 0.0, 100.0, 0.0, key="pg2")
                    m_iban_2 = c8.text_input("IBAN / Cuenta Pago 2", key="ib2")

                    st.write("**2. Cronograma (Smart Dates)**")
                    d1, d2, d3 = st.columns(3)
                    f_suscripcion = d1.date_input("Fecha de Suscripción / Firma *")
                    duracion_anos = d2.number_input("Duración Contrato (Años)", 1, 20, 5)
                    meses_aviso = d3.number_input("Meses Preaviso No Renovación", 1, 12, 2)

                    d4, d5, d6 = st.columns(3)
                    f_entrega = d4.date_input("Fecha Entrega Llaves *")
                    
                    # 💡 SOLUCIÓN: Carencia exacta por fecha fin, no por meses genéricos
                    f_fin_carencia = d5.date_input("Fecha Fin de Carencia *", value=f_entrega)
                    
                    f_vencimiento = f_suscripcion + relativedelta(years=duracion_anos)
                    
                    # 🚀 Lógica contable NIIF: El pago se inicia EL DÍA DESPUÉS de terminar la carencia
                    f_inicio_pagos = f_fin_carencia + relativedelta(days=1)
                    
                    f_limite_aviso = f_vencimiento - relativedelta(months=meses_aviso)
                    c_res1, c_res2 = st.columns([8.5, 1.5])
                    c_res1.success(f"🗓️ **Resumen:** Pagos inician: **{f_inicio_pagos}** | Vence: **{f_vencimiento}** | Preaviso: **{f_limite_aviso}**")
                    c_res2.form_submit_button("🔄 Recalcular")
                    
                    st.write("**3. Acuerdo Económico**")
                    e1, e2, e3 = st.columns(3)
                    m_renta = e1.number_input(f"Renta Garantizada ({simbolo_mon}) *", min_value=0.0, step=50.0)
                    m_fianza = e2.number_input(f"Fianza a Entregar ({simbolo_mon}) *", min_value=0.0, step=50.0)
                    m_act = e3.selectbox("Actualización Anual", ["IPC", "FIJO", "NO APLICA"])

                    #st.info("🛡️ Cláusula de protección (Amortización de Mejoras)")
                    c_ind1, c_ind2 = st.columns([2, 1])
                    m_tipo_ind_ui = c_ind1.selectbox("Modalidad de Penalización", ["NO APLICA", "MONTO FIJO (Cualquier momento)", "AMORTIZACIÓN DECRECIENTE (5 Años)"])
                    mapa_ind = {"NO APLICA": "NINGUNA", "MONTO FIJO (Cualquier momento)": "FIJA", "AMORTIZACIÓN DECRECIENTE (5 Años)": "DECRECIENTE_5Y"}
                    m_tipo_ind_db = mapa_ind[m_tipo_ind_ui]
                    m_indemnizacion = c_ind2.number_input(f"Monto Base 100% ({simbolo_mon})", min_value=0.0, step=50.0)

                    st.write("**4. Documentación Escaneada**")
                    cd1, cd2 = st.columns(2)
                    doc_contrato = cd1.file_uploader("Contrato Firmado", type=["pdf", "jpg", "png"])
                    doc_empadrona = cd2.file_uploader("Aut. Empadronamiento", type=["pdf", "jpg", "png"])
                    cd3, cd4 = st.columns(2)
                    doc_inv = cd3.file_uploader("Acta Inventario", type=["pdf", "jpg", "png"])
                    doc_sum = cd4.file_uploader("Recibos Suministros", type=["pdf", "jpg", "png"])

                    st.markdown("---")
                    col_b1, col_b2, _ = st.columns([2.0, 1.5, 6.5])
                    if col_b1.form_submit_button("💾 Generar Mandato"):
                        if (m_porc_pago_1 + m_porc_pago_2) > 100.1 or (m_porc_prop_1 + m_porc_prop_2) > 100.1:
                            st.error("❌ Los porcentajes superan el 100%.")
                        elif not id_op_heredado:
                            st.error("❌ Debes seleccionar un operador fiscal.")
                        else:
                            with st.spinner("Registrando contrato y vinculando operador..."):
                                try:
                                    id_p1 = df_prop_m[df_prop_m['nombre'] == m_prop_sel_1].iloc[0]['id']
                                    id_p2 = int(df_prop_m[df_prop_m['nombre'] == m_prop_sel_2].iloc[0]['id']) if m_prop_sel_2 != "-- Ninguno --" else None
                                    
                                    def subir_pdf(archivo, prefijo):
                                        if not archivo: return None
                                        ext = archivo.name.split('.')[-1].lower()
                                        tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                        n_nube = f"{prefijo}_{id_inm}_{int(time.time())}.{ext}"
                                        supabase.storage.from_("documentos_mandatos").upload(n_nube, archivo.getvalue(), file_options={"content-type": tipo_mime})
                                        return supabase.storage.from_("documentos_mandatos").get_public_url(n_nube)

                                    url_c = subir_pdf(doc_contrato, "contrato")
                                    url_e = subir_pdf(doc_empadrona, "empadronamiento")
                                    url_i = subir_pdf(doc_inv, "inventario")
                                    url_s = subir_pdf(doc_sum, "suministros")

                                    datos = {
                                        "id_inmueble": int(id_inm), "id_propietario": int(id_p1), "id_propietario_2": id_p2,
                                        "id_operador": int(id_op_heredado), "moneda": moneda_sesion, 
                                        "porcentaje_propiedad": m_porc_prop_1, "porcentaje_propiedad_2": m_porc_prop_2,
                                        "porcentaje_pago_1": m_porc_pago_1, "porcentaje_pago_2": m_porc_pago_2,
                                        "cuenta_pago": m_iban_1, "cuenta_pago_2": m_iban_2,
                                        "ingreso_garantizado": m_renta, "valor_fianza": m_fianza,
                                        "tipo_actualizacion": m_act, "tipo_indemnizacion": m_tipo_ind_db, 
                                        "indemnizacion_anticipada": m_indemnizacion,
                                        "fecha_suscripcion": str(f_suscripcion), "fecha_entrega": str(f_entrega),
                                        "fecha_inicio_pagos": str(f_inicio_pagos), "fecha_terminacion": str(f_vencimiento),
                                        "fecha_aviso_no_renovacion": str(f_limite_aviso), "fecha_fin_carencia": str(f_fin_carencia),
                                        "url_contrato": url_c, "url_empadronamiento": url_e,
                                        "url_inventario": url_i, "url_suministros": url_s,
                                        "estado_contrato": "FIRMADO", "estado_financiero": "PENDIENTE_FIANZA"
                                    }
                                    res = supabase.table("mandatos").insert(datos).execute()
                                    id_mandato_nuevo = res.data[0]['id']
                                    
                                    # 🚀 MOTOR AUTOMÁTICO CONTABLE: FIANZAS Y TERCEROS
                                    # 1. Buscar Catálogo de Cuentas Inteligente
                                    id_cta_fianza, id_cta_pasivo = None, None
                                    try:
                                        res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo, nombre").eq("moneda", moneda_sesion).execute()
                                        df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
                                        if not df_ctas.empty:
                                            df_ctas['cod_str'] = df_ctas['codigo'].astype(str)
                                            df_ctas['nom_low'] = df_ctas['nombre'].astype(str).str.lower()
                                            df_ctas['cod_str'] = df_ctas['codigo'].astype(str).str.strip() # Limpiamos espacios invisibles
                                            df_ctas['nom_low'] = df_ctas['nombre'].astype(str).str.lower()
                                            
                                            # --- 🛑 PRUEBA DEL ÁCIDO ---
                                            #@st.error(f"🛑 DETENIDO: Encontré {len(df_ctas)} cuentas en la BD.")
                                            #st.warning(f"¿Python puede ver la 260000?: {'260000' in df_ctas['cod_str'].values}")
                                            #st.stop() # Esto APAGA el motor de golpe. ¡Es imposible que genere un asiento!
                                            
                                            # 🎯 Buscamos Activo: Fianzas Constituidas (Con estricto orden de prioridad)    
                                        # 🎯 Buscamos Activo: Fianzas Constituidas (Con estricto orden de prioridad)
                                            for pref in ['260', '26', '15', '11']:
                                                fianzas = df_ctas[df_ctas['cod_str'].str.startswith(pref)]
                                                if not fianzas.empty: 
                                                    id_cta_fianza = int(fianzas.iloc[0]['id'])
                                                    break
                                            if not id_cta_fianza: # Fallback de emergencia por nombre
                                                fianzas = df_ctas[df_ctas['nom_low'].str.contains('fianza|deposito', regex=True)]
                                                if not fianzas.empty: id_cta_fianza = int(fianzas.iloc[0]['id'])
                                            
                                            # 🎯 LA MAGIA DEL TERCERO: Pasivo Acreedores (Con estricto orden de prioridad)
                                            # Intento 1: Cuenta 410 específica del tercero
                                            cta_tercero = df_ctas[(df_ctas['cod_str'].str.startswith('410')) & (df_ctas['nom_low'].str.contains(str(m_prop_sel_1).lower(), na=False, regex=False))]
                                            if not cta_tercero.empty:
                                                id_cta_pasivo = int(cta_tercero.iloc[0]['id'])
                                            else:
                                                # Intento 2: Cuentas genéricas en ESTRICO ORDEN (Obligando a agarrar la 410000 primero)
                                                for pref in ['410000', '4100', '22', '41']:    
                                                    pasivos = df_ctas[(df_ctas['cod_str'].str.startswith(pref)) & (~df_ctas['nom_low'].str.contains('impuesto|retenci', regex=True))]
                                                    if not pasivos.empty:
                                                        id_cta_pasivo = int(pasivos.iloc[0]['id'])
                                                        break
                                    except Exception as e:
                                        pass

                                    # 🚀 2. CAUSACIÓN ÚNICAMENTE DE LA FIANZA
                                    if m_fianza > 0:
                                        # A. Registrar Fianza Operativa
                                        supabase.table("fin_fianzas").insert({"tipo": "ENTREGADA", "modulo_origen": "MANDATOS", "id_origen": id_mandato_nuevo, "id_inmueble": int(id_inm), "tercero": m_prop_sel_1, "importe_inicial": m_fianza, "saldo_pendiente": m_fianza, "moneda": moneda_sesion, "estado": "REGISTRADA"}).execute()
                                        
                                        # B. Orden de Pago (CxP Tesorería)
                                        supabase.table("fin_cuentas_pagar").insert({"modulo_origen": "MANDATOS", "id_origen": id_mandato_nuevo, "acreedor": m_prop_sel_1, "concepto": f"Pago de Fianza - Mandato {id_mandato_nuevo}", "monto_total": m_fianza, "saldo_pendiente": m_fianza, "moneda": moneda_sesion, "estado": "PENDIENTE"}).execute()
                                        
                                        # C. Asiento Contable
                                        if id_cta_fianza and id_cta_pasivo:
                                            res_ast_f = supabase.table("fin_asientos").insert({"fecha_contable": str(f_suscripcion), "descripcion": f"CAUSACIÓN FIANZA ENTREGADA - MANDATO {id_mandato_nuevo}", "concepto_general": "Fianza a Propietario", "origen": "MODULO_MANDATOS", "moneda": moneda_sesion, "estado": "CONTABILIZADO"}).execute()
                                            id_ast_f = res_ast_f.data[0]['id']
                                            supabase.table("fin_apuntes").insert([
                                                {"id_asiento": id_ast_f, "id_cuenta_contable": id_cta_fianza, "debito": float(m_fianza), "credito": 0.0, "descripcion_linea": "Fianza constituida a largo plazo", "tercero": m_prop_sel_1},
                                                {"id_asiento": id_ast_f, "id_cuenta_contable": id_cta_pasivo, "debito": 0.0, "credito": float(m_fianza), "descripcion_linea": "CxP Fianza a Propietario", "tercero": m_prop_sel_1}
                                            ]).execute()

                                    # ⚠️ NOTA: La causación de la Renta Garantizada se trasladó al Motor Mensual de Arrendamientos.

                                    # 🚀 3. MOTOR AUTOMÁTICO: Auditoría Estricta del Evento
                                    periodo_actual = pd.Timestamp.now().strftime("%Y-%m")
                                    supabase.table("sys_motor_automatico_logs").insert({
                                        "evento": "contrato_activado", "modulo_origen": "MANDATOS", "id_origen": id_mandato_nuevo,
                                        "regla_evaluada": "SI mandato_activo -> generar_cxp_y_fianza",
                                        "accion_ejecutada": "generar_cxp, generar_asiento, registrar_fianza",
                                        "periodo": periodo_actual, "resultado": "EXITO",
                                        "detalles": f"CxP y Asiento: {m_renta} | Fianza: {m_fianza}"
                                    }).execute()

                                    # Log Tradicional Historial de Inmuebles
                                    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                                    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                                    
                                    supabase.table("historial_mandatos").insert({
                                        "id_mandato": id_mandato_nuevo, 
                                        "accion": f"CREACIÓN MANDATO (Firma: {f_suscripcion}). Operador: {nom_op}",
                                        "usuario": usuario_actual
                                    }).execute()
                                    
                                    # 🚀 4. EL LOG GLOBAL QUE FALTABA (Dashboard de Actividad Principal)
                                    log_accion(supabase, usuario_actual, "CREAR MANDATO", f"Propiedad: {m_inm_sel} | Propietario: {m_prop_sel_1}")

                                    st.success("✅ Mandato registrado. Motor automático: CxP, Asiento Contable y Fianza generadas.")
                                    st.session_state.modo_mandato = "NADA"; time.sleep(2.5); st.rerun()
                                except Exception as e: st.error(f"❌ Error al orquestar: {e}")

                    if col_b2.form_submit_button("❌ Cancelar"): st.session_state.modo_mandato = "NADA"; st.rerun()


        elif st.session_state.modo_mandato == "DOCUMENTOS" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 📁 Bóveda de Documentos Legales")
            op_man_docs = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_doc = st.selectbox("Selecciona el Mandato para ver sus archivos:", op_man_docs)
            if m_sel_doc:
                idx = op_man_docs.index(m_sel_doc)
                d_m = df_man.iloc[idx]
                c1, c2, c3, c4 = st.columns(4)
                def tarjeta_doc(columna, titulo, url_doc, icono):
                    with columna:
                        st.markdown(f"**{icono} {titulo}**")
                        if url_doc and str(url_doc).strip() != "None" and str(url_doc).strip() != "":
                            st.success("✅ Guardado")
                            st.markdown(f"[📥 Abrir Documento]({url_doc})")
                        else: st.warning("❌ Pendiente")
                tarjeta_doc(c1, "Contrato", d_m.get('url_contrato'), "📄")
                tarjeta_doc(c2, "Empadrona.", d_m.get('url_empadronamiento'), "🏠")
                tarjeta_doc(c3, "Inventario", d_m.get('url_inventario'), "📦")
                tarjeta_doc(c4, "Suministros", d_m.get('url_suministros'), "💧")
            st.markdown("---")
            if st.button("❌ Cerrar Bóveda"): st.session_state.modo_mandato = "NADA"; st.rerun()

        elif st.session_state.modo_mandato == "HISTORIAL" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 📜 Historial y Auditoría del Contrato")
            op_man_hist = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_hist = st.selectbox("Selecciona el Mandato para ver su actividad:", op_man_hist)
            if m_sel_hist:
                idx = op_man_hist.index(m_sel_hist)
                id_m = df_man.iloc[idx]['id']
                try:
                    res_hist = supabase.table("historial_mandatos").select("fecha_evento, accion, usuario").eq("id_mandato", int(id_m)).order("fecha_evento", desc=True).execute()
                    df_h = pd.DataFrame(res_hist.data) if res_hist.data else pd.DataFrame()
                except Exception as e: df_h = pd.DataFrame()
                if not df_h.empty:
                    df_h['FECHA'] = pd.to_datetime(df_h['fecha_evento']).dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(df_h[['FECHA', 'accion', 'usuario']].copy(), use_container_width=True, hide_index=True)
                else: st.info("ℹ️ No hay registros en el historial.")
            st.markdown("---")
            if st.button("❌ Cerrar Historial"): st.session_state.modo_mandato = "NADA"; st.rerun()
# --- PANEL: GENERADOR DE CONTRATO (BORRADOR INTERACTIVO) ---
        elif st.session_state.modo_mandato == "GENERAR_CONTRATO" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 📄 Generador Interactivo de Contratos Legales")
            
            op_man_gen = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_gen = st.selectbox("1. Selecciona el Mandato para redactar su contrato:", op_man_gen)
            
            if m_sel_gen:
                idx = op_man_gen.index(m_sel_gen)
                d_m = df_man.iloc[idx]
                id_m = str(d_m['id'])
                
                # Extracción de datos maestros
                res_inm = supabase.table("inmuebles").select("nombre, ciudad, referencia_catastral").eq("id", d_m['id_inmueble']).execute()
                datos_inm = res_inm.data[0] if res_inm.data else {"nombre": "N/A", "ciudad": "N/A", "referencia_catastral": "N/A"}
                
                # Etiqueta dinámica según el país
                lbl_catastro = "Matrícula Inmobiliaria" if moneda_sesion == "COP" else "Referencia Catastral"
                res_p1 = supabase.table("propietarios").select("nombre, identificacion").eq("id", d_m['id_propietario']).execute()
                datos_p1 = res_p1.data[0] if res_p1.data else {"nombre": "N/A", "identificacion": "N/A"}
                
                datos_p2 = None
                if d_m.get('id_propietario_2'):
                    res_p2 = supabase.table("propietarios").select("nombre, identificacion").eq("id", d_m['id_propietario_2']).execute()
                    datos_p2 = res_p2.data[0] if res_p2.data else None
                    
                # Extracción de la DB incluyendo la dirección y el correo
                res_op = supabase.table("operadores").select("nombre, identificacion, direccion, correo").eq("id", d_m['id_operador']).execute()
                datos_op = res_op.data[0] if res_op.data else {"nombre": "N/A", "identificacion": "N/A", "direccion": "DIRECCIÓN NO REGISTRADA", "correo": "CORREO NO REGISTRADO"}
                # 🌍 Lógica de Tratamiento y Documentos por Región
                if moneda_sesion == "EUR":
                    opc_trat_op = ["D.", "Dña."]
                    opc_doc_op = ["DNI", "NIE"]
                    lbl_doc_op = "DNI / NIE del Rep."
                    lbl_doc_empresa = "CIF"
                elif moneda_sesion == "COP":
                    opc_trat_op = ["Sr.", "Sra."]
                    opc_doc_op = ["CC", "NIT"]
                    lbl_doc_op = "CC / NIT del Rep."
                    lbl_doc_empresa = "NIT"
                else:
                    opc_trat_op = ["D.", "Dña.", "Sr.", "Sra."]
                    opc_doc_op = ["DNI", "NIE", "CC", "NIT"]
                    lbl_doc_op = "Identificación"
                    lbl_doc_empresa = "Identificación"

                # Interfaz "Listbox" Inteligente para Representantes
                st.write("**2. Firma de la Gestora**")
                c_rep1, c_rep2 = st.columns(2)
                
                # 🧠 Diccionario inteligente (Nombre: DNI/NIE)
                if 'dict_admins' not in st.session_state:
                    st.session_state.dict_admins = {"JORGE SALAZAR": "Y9720117D", "GIANFRANCO VOLI": "X2211568A"}
                    
                opciones_admins = list(st.session_state.dict_admins.keys()) + ["Añadir nuevo..."]
                sel_admin = c_rep1.selectbox("Representante Legal (Historial)", opciones_admins)
                
                if sel_admin == "Añadir nuevo...":
                    admin_nombre = c_rep1.text_input("Nombre del nuevo Representante *")
                    admin_id = c_rep2.text_input(f"{lbl_doc_op} *")
                else:
                    admin_nombre = sel_admin
                    # Autocompleta el ID basado en el nombre seleccionado
                    admin_id = c_rep2.text_input(lbl_doc_op, value=st.session_state.dict_admins[sel_admin])                
                
                # Fila extra para Tratamiento y Tipo de Documento
                c_rep3, c_rep4 = st.columns(2)
                trat_admin = c_rep3.radio("Tratamiento Gestor:", opc_trat_op, horizontal=True)
                tipo_doc_admin = c_rep4.radio("Tipo Documento:", opc_doc_op, horizontal=True)
                
                st.markdown("---")
                st.write("**3. Tratamiento de los Propietarios**")
                c_trat1, c_trat2 = st.columns(2)
                
                # 🌍 Lógica de Tratamiento por Región
                if moneda_sesion == "EUR":
                    opciones_tratamiento = ["D.", "Dña."]
                elif moneda_sesion == "COP":
                    opciones_tratamiento = ["Sr.", "Sra."]
                else:
                    opciones_tratamiento = ["D.", "Dña.", "Sr.", "Sra."]
                
                # Botones de radio para el Propietario 1
                trat_p1 = c_trat1.radio(f"Tratamiento para: **{datos_p1['nombre']}**", opciones_tratamiento, horizontal=True)
                
                # Botones de radio para el Propietario 2 (Solo si existe)
                trat_p2 = None
                if datos_p2:
                    trat_p2 = c_trat2.radio(f"Tratamiento para: **{datos_p2['nombre']}**", opciones_tratamiento, horizontal=True)
                st.markdown("---")
                
                # ⚙️ 1. CÁLCULOS Y PLANTILLA EN VIVO
                # 🧠 Lógica Gramatical Dinámica
                if datos_p2:
                    bloque_props = f"De una parte, {trat_p1} {datos_p1['nombre']} con DNI {datos_p1['identificacion']} y {trat_p2} {datos_p2['nombre']} con DNI {datos_p2['identificacion']}, propietarios del inmueble sito en {datos_inm['nombre']}, en adelante, LOS PROPIETARIOS."
                    txt_propietario = "LOS PROPIETARIOS"
                    txt_titularidad = "son titulares plenos"
                    # Inyectamos ambos nombres en MAYÚSCULAS (para forzar negrita) y con 4 líneas de espacio
                    txt_firmas_propietarios = f"{trat_p1.upper()} {datos_p1['nombre'].upper()}\n\n\n\n{trat_p2.upper()} {datos_p2['nombre'].upper()}"
                else:
                    bloque_props = f"De una parte, {trat_p1} {datos_p1['nombre']} con DNI {datos_p1['identificacion']}, propietario del inmueble sito en {datos_inm['nombre']}, en adelante, EL PROPIETARIO."
                    txt_propietario = "EL PROPIETARIO"
                    txt_titularidad = "es titular pleno"
                    # Inyectamos el único nombre en MAYÚSCULAS
                    txt_firmas_propietarios = f"{trat_p1.upper()} {datos_p1['nombre'].upper()}"
                # Cálculos de Fechas
                f_firma = pd.to_datetime(d_m['fecha_suscripcion'])
                f_vence = pd.to_datetime(d_m['fecha_terminacion'])
                f_entrega = pd.to_datetime(d_m['fecha_entrega'])
                f_pagos = pd.to_datetime(d_m['fecha_inicio_pagos'])
                f_aviso = pd.to_datetime(d_m['fecha_aviso_no_renovacion'])
                
                anos = (f_vence.year - f_firma.year) if pd.notna(f_vence) and pd.notna(f_firma) else 5
                meses_preaviso = (f_vence.year - f_aviso.year) * 12 + (f_vence.month - f_aviso.month) if pd.notna(f_vence) and pd.notna(f_aviso) else 2
                meses_carencia = (f_pagos.year - f_entrega.year) * 12 + (f_pagos.month - f_entrega.month) if pd.notna(f_pagos) and pd.notna(f_entrega) else 0
                
                # 🗓️ Formateador de Fecha al Español Legal
                meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                try:
                    fecha_firma_formateada = f"{f_firma.day} de {meses_es[f_firma.month - 1]} de {f_firma.year}"
                except:
                    fecha_firma_formateada = str(d_m.get('fecha_suscripcion', 'N/A'))                
                

                try:
                    fecha_entrega_formateada = f"{f_entrega.day} de {meses_es[f_entrega.month - 1]} de {f_entrega.year}"
                except:
                    fecha_entrega_formateada = str(d_m.get('fecha_entrega', 'N/A'))

                # 🗓️ Formateador para las nuevas fechas de Carencia
                try:
                    fecha_inicio_pagos_formateada = f"{f_pagos.day} de {meses_es[f_pagos.month - 1]} de {f_pagos.year}"
                except:
                    fecha_inicio_pagos_formateada = str(d_m.get('fecha_inicio_pagos', 'N/A'))

                try:
                    f_fin_carencia = pd.to_datetime(d_m.get('fecha_fin_carencia'))
                    fecha_fin_carencia_formateada = f"{f_fin_carencia.day} de {meses_es[f_fin_carencia.month - 1]} de {f_fin_carencia.year}"
                except:
                    fecha_fin_carencia_formateada = str(d_m.get('fecha_fin_carencia', 'N/A'))

                # 🔢 Formateador Legal de Números a Letras (Cero decimales)
                def num_a_letras(n):
                    n = int(n)
                    if n == 0: return "cero"
                    un = ["", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
                    dec = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
                    esp = {10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince", 16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve", 20: "veinte", 21: "veintiún", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro", 25: "veinticinco", 26: "veintiséis", 27: "veintisiete", 28: "veintiocho", 29: "veintinueve"}
                    cen = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
                    def conv(num):
                        if num == 100: return "cien"
                        if num in esp: return esp[num]
                        c, d, u = num // 100, (num % 100) // 10, num % 10
                        r = cen[c]
                        if d > 2: r += (" " if r else "") + dec[d] + (" y " + un[u] if u > 0 else "")
                        elif d == 0 and u > 0: r += (" " if r else "") + un[u]
                        return r.strip()
                    m, resto = n // 1000, n % 1000
                    res = "mil" if m == 1 else (conv(m) + " mil" if m > 1 else "")
                    return (res + (" " if res else "") + conv(resto)).strip()

                val_renta = int(float(d_m.get('ingreso_garantizado', 0) or 0))
                val_fianza = int(float(d_m.get('valor_fianza', 0) or 0))
                val_indem = int(float(d_m.get('indemnizacion_anticipada', 0) or 0))
                
                moneda_legal = "EUROS" if moneda_sesion == "EUR" else "PESOS"
                
                txt_renta = f"{num_a_letras(val_renta)} ({val_renta}) {moneda_legal}"
                txt_fianza = f"{num_a_letras(val_fianza)} ({val_fianza}) {moneda_legal}"
                txt_indem = f"{num_a_letras(val_indem)} ({val_indem}) {moneda_legal}"
                
                # 📝 MOTOR DE PLANTILLA
                plantilla = f"""CONTRATO DE GESTIÓN INTEGRAL DE ALQUILER POR HABITACIONES CON GARANTÍA DE INGRESOS

REUNIDOS
{bloque_props}

Y de otra, {datos_op['nombre']}, con {lbl_doc_empresa} {datos_op['identificacion']} y domicilio en {datos_op.get('direccion', 'DIRECCIÓN NO REGISTRADA')}, representada por {trat_admin} {admin_nombre} con {tipo_doc_admin} {admin_id}, en su condición de administrador, en adelante, LA GESTORA.

MANIFIESTAN
1) Que {txt_propietario} {txt_titularidad} del inmueble descrito, con {lbl_catastro} {datos_inm.get('referencia_catastral', 'N/A')}.
2) Que LA GESTORA desarrolla actividad empresarial de gestión inmobiliaria. 
3) Que ambas partes desean formalizar contrato de gestión integral con garantía de ingresos.

ACUERDAN
PRIMERO. Naturaleza jurídica
1) El presente contrato tiene naturaleza mercantil. 
2) No constituye contrato de arrendamiento entre las partes.
3) La Gestora no adquiere derecho real ni posesión plena del inmueble. 
4) {txt_propietario.capitalize()} mantiene la condición de arrendador frente a los ocupantes finales.

SEGUNDO. Objeto
La Gestora asumirá la gestión integral del alquiler por habitaciones del inmueble, incluyendo: Estudio de viabilidad, Adecuación no estructural, Captación y selección de ocupantes, Formalización de contratos temporales, Gestión de cobros, Gestión de incidencias, Supervisión periódica, Coordinación de mantenimiento ordinario, Gestión de empadronamiento.

TERCERO. Garantía de ingresos
La Gestora garantiza a {txt_propietario} un ingreso mínimo mensual de {txt_renta}. El pago se efectuará dentro de los cinco primeros días de cada mes. La garantía opera con independencia del nivel de ocupación. A la firma del presente contrato la Gestora pagará el valor de {txt_fianza} como fianza.

CUARTO. Retribución de la Gestora
La Gestora percibirá como honorarios la diferencia entre ingresos brutos obtenidos y el ingreso mínimo garantizado. La Gestora emitirá factura mensual con IVA conforme a la normativa vigente.

QUINTO. Duración
Duración de {anos} años, con prórroga automática a menos que alguna de las partes notifique a la otra su decisión de no hacerlo con una antelación no inferior a {meses_preaviso} meses.

SEXTO. Inversión
La Gestora podrá realizar mejoras no estructurales. {txt_propietario.capitalize()} recibió y aceptó de la Gestora informe previo con detalle de inversión. Las mejoras quedarán en beneficio del inmueble. Esto excluye muebles y enseres.

SÉPTIMO. Gastos
A cargo de {txt_propietario}: IBI, Comunidad y Seguro de hogar con responsabilidad civil.
A cargo de la Gestora: Suministros, Internet, Gestión Operativa y Tasa de Basuras.

OCTAVO. Responsabilidad
La Gestora responderá frente a {txt_propietario} por negligencia grave en la gestión. {txt_propietario.capitalize()} mantendrá responsabilidad estructural del inmueble.

NOVENO. Jurisdicción 
Juzgados y Tribunales de {datos_inm['ciudad'].capitalize()}.

DÉCIMO. Recuperación anticipada por venta
En caso de que {txt_propietario} decida vender el inmueble antes del vencimiento del contrato, deberá comunicarlo con un preaviso mínimo de 90 días. {txt_propietario.capitalize()} deberá abonar a la Gestora el importe de la inversión de {txt_indem}. La transmisión del inmueble quedará supeditada a la liquidación previa de las cantidades indicadas y a la terminación de los contratos vigentes de alquiler de las habitaciones. Las mejoras quedarán incorporadas al inmueble sin derecho a retirada.

DÉCIMO PRIMERO. Carencia
Las partes acuerdan un periodo de carencia desde el {fecha_entrega_formateada} y hasta el {fecha_fin_carencia_formateada}. El pago de la renta garantizada se iniciará el día {fecha_inicio_pagos_formateada}.
--- SALTO DE PÁGINA ---
DÉCIMO SEGUNDO. Entrega: La fecha de entrega a la Gestora será el {fecha_entrega_formateada}.

DÉCIMO TERCERO. Protección de datos
Las partes declaran haber sido informadas del tratamiento de sus datos personales conforme al Reglamento (UE) 2016/679 y normativa vigente, remitiéndose al Anexo I - Política de Privacidad.

Firmado en {datos_inm['ciudad'].capitalize()}, a {fecha_firma_formateada}.

Por {txt_propietario}:



{txt_firmas_propietarios}



Por LA GESTORA:



{datos_op['nombre']}
Representada por: {admin_nombre}


--- SALTO DE PÁGINA ---

ANEXO I - POLÍTICA DE PRIVACIDAD


RESPONSABLE: {datos_op['nombre']}
CIF: {datos_op['identificacion']}
EMAIL: {datos_op.get('correo', 'CORREO NO REGISTRADO')}

FINALIDAD: Gestión contractual, administrativa, cobros, pagos, incidencias y cumplimiento legal.

BASE JURIDICA: Ejecución del contrato y obligaciones legales.

DESTINATARIOS: Administraciones públicas, entidades financieras, aseguradoras y proveedores necesarios.

CONSERVACION: Durante la relación contractual y plazos legales.

DERECHOS: Acceso, rectificación, supresión, oposición, limitación y portabilidad.

El interesado declara haber sido informado mediante la firma del presente Anexo.

Por {txt_propietario}:




{txt_firmas_propietarios}


Por LA GESTORA:



{datos_op['nombre']}
Representada por: {admin_nombre}
"""
                # ⚙️ 2. MOTOR FPDF DE CÓDIGO AL VUELO
                def generar_pdf_contrato_legal(texto):
                    pdf = FPDF()
                    pdf.set_margins(left=30, top=25, right=30)
                    pdf.set_auto_page_break(auto=True, margin=25)
                    pdf.add_page()
                    pdf.set_font("Arial", "", 11)
                    
                    # 💡 PARCHE FPDF: Reemplazar símbolo por palabra formal para evitar borrados
                    texto_limpio = texto.replace('€', 'Euros')
                    
                    for linea in texto_limpio.split('\n'):
                        if "--- SALTO DE PÁGINA ---" in linea:
                            pdf.add_page()
                            continue
                        if linea.isupper() and len(linea) > 0 and len(linea) < 90:
                            pdf.set_font("Arial", "B", 11)
                            pdf.multi_cell(0, 6, linea.encode('latin-1', 'ignore').decode('latin-1'))
                            pdf.set_font("Arial", "", 11)
                        else:
                            pdf.multi_cell(0, 6, linea.encode('latin-1', 'ignore').decode('latin-1'))
                    return pdf.output(dest='S').encode('latin-1')
                # 🚀 3. BOTONERA BIFURCADA
                st.write("**4. Acciones de Generación**")
                c_acc1, c_acc2 = st.columns(2)
                
                with c_acc1:
                    # 🟢 Vía Rápida: Descarga directa
                    st.download_button(
                        label="⚡ Generar Contrato Automático (PDF)", 
                        data=generar_pdf_contrato_legal(plantilla), 
                        file_name=f"Contrato_{datos_inm['nombre'].replace(' ','_')}.pdf", 
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with c_acc2:
                    # 🟡 Vía Lenta: Borrador Editable
                    if st.button("📝 Revisar/Editar Borrador (Opcional)", use_container_width=True):
                        st.session_state[f"borrador_{id_m}"] = plantilla
                        st.rerun()

                # 📝 EL BORRADOR INTERACTIVO (Solo se muestra si hacen clic en Revisar)
                if f"borrador_{id_m}" in st.session_state:
                    st.success("✅ **Borrador Abierto.** Edita el texto libremente antes de descargar el PDF definitivo.")
                    texto_final = st.text_area("Borrador del Contrato", value=st.session_state[f"borrador_{id_m}"], height=600)
                    
                    st.download_button(
                        label="🔒 Confirmar Cambios y Descargar PDF", 
                        data=generar_pdf_contrato_legal(texto_final), 
                        file_name=f"Contrato_{datos_inm['nombre'].replace(' ','_')}_Editado.pdf", 
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_descarga_editado"
                    )            
            st.markdown("---")
            if st.button("❌ Cerrar Panel"): 
                st.session_state.modo_mandato = "NADA"
                st.rerun()
# --- PANEL EDITAR (AHORA CON BÓVEDA DOCUMENTAL) ---
        elif st.session_state.modo_mandato == "EDITAR" and not df_man.empty:
            st.markdown("---")
            st.markdown("### ⚙️ Gestionar Contrato y Documentos")
            op_man_edit = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_edit = st.selectbox("Selecciona el Mandato a gestionar:", op_man_edit)
            
            if m_sel_edit:
                idx = op_man_edit.index(m_sel_edit)
                d_m = df_man.iloc[idx]
                id_m = str(d_m['id'])
                
                with st.form(f"form_edit_man_{id_m}", clear_on_submit=False):
                    st.write("**1. Condiciones Financieras**")
                    c1, c2, c3 = st.columns(3)
                    e_renta = c1.number_input(f"Renta Garantizada ({simbolo_mon})", value=float(d_m.get('ingreso_garantizado', 0.0)), step=50.0)
                    e_fianza = c2.number_input(f"Fianza ({simbolo_mon})", value=float(d_m.get('valor_fianza', 0.0)), step=50.0)
                    
                    lista_act = ["IPC", "FIJO", "NO APLICA"]
                    idx_act = lista_act.index(d_m.get('tipo_actualizacion', 'IPC')) if d_m.get('tipo_actualizacion') in lista_act else 0
                    e_act = c3.selectbox("Actualización Anual", lista_act, index=idx_act)
                    
                    c4, c5 = st.columns(2)
                    e_cta1 = c4.text_input("Cuenta / IBAN Principal", value=str(d_m.get('cuenta_pago', '')))
                    e_cta2 = c5.text_input("Cuenta / IBAN Secundaria", value=str(d_m.get('cuenta_pago_2', '')).replace("None", ""))
                    
                    st.markdown("---")
                    st.write("**2. Anexar Documentos Faltantes (Opcional)**")
                    st.caption("Sube un archivo solo si deseas reemplazar el actual o si estaba pendiente.")
                    cd1, cd2 = st.columns(2)
                    doc_contrato = cd1.file_uploader("Contrato Firmado", type=["pdf", "jpg", "png"], key="edit_doc_c")
                    doc_empadrona = cd2.file_uploader("Aut. Empadronamiento", type=["pdf", "jpg", "png"], key="edit_doc_e")
                    cd3, cd4 = st.columns(2)
                    doc_inv = cd3.file_uploader("Acta Inventario", type=["pdf", "jpg", "png"], key="edit_doc_i")
                    doc_sum = cd4.file_uploader("Recibos Suministros", type=["pdf", "jpg", "png"], key="edit_doc_s")

                    st.markdown("---")
                    col_b1, col_b2, _ = st.columns([2, 1.5, 6.5])
                    
                    if col_b1.form_submit_button("💾 Guardar Cambios"):
                        with st.spinner("Actualizando contrato y subiendo documentos..."):
                            # Preparar URLs actuales
                            url_c = d_m.get('url_contrato')
                            url_e = d_m.get('url_empadronamiento')
                            url_i = d_m.get('url_inventario')
                            url_s = d_m.get('url_suministros')
                            
                            # Función auxiliar de subida
                            def subir_reemplazo(archivo, prefijo):
                                if not archivo: return None
                                ext = archivo.name.split('.')[-1].lower()
                                tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                n_nube = f"{prefijo}_edit_{id_m}_{int(time.time())}.{ext}"
                                supabase.storage.from_("documentos_mandatos").upload(n_nube, archivo.getvalue(), file_options={"content-type": tipo_mime})
                                return supabase.storage.from_("documentos_mandatos").get_public_url(n_nube)
                            
                            # Si hay archivo nuevo, sobrescribe la variable
                            if doc_contrato: url_c = subir_reemplazo(doc_contrato, "contrato")
                            if doc_empadrona: url_e = subir_reemplazo(doc_empadrona, "empadronamiento")
                            if doc_inv: url_i = subir_reemplazo(doc_inv, "inventario")
                            if doc_sum: url_s = subir_reemplazo(doc_sum, "suministros")

                            # Actualizar Base de Datos
                            datos_upd = {
                                "ingreso_garantizado": e_renta, "valor_fianza": e_fianza, 
                                "tipo_actualizacion": e_act, "cuenta_pago": e_cta1.strip(), "cuenta_pago_2": e_cta2.strip(),
                                "url_contrato": url_c, "url_empadronamiento": url_e,
                                "url_inventario": url_i, "url_suministros": url_s
                            }
                            supabase.table("mandatos").update(datos_upd).eq("id", int(id_m)).execute()
                            
                            var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                            usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                            supabase.table("historial_mandatos").insert({"id_mandato": int(id_m), "accion": f"CONDICIONES / DOCS ACTUALIZADOS", "usuario": usuario_actual}).execute()
                            
                            st.success("✅ Contrato actualizado con éxito.")
                            st.session_state.modo_mandato = "NADA"
                            time.sleep(1)
                            st.rerun()
                            
                    if col_b2.form_submit_button("❌ Cerrar"): 
                        st.session_state.modo_mandato = "NADA"
                        st.rerun()
                
                # ZONA DE PELIGRO (Se mantiene intacta)
                st.write("")
                st.error("🚨 Zona de Peligro: Finalización de Contrato")
                c_del1, c_del2 = st.columns([7, 3])
                confirmar_fin = c_del1.checkbox("⚠️ Confirmo que deseo FINALIZAR este contrato.", key=f"chk_fin_{id_m}")
                if c_del2.button("🛑 Finalizar Contrato", disabled=not confirmar_fin, use_container_width=True):
                    supabase.table("mandatos").update({"estado_contrato": "FINALIZADO"}).eq("id", int(id_m)).execute()
                    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                    supabase.table("historial_mandatos").insert({"id_mandato": int(id_m), "accion": "CONTRATO FINALIZADO POR EL USUARIO", "usuario": usuario_actual}).execute()
                    # 💡 Próximamente: El Motor Automático atrapará esto para devolver la fianza
                    st.success("✅ El contrato ha sido finalizado.")
                    st.session_state.modo_mandato = "NADA"
                    time.sleep(1.5)
                    st.rerun()

        elif st.session_state.modo_mandato == "REPORTES" and not df_man.empty:
            st.markdown("---")
            st.markdown("## Centro de Reportes de Mandatos")
            tipo_rep = st.selectbox("Elige el tipo de reporte:", ["Ficha Detallada (Un Contrato)", "Historial de Auditoría (Un Contrato)", "Directorio Global (Todos los Contratos)"])
            
            var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
            usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

            # 🛡️ Lógica para Operadores y Título del PDF
            try: 
                res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
                df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
            except: 
                df_ops = pd.DataFrame()
                
            titulo_encabezado = "INMOLEASING"
            if not df_ops.empty and len(df_ops) == 1:
                titulo_encabezado = str(df_ops.iloc[0]['nombre']).upper()

            if tipo_rep == "Directorio Global (Todos los Contratos)":
                df_rep = df_view_display.copy()
                if 'DOCS' in df_rep.columns: df_rep = df_rep.drop(columns=['DOCS'])
                panel_reportes_y_compartir(df_rep, "directorio_mandatos", "Mandatos", lambda df: generar_pdf_mandatos(df, titulo_encabezado), df_ops, supabase, usuario_actual, "modo_mandato")
            
            elif tipo_rep == "Ficha Detallada (Un Contrato)":
                op_man_rep = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
                m_sel_rep = st.selectbox("Selecciona el Mandato a exportar:", op_man_rep)
                if m_sel_rep:
                    idx = op_man_rep.index(m_sel_rep)
                    d_m = df_man.iloc[idx]; d_v = df_view_display.iloc[idx]
                    datos_ficha = {
                        'inmueble': d_v['INMUEBLE'], 'propietario_1': d_v['TITULAR'], 'porc_prop_1': d_m.get('porcentaje_propiedad', 0), 'porc_pago_1': d_m.get('porcentaje_pago_1', 0), 'iban_1': d_m.get('cuenta_pago', ''), 'porc_prop_2': d_m.get('porcentaje_propiedad_2', 0), 'porc_pago_2': d_m.get('porcentaje_pago_2', 0), 'iban_2': d_m.get('cuenta_pago_2', ''), 'f_suscripcion': d_m.get('fecha_suscripcion', ''), 'f_entrega': d_m.get('fecha_entrega', ''), 'f_pagos': d_m.get('fecha_inicio_pagos', ''), 'f_vence': d_m.get('fecha_terminacion', ''), 'f_aviso': d_m.get('fecha_aviso_no_renovacion', ''), 'renta': d_m.get('ingreso_garantizado', 0), 'actualizacion': d_m.get('tipo_actualizacion', ''), 'fianza': d_m.get('valor_fianza', 0), 'tipo_ind': d_m.get('tipo_indemnizacion', ''), 'monto_ind': d_m.get('indemnizacion_anticipada', 0), 'estado_fin': d_m.get('estado_financiero', ''), 'url_c': d_m.get('url_contrato', ''), 'url_e': d_m.get('url_empadronamiento', ''), 'url_i': d_m.get('url_inventario', ''), 'url_s': d_m.get('url_suministros', '')
                    }
                    panel_reportes_y_compartir(pd.DataFrame([datos_ficha]), f"Ficha_Mandato", "Ficha de Mandato", lambda df: generar_pdf_ficha_mandato(df, titulo_encabezado), df_ops, supabase, usuario_actual, "modo_mandato")
            
            elif tipo_rep == "Historial de Auditoría (Un Contrato)":
                op_man_aud = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
                m_sel_aud = st.selectbox("Selecciona el Mandato para auditar:", op_man_aud)
                if m_sel_aud:
                    idx = op_man_aud.index(m_sel_aud)
                    id_m = df_man.iloc[idx]['id']
                    try: res_hist = supabase.table("historial_mandatos").select("fecha_evento, accion, usuario").eq("id_mandato", int(id_m)).order("fecha_evento", desc=True).execute(); df_h = pd.DataFrame(res_hist.data) if res_hist.data else pd.DataFrame()
                    except Exception as e: df_h = pd.DataFrame()
                    if not df_h.empty:
                        df_h['FECHA'] = pd.to_datetime(df_h['fecha_evento']).dt.strftime('%d/%m/%Y %H:%M')
                        df_h_rep = df_h[['FECHA', 'accion', 'usuario']].copy()
                        df_h_rep.rename(columns={'accion': 'ACCION REGISTRADA', 'usuario': 'USUARIO'}, inplace=True)
                        panel_reportes_y_compartir(df_h_rep, f"Auditoria_Mandato", "Historial Mandato", lambda df: generar_pdf_historial_mandato(df, titulo_encabezado), df_ops, supabase, usuario_actual, "modo_mandato")
                    else: st.info("ℹ️ No hay registros.")
            st.markdown("---")
            if st.button("❌ Cerrar Panel"): st.session_state.modo_mandato = "NADA"; st.rerun()

    # ==========================================
    # TAB 4: ACTIVOS NO INVENTARIOS (Mobiliario y Equipos)
    # ==========================================
    with tab4:
        if 'modo_activo' not in st.session_state:
            st.session_state.modo_activo = "NADA"

        st.subheader("Activos Fijos y Mobiliario")

        moneda_sesion = st.session_state.get("moneda_usuario", "EUR")
        simbolo_mon = "€" if moneda_sesion == "EUR" else "$"

        try:
            res_inm = supabase.table("inmuebles").select("id, nombre").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
            df_inm_act = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
        except:
            df_inm_act = pd.DataFrame()
# 🚀 --- DIRECTORIO DE ACTIVOS (LA CUADRÍCULA) --- 🚀
        if st.session_state.modo_activo == "NADA":
            try:
                # Traemos los activos cruzando datos con operadores, propiedades y unidades para tener los nombres reales
                res_act = supabase.table("activos").select("*, operadores(nombre), inmuebles(nombre), unidades(nombre)").eq("moneda", moneda_sesion).execute()
                df_act = pd.DataFrame(res_act.data) if res_act.data else pd.DataFrame()
            except:
                df_act = pd.DataFrame()

            st.write("") 
            
            if not df_act.empty:
                df_act_display = df_act.copy()
                
                # --- 1. PREPARAMOS LOS DATOS PRIMERO ---
                def get_dueno(row):
                    if row.get('propiedad') == 'Empresa' and isinstance(row.get('operadores'), dict):
                        return row['operadores'].get('nombre', 'Operador')
                    return "Propietario"
                    
                def get_ubicacion(row):
                    ubi = str(row.get('ubicacion_tipo', 'Bodega'))
                    if ubi == 'Zona Común' and isinstance(row.get('inmuebles'), dict):
                        return f"{row['inmuebles'].get('nombre', '')}: Común"
                    elif ubi == 'Unidad' and isinstance(row.get('unidades'), dict):
                        inm_nom = row['inmuebles'].get('nombre', '') if isinstance(row.get('inmuebles'), dict) else ""
                        return f"{inm_nom}: {row['unidades'].get('nombre', '')}"
                    return ubi
                
                df_act_display['DUEÑO'] = df_act_display.apply(get_dueno, axis=1)
                df_act_display['UBICACIÓN'] = df_act_display.apply(get_ubicacion, axis=1)
                df_act_display['VALOR'] = pd.to_numeric(df_act_display['valor_compra']).fillna(0).apply(lambda x: f"{simbolo_mon} {x:,.2f}" if x > 0 else "-")
                
                df_act_display.rename(columns={'codigo_unico': 'CÓDIGO', 'nombre': 'ACTIVO', 'categoria': 'CATEGORÍA', 'estado': 'ESTADO', 'factura_url': 'SOPORTE'}, inplace=True)
                
                # --- 2. LOS 3 FILTROS SUPERIORES ---
                c_busq1, c_busq2, c_busq3 = st.columns([4, 3, 3])
                
                busqueda_act = c_busq1.text_input("🔍 Buscar Código o Nombre...", "").upper().strip()
                
                lista_ubicaciones = ["TODAS"] + sorted(df_act_display['UBICACIÓN'].dropna().unique().tolist())
                filtro_ubi = c_busq2.selectbox("Filtrar por Ubicación", lista_ubicaciones)
                
                lista_categorias = ["TODAS"] + sorted(df_act_display['CATEGORÍA'].dropna().unique().tolist())
                filtro_cat = c_busq3.selectbox("Filtrar por Categoría", lista_categorias)
                
                # --- 3. APLICAMOS LOS FILTROS ---
                if busqueda_act:
                    df_act_display = df_act_display[df_act_display['CÓDIGO'].str.contains(busqueda_act) | df_act_display['ACTIVO'].str.contains(busqueda_act)]
                if filtro_ubi != "TODAS":
                    df_act_display = df_act_display[df_act_display['UBICACIÓN'] == filtro_ubi]
                if filtro_cat != "TODAS":
                    df_act_display = df_act_display[df_act_display['CATEGORÍA'] == filtro_cat]

                # --- 4. MOSTRAR LA TABLA BONITA ---
                st.dataframe(
                    df_act_display[['CÓDIGO', 'ACTIVO', 'CATEGORÍA', 'DUEÑO', 'UBICACIÓN', 'ESTADO', 'VALOR', 'SOPORTE']].sort_values(by='CÓDIGO', ascending=False), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "SOPORTE": st.column_config.LinkColumn(
                            "🔍 DOC",
                            help="Haz clic para abrir la factura o soporte",
                            display_text="🔍 Abrir"
                        )
                    }
                )
            else:
                st.info(f"ℹ️ Aún no hay activos registrados en tu entorno operativo ({moneda_sesion}).")

        # --- BARRA DE HERRAMIENTAS ---
        st.markdown("---")
        a_c1, a_c2, a_c3, a_c4, a_c5 = st.columns([1.5, 1.5, 1.5, 1.5, 4.0])
        
        if a_c1.button("➕ Nuevo", key="btn_nuevo_act", use_container_width=True):
            st.session_state.modo_activo = "CREAR"; st.rerun()
        if a_c2.button("⚙️ Gestionar", key="btn_gest_act", use_container_width=True):
            st.session_state.modo_activo = "GESTIONAR"; st.rerun()
        if a_c3.button("📦 Mover", key="btn_mover_act", use_container_width=True):
            st.session_state.modo_activo = "MOVER"; st.rerun()
        if a_c4.button("📊 Reportes", key="btn_rep_act", use_container_width=True):
            st.session_state.modo_activo = "REPORTES"; st.rerun()

        # --- PANEL: CREAR NUEVO ACTIVO (CON CASCADA CONTABLE) ---
        if st.session_state.modo_activo == "CREAR":
            from dateutil.relativedelta import relativedelta
            st.markdown("---")
            st.markdown("### Alta de Nuevo Activo Fijo")

            try:
                res_ops = supabase.table("operadores").select("id, nombre").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
                df_ops_act = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
            except:
                df_ops_act = pd.DataFrame()

            if df_inm_act.empty:
                st.error(f"❌ No hay propiedades registradas en {moneda_sesion}.")
            else:
                with st.container():
                    st.write("**1. Identificación y Propiedad**")
                    c1, c2 = st.columns(2)
                    
                    tipo_propiedad = c1.selectbox("¿A quién pertenece el activo? *", ["Operador", "Propietario"], key="tipo_prop_din")
                    
                    es_operador = (tipo_propiedad == "Operador")
                    id_operador_sel = None
                    nombre_dueño_final = "Propietario"
                    prefijo = "OP-" if es_operador else "PO-" 
                    
                    # --- NUEVAS VARIABLES FINANCIERAS ---
                    origen_activo = "PROPIETARIO"
                    id_cta_bancaria = None
                    saldo_actual_banco = 0.0

                    if es_operador:
                        if len(df_ops_act) == 1:
                            nombre_dueño_final = df_ops_act.iloc[0]['nombre']
                            id_operador_sel = int(df_ops_act.iloc[0]['id'])
                            st.info(f"🏢 **Dueño:** {nombre_dueño_final} (Auto-asignado)")
                        elif len(df_ops_act) > 1:
                            nombre_dueño_final = st.selectbox("Selecciona el Operador dueño *", df_ops_act['nombre'].tolist(), key="sel_op_din")
                            id_operador_sel = int(df_ops_act[df_ops_act['nombre'] == nombre_dueño_final].iloc[0]['id'])
                        
                        st.markdown("---")
                        st.write("**💰 Adquisición y Contabilidad**")
                        c_orq1, c_orq2 = st.columns(2)
                        origen_activo = c_orq1.selectbox("Origen del Activo *", ["COMPRA DIRECTA", "APORTACIÓN DE SOCIO"])
                        
                        if origen_activo == "COMPRA DIRECTA":
                            c_orq2.info("🧾 Esta compra generará una Cuenta por Pagar (CxP) en Tesorería.")
                        elif origen_activo == "APORTACIÓN DE SOCIO":
                            c_orq2.info("📈 Este activo aumentará el patrimonio (Aportes Sociales) sin afectar tesorería.")
                        st.markdown("---")
                    c3, c4 = st.columns([2, 1])
                    nombre_act = c3.text_input("Nombre / Descripción *", placeholder="Ej: Lavadora LG 9kg", key="nom_act_din")
                    categoria = c4.selectbox("Categoría", ["Mobiliario", "Electrodomésticos", "Electrónica", "Climatización", "Decoración", "Otro"], key="cat_act_din")

                    st.write("**2. Ubicación Física**")
                    c5, c6, c7 = st.columns(3)
                    
                    ubic_tipo = c5.selectbox("Ubicación *", ["Bodega", "Zona Común", "Unidad"], key="ubi_tipo_din")
                    id_inm_sel, id_uni_sel = None, None
                    
                    if ubic_tipo in ["Zona Común", "Unidad"]:
                        inm_sel = c6.selectbox("Edificio *", df_inm_act['nombre'].tolist(), key="inm_sel_din")
                        id_inm_sel = df_inm_act[df_inm_act['nombre'] == inm_sel].iloc[0]['id']
                        
                        if ubic_tipo == "Unidad":
                            res_u = supabase.table("unidades").select("id, nombre").eq("id_inmueble", int(id_inm_sel)).eq("estado", "ACTIVO").execute()
                            df_u = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
                            if not df_u.empty:
                                uni_sel = c7.selectbox("Unidad *", df_u['nombre'].tolist(), key="uni_sel_din")
                                id_uni_sel = df_u[df_u['nombre'] == uni_sel].iloc[0]['id']
                            else:
                                c7.warning("Este edificio no tiene unidades.")

                    st.write("**3. Valor, Estado y Garantía**")
                    c8, c9, c10 = st.columns(3)
                    valor_compra = c8.number_input(f"Valor ({simbolo_mon})", min_value=0.0, step=1.0, value=0.0, disabled=not es_operador, key="val_act_din")
                    fecha_compra = c9.date_input("Fecha Compra", key="f_compra_din")
                    estado_fisico = c10.selectbox("Estado", ["Nuevo", "Bueno", "Deteriorado", "En reparación", "En bodega"], key="est_act_din")
                    meses_gar = st.number_input("Meses de Garantía (Ejem: 36 para 3 años)", min_value=0, value=12, step=1, key="meses_gar_din")

                    st.write("**4. Soporte**")
                    factura_file = st.file_uploader("Factura (PDF/Imagen)", type=["pdf", "jpg", "png"], key="fac_file_din")

                    st.markdown("---")
                    col_b1, col_b2, _ = st.columns([2.0, 1.5, 6.5]) 
                    
                    if col_b1.button("💾 Guardar Activo", key="btn_save_din"):
                        if not nombre_act:
                            st.error("❌ El nombre es obligatorio.")
                        elif ubic_tipo == "Unidad" and not id_uni_sel:
                            st.error("❌ Selecciona una unidad o revisa que el edificio tenga unidades creadas.")
                        else:
                            try:
                                with st.spinner("Generando código, guardando y ejecutando cascada contable..."):
                                    res_last = supabase.table("activos").select("codigo_unico").like("codigo_unico", f"{prefijo}%").order("codigo_unico", desc=True).limit(1).execute()
                                    if not res_last.data:
                                        cod_final = f"{prefijo}001"
                                    else:
                                        ultimo_txt = res_last.data[0]['codigo_unico']
                                        try: num_extraido = int(ultimo_txt.split('-')[1]); cod_final = f"{prefijo}{num_extraido + 1:03d}"
                                        except: cod_final = f"{prefijo}001"

                                    url_f = None
                                    if factura_file:
                                        ext = factura_file.name.split('.')[-1].lower()
                                        n_f = f"fac_{int(time.time())}.{ext}"
                                        supabase.storage.from_("documentos_activos").upload(n_f, factura_file.getvalue(), file_options={"content-type": f"image/{ext}" if ext != 'pdf' else "application/pdf"})
                                        url_f = supabase.storage.from_("documentos_activos").get_public_url(n_f)

                                    f_vence_gar = fecha_compra + relativedelta(months=meses_gar)
                                    
                                    ins = {
                                        "codigo_unico": cod_final, "nombre": nombre_act.strip().upper(),
                                        "categoria": categoria, "propiedad": "Empresa" if es_operador else "Propietario", 
                                        "origen": origen_activo, # 🚀 DATO NUEVO
                                        "operador_id": id_operador_sel, "moneda": moneda_sesion,
                                        "valor_compra": float(valor_compra) if es_operador else 0.0, 
                                        "fecha_compra": str(fecha_compra), "ubicacion_tipo": ubic_tipo, 
                                        "inmueble_id": int(id_inm_sel) if id_inm_sel else None,
                                        "unidad_id": int(id_uni_sel) if id_uni_sel else None, 
                                        "estado": estado_fisico, "inicio_garantia": str(fecha_compra), 
                                        "fin_garantia": str(f_vence_gar), "factura_url": url_f
                                    }
                                    res_ins = supabase.table("activos").insert(ins).execute()
                                    
                                    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                                    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

                                    supabase.table("activos_movimientos").insert({
                                        "activo_id": res_ins.data[0]['id'], "origen_tipo": "ALTA", 
                                        "destino_tipo": ubic_tipo, "motivo": f"Registro Inicial {cod_final} ({origen_activo})", 
                                        "usuario_responsable": usuario_actual
                                    }).execute()
                                    # 🚀 --- CASCADA FINANCIERA AUTOMÁTICA --- 🚀
                                    if es_operador and float(valor_compra) > 0:
                                        try:
                                            # 1. Traer catálogo de cuentas (Buscamos Activos, Patrimonio y CxP)
                                            res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo").eq("moneda", moneda_sesion).execute()
                                            df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
                                            
                                            id_cta_activo, id_cta_patrimonio, id_cta_cxp = None, None, None
                                            if not df_ctas.empty:
                                                cta_act = df_ctas[df_ctas['codigo'].str.startswith('15', na=False)]
                                                if not cta_act.empty: id_cta_activo = cta_act.iloc[0]['id']
                                                
                                                cta_patr = df_ctas[df_ctas['codigo'].str.startswith('31', na=False)]
                                                if not cta_patr.empty: id_cta_patrimonio = cta_patr.iloc[0]['id']
                                                
                                                # Cuentas 22 o 23 para Proveedores / CxP
                                                cta_cxp = df_ctas[df_ctas['codigo'].str.startswith('22', na=False) | df_ctas['codigo'].str.startswith('23', na=False)]
                                                if not cta_cxp.empty: id_cta_cxp = cta_cxp.iloc[0]['id']

                                            # 2. Crear Asiento Contable Maestro
                                            desc_asiento = f"ALTA ACTIVO: {nombre_act.strip().upper()} ({cod_final})"
                                            res_ast = supabase.table("fin_asientos").insert({
                                                "fecha_contable": str(fecha_compra), "descripcion": desc_asiento,
                                                "concepto_general": f"Ingreso por {origen_activo}", "origen": "MODULO_ACTIVOS",
                                                "moneda": moneda_sesion, "estado": "CONTABILIZADO"
                                            }).execute()
                                            id_ast = res_ast.data[0]['id']

                                            # Débito al Activo (Aumenta tu inventario)
                                            if id_cta_activo:
                                                supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(id_cta_activo), "debito": float(valor_compra), "credito": 0.0, "descripcion_linea": desc_asiento}).execute()

                                            if origen_activo == "COMPRA DIRECTA":
                                                # Crédito a CxP (Pasivo Contable)
                                                if id_cta_cxp:
                                                    supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(id_cta_cxp), "debito": 0.0, "credito": float(valor_compra), "descripcion_linea": "CxP por compra activo"}).execute()
                                                
                                                # 🚀 MOTOR AUTOMÁTICO: Generar Cuenta Por Pagar Operativa
                                                supabase.table("fin_cuentas_pagar").insert({
                                                    "modulo_origen": "ACTIVOS", "id_origen": res_ins.data[0]['id'],
                                                    "acreedor": "PROVEEDOR DE ACTIVOS", "concepto": desc_asiento,
                                                    "monto_total": float(valor_compra), "saldo_pendiente": float(valor_compra),
                                                    "moneda": moneda_sesion, "estado": "PENDIENTE"
                                                }).execute()
                                                
                                                # 🚀 MOTOR AUTOMÁTICO: Log de Auditoría
                                                supabase.table("sys_motor_automatico_logs").insert({
                                                    "evento": "compra_activo_fijo", "modulo_origen": "ACTIVOS", "id_origen": res_ins.data[0]['id'],
                                                    "regla_evaluada": "SI origen=COMPRA DIRECTA -> generar_cxp",
                                                    "accion_ejecutada": "generar_cxp",
                                                    "periodo": pd.Timestamp.now().strftime("%Y-%m"), "resultado": "EXITO",
                                                    "detalles": f"CxP Generada: {valor_compra}"
                                                }).execute()

                                            elif origen_activo == "APORTACIÓN DE SOCIO":
                                                if id_cta_patrimonio:
                                                    # Crédito al Patrimonio (Aumenta el capital)
                                                    supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(id_cta_patrimonio), "debito": 0.0, "credito": float(valor_compra), "descripcion_linea": "Aporte No Dinerario de Socio"}).execute()
                                        except Exception as e:
                                            st.error(f"⚠️ Activo guardado, pero hubo un error en la cascada contable: {e}")
                                    st.success(f"✅ Activo **{cod_final}** y contabilidad registrados.");
                                    log_accion(supabase, usuario_actual, "CREAR ACTIVO", f"{cod_final} - {nombre_act.strip().upper()}")
                                    time.sleep(2.5); 
                                    st.session_state.modo_activo = "NADA";
                                    st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    if col_b2.button("❌ Cancelar", key="btn_cancel_din"): st.session_state.modo_activo = "NADA"; st.rerun()
        # --- PANEL: GESTIONAR ACTIVO ---
        elif st.session_state.modo_activo == "GESTIONAR":
            st.markdown("---")
            st.markdown("### ⚙️ Gestionar Activo Fijo")

            try:
                res_act_edit = supabase.table("activos").select("*, operadores(nombre), inmuebles(nombre), unidades(nombre)").eq("moneda", moneda_sesion).order("codigo_unico", desc=True).execute()
                df_a_edit = pd.DataFrame(res_act_edit.data) if res_act_edit.data else pd.DataFrame()
            except: df_a_edit = pd.DataFrame()

            if df_a_edit.empty:
                st.warning("No hay activos registrados para gestionar.")
                if st.button("❌ Cerrar Panel"): st.session_state.modo_activo = "NADA"; st.rerun()
            else:
                def get_ubicacion_edit(row):
                    ubi = str(row.get('ubicacion_tipo', 'Bodega'))
                    if ubi == 'Zona Común' and isinstance(row.get('inmuebles'), dict): return f"{row['inmuebles'].get('nombre', '')}: Común"
                    elif ubi == 'Unidad' and isinstance(row.get('unidades'), dict):
                        inm_nom = row['inmuebles'].get('nombre', '') if isinstance(row.get('inmuebles'), dict) else ""
                        return f"{inm_nom}: {row['unidades'].get('nombre', '')}"
                    return ubi
                
                df_a_edit['UBICACION'] = df_a_edit.apply(get_ubicacion_edit, axis=1)

                st.markdown("**🔍 Buscar activo a modificar**")
                c_f1, c_f2, c_f3 = st.columns([4, 3, 3])
                busqueda_edit = c_f1.text_input("Buscar Código o Nombre...", "", key="busq_edit_act").upper().strip()
                lista_ubicaciones = ["TODAS"] + sorted(df_a_edit['UBICACION'].dropna().unique().tolist())
                filtro_ubi = c_f2.selectbox("Filtrar por Ubicación", lista_ubicaciones, key="ubi_edit_act")
                lista_categorias = ["TODAS"] + sorted(df_a_edit['categoria'].dropna().unique().tolist())
                filtro_cat = c_f3.selectbox("Filtrar por Categoría", lista_categorias, key="cat_edit_act")

                df_filtrado = df_a_edit.copy()
                if busqueda_edit: df_filtrado = df_filtrado[df_filtrado['codigo_unico'].str.contains(busqueda_edit) | df_filtrado['nombre'].str.contains(busqueda_edit)]
                if filtro_ubi != "TODAS": df_filtrado = df_filtrado[df_filtrado['UBICACION'] == filtro_ubi]
                if filtro_cat != "TODAS": df_filtrado = df_filtrado[df_filtrado['categoria'] == filtro_cat]

                if df_filtrado.empty:
                    st.warning("⚠️ No se encontraron activos con estos filtros.")
                    if st.button("❌ Cancelar", key="btn_cancel_empty"): st.session_state.modo_activo = "NADA"; st.rerun()
                else:
                    opciones_activos = df_filtrado.apply(lambda r: f"{r['codigo_unico']} - {r['nombre']} ({r['UBICACION']})", axis=1).tolist()
                    act_sel = st.selectbox("Selecciona el Activo exacto:", opciones_activos)

                    if act_sel:
                        cod_seleccionado = act_sel.split(" - ")[0]
                        datos_act = df_filtrado[df_filtrado['codigo_unico'] == cod_seleccionado].iloc[0]
                        id_act = str(datos_act['id'])
                        es_op = datos_act.get('propiedad') == 'Empresa'

                        with st.form(f"form_edit_act_{id_act}", clear_on_submit=False):
                            st.write("**Detalles del Activo**")
                            c1, c2 = st.columns([2, 1])
                            e_nom = c1.text_input("Nombre / Descripción *", datos_act['nombre'])
                            
                            lista_cat = ["Mobiliario", "Electrodomésticos", "Electrónica", "Climatización", "Decoración", "Otro"]
                            idx_cat = lista_cat.index(datos_act['categoria']) if datos_act.get('categoria') in lista_cat else 0
                            e_cat = c2.selectbox("Categoría", lista_cat, index=idx_cat)

                            c3, c4 = st.columns(2)
                            lista_est = ["Nuevo", "Bueno", "Deteriorado", "En reparación", "En bodega", "Sustituido", "Inactivo", "Punto Limpio"]
                            idx_est = lista_est.index(datos_act['estado']) if datos_act.get('estado') in lista_est else 0
                            e_est = c3.selectbox("Estado Físico", lista_est, index=idx_est)
                            
                            # 🚀 CAMPOS FINANCIEROS EDITABLES
                            if es_op:
                                st.markdown("---")
                                st.write("💰 **Corrección Financiera (Atención: Modificar esto recalculará la contabilidad)**")
                                cf1, cf2, cf3 = st.columns(3)
                                e_val = cf1.number_input(f"Valor de Compra ({simbolo_mon})", min_value=0.0, step=1.0, value=float(datos_act.get('valor_compra', 0.0)))
                                
                                lista_origen = ["COMPRA DIRECTA", "APORTACIÓN DE SOCIO", "PROPIETARIO"]
                                idx_ori = lista_origen.index(datos_act.get('origen', 'COMPRA DIRECTA')) if datos_act.get('origen') in lista_origen else 0
                                e_ori = cf2.selectbox("Origen del Activo", lista_origen, index=idx_ori)
                                if e_ori == "COMPRA DIRECTA":
                                    cf3.info("🧾 Actualizará CxP en Tesorería.")
                                elif e_ori == "APORTACIÓN DE SOCIO":
                                    cf3.info("📈 Actualizará Patrimonio.")
                                else:
                                    cf3.info("No afecta contabilidad.")
                            else:
                                e_val = 0.0
                                e_ori = "PROPIETARIO"

                            st.markdown("---")
                            col_b1, col_b2, _ = st.columns([2.0, 1.5, 6.5])                                
                            if not e_nom: st.error("❌ El nombre no puede estar vacío.")
                            else:
                                    # 🚀 1. REVERSIÓN CONTABLE DEL PASADO (Si hubo cambios financieros)
                                    cambio_financiero = es_op and (float(e_val) != float(datos_act.get('valor_compra', 0.0)) or e_ori != datos_act.get('origen'))
                                    
                                    if cambio_financiero and float(datos_act.get('valor_compra', 0.0)) > 0:
                                        with st.spinner("Revirtiendo contabilidad anterior..."):
                                            # Borrar asiento viejo
                                            res_v = supabase.table("fin_asientos").select("id").like("descripcion", f"%({cod_seleccionado})%").execute()
                                            if res_v.data:
                                                for asnt in res_v.data: supabase.table("fin_asientos").delete().eq("id", asnt['id']).execute()
                                            
                                            # Borrar la CxP vieja si seguía PENDIENTE
                                            supabase.table("fin_cuentas_pagar").delete().eq("modulo_origen", "ACTIVOS").like("concepto", f"%({cod_seleccionado})%").eq("estado", "PENDIENTE").execute()
                                    # 🚀 2. ACTUALIZAR ACTIVO
                                    upd_data = {
                                        "nombre": e_nom.strip().upper(), "categoria": e_cat, "estado": e_est,
                                        "valor_compra": e_val if es_op else 0.0, "origen": e_ori if es_op else "PROPIETARIO"
                                    }
                                    supabase.table("activos").update(upd_data).eq("id", id_act).execute()
                                    
                                    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                                    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                                    
                                    supabase.table("activos_movimientos").insert({
                                        "activo_id": id_act, "origen_tipo": "MODIFICACIÓN", "destino_tipo": "N/A",
                                        "motivo": f"Actualización (Estado: {e_est})", "usuario_responsable": usuario_actual
                                    }).execute()

                                    # 🚀 3. NUEVA CASCADA FINANCIERA (Si aplica)
                                    if cambio_financiero and float(e_val) > 0:
                                        with st.spinner("Generando nueva contabilidad..."):
                                            res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo").eq("moneda", moneda_sesion).execute()
                                            df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
                                            
                                            id_cta_activo, id_cta_patrimonio, id_cta_banco = None, None, None
                                            if not df_ctas.empty:
                                                cta_act = df_ctas[df_ctas['codigo'].str.startswith('15', na=False)]
                                                if not cta_act.empty: id_cta_activo = cta_act.iloc[0]['id']
                                                
                                                cta_patr = df_ctas[df_ctas['codigo'].str.startswith('31', na=False)]
                                                if not cta_patr.empty: id_cta_patrimonio = cta_patr.iloc[0]['id']
                                                
                                                cta_ban = df_ctas[df_ctas['codigo'].str.startswith('1110', na=False)]
                                                if not cta_ban.empty: id_cta_banco = cta_ban.iloc[0]['id']
                                            fecha_hoy = time.strftime("%Y-%m-%d")
                                            desc_asiento = f"AJUSTE ACTIVO: {e_nom.strip().upper()} ({cod_seleccionado})"
                                            res_ast = supabase.table("fin_asientos").insert({
                                                "fecha_contable": fecha_hoy, "descripcion": desc_asiento,
                                                "concepto_general": f"Ajuste por {e_ori}", "origen": "MODULO_ACTIVOS",
                                                "moneda": moneda_sesion, "estado": "CONTABILIZADO"
                                            }).execute()
                                            id_ast = res_ast.data[0]['id']

                                            if id_cta_activo: 
                                                supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(id_cta_activo), "debito": float(e_val), "credito": 0.0, "descripcion_linea": desc_asiento}).execute()

                                        if e_ori == "COMPRA DIRECTA":
                                                res_cxp = supabase.table("fin_cuentas_contables").select("id").like("codigo", "22%").eq("moneda", moneda_sesion).execute()
                                                if res_cxp.data:
                                                    supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(res_cxp.data[0]['id']), "debito": 0.0, "credito": float(e_val), "descripcion_linea": "CxP ajustada"}).execute()
                                                
                                                supabase.table("fin_cuentas_pagar").insert({
                                                    "modulo_origen": "ACTIVOS", "id_origen": int(id_act),
                                                    "acreedor": "PROVEEDOR DE ACTIVOS", "concepto": desc_asiento,
                                                    "monto_total": float(e_val), "saldo_pendiente": float(e_val),
                                                    "moneda": moneda_sesion, "estado": "PENDIENTE"
                                                }).execute()
                                        elif e_ori == "APORTACIÓN DE SOCIO":
                                                if id_cta_patrimonio: 
                                                    supabase.table("fin_apuntes").insert({"id_asiento": id_ast, "id_cuenta_contable": int(id_cta_patrimonio), "debito": 0.0, "credito": float(e_val), "descripcion_linea": "Aporte ajustado"}).execute()
                                    log_accion(supabase, usuario_actual, "EDITAR ACTIVO", f"{cod_seleccionado} - {e_nom.strip().upper()}")
                                    st.success("✅ Activo y contabilidad actualizados exitosamente.")
                                    time.sleep(1.5); st.session_state.modo_activo = "NADA"; st.rerun()

                            if col_b2.form_submit_button("❌ Cancelar"): st.session_state.modo_activo = "NADA"; st.rerun()
                        
                        # --- 🚨 ZONA DE PELIGRO: DAR DE BAJA (CON ASIENTO DE PÉRDIDA) ---
                        st.write("")
                        st.error("🚨 Zona de Peligro: Baja del Activo")
                        c_del1, c_del2 = st.columns([7, 3])
                        confirmar_baja = c_del1.checkbox("⚠️ Confirmo que deseo desechar este activo (Enviar a Punto Limpio).", key=f"del_chk_act_{id_act}")
                        
                        if c_del2.button("🚫 Dar de Baja", disabled=not confirmar_baja, use_container_width=True):
                            with st.spinner("Registrando baja y ajustando patrimonio..."):
                                var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                                usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                                
                                # 🚀 CASCADA CONTABLE DE PÉRDIDA POR BAJA
                                if es_op and float(datos_act.get('valor_compra', 0)) > 0:
                                    try:
                                        val_perdida = float(datos_act['valor_compra'])
                                        desc_baja = f"BAJA ACTIVO: {datos_act['nombre']} ({cod_seleccionado})"
                                        res_ast_baja = supabase.table("fin_asientos").insert({
                                            "fecha_contable": time.strftime("%Y-%m-%d"), "descripcion": desc_baja,
                                            "concepto_general": "Baja/Pérdida de Activo Fijo", "origen": "MODULO_ACTIVOS",
                                            "moneda": moneda_sesion, "estado": "CONTABILIZADO"
                                        }).execute()
                                        id_ast_baja = res_ast_baja.data[0]['id']

                                        # Cuenta Activos (15/21) disminuye, Gastos (53/67) aumenta
                                        res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo").eq("moneda", moneda_sesion).execute()
                                        df_ctas = pd.DataFrame(res_ctas.data) if res_ctas.data else pd.DataFrame()
                                        
                                        id_cta_activo, id_cta_gasto = None, None
                                        if not df_ctas.empty:
                                            cta_act = df_ctas[df_ctas['codigo'].str.startswith('15', na=False)]
                                            if not cta_act.empty: id_cta_activo = cta_act.iloc[0]['id']
                                            
                                            cta_gas = df_ctas[df_ctas['codigo'].str.startswith('53', na=False) | df_ctas['codigo'].str.startswith('51', na=False)]
                                            if not cta_gas.empty: id_cta_gasto = cta_gas.iloc[0]['id']    
                                        if id_cta_activo and id_cta_gasto:
                                            supabase.table("fin_apuntes").insert([
                                                {"id_asiento": id_ast_baja, "id_cuenta_contable": int(id_cta_gasto), "debito": val_perdida, "credito": 0.0, "descripcion_linea": "Pérdida por retiro"},
                                                {"id_asiento": id_ast_baja, "id_cuenta_contable": int(id_cta_activo), "debito": 0.0, "credito": val_perdida, "descripcion_linea": "Salida de activo"}
                                            ]).execute()
                                    except Exception as e:
                                        pass # Fallback silencioso si no existen cuentas                                
                                log_accion(supabase, usuario_actual, "BAJA ACTIVO", f"{cod_seleccionado} enviado a Punto Limpio.")
                                
                                st.success("✅ Activo enviado a Punto Limpio y pérdida patrimonial registrada.")
                                time.sleep(2.0); st.session_state.modo_activo = "NADA"; st.rerun()
# --- PANEL: MOVER ACTIVO ---
        elif st.session_state.modo_activo == "MOVER":
            st.markdown("---")
            st.markdown("### 📦 Mover / Trasladar Activo Fijo")

            try:
                # 🚀 Traemos la información completa
                res_act_mov = supabase.table("activos").select("*, operadores(nombre), inmuebles(nombre), unidades(nombre)").eq("moneda", moneda_sesion).order("codigo_unico", desc=True).execute()
                df_a_mov = pd.DataFrame(res_act_mov.data) if res_act_mov.data else pd.DataFrame()
            except:
                df_a_mov = pd.DataFrame()

            if df_a_mov.empty:
                st.warning("No hay activos registrados para mover.")
                if st.button("❌ Cerrar Panel"): st.session_state.modo_activo = "NADA"; st.rerun()
            else:
                def get_ubicacion_mov(row):
                    ubi = str(row.get('ubicacion_tipo', 'Bodega'))
                    if ubi == 'Zona Común' and isinstance(row.get('inmuebles'), dict):
                        return f"{row['inmuebles'].get('nombre', '')}: Común"
                    elif ubi == 'Unidad' and isinstance(row.get('unidades'), dict):
                        inm_nom = row['inmuebles'].get('nombre', '') if isinstance(row.get('inmuebles'), dict) else ""
                        return f"{inm_nom}: {row['unidades'].get('nombre', '')}"
                    return ubi
                
                df_a_mov['UBICACION'] = df_a_mov.apply(get_ubicacion_mov, axis=1)

                st.markdown("**🔍 Buscar activo a trasladar**")
                c_f1, c_f2, c_f3 = st.columns([4, 3, 3])
                
                busqueda_mov = c_f1.text_input("Buscar Código o Nombre...", "", key="busq_mov_act").upper().strip()
                lista_ubicaciones = ["TODAS"] + sorted(df_a_mov['UBICACION'].dropna().unique().tolist())
                filtro_ubi = c_f2.selectbox("Filtrar por Ubicación", lista_ubicaciones, key="ubi_mov_act")
                lista_categorias = ["TODAS"] + sorted(df_a_mov['categoria'].dropna().unique().tolist())
                filtro_cat = c_f3.selectbox("Filtrar por Categoría", lista_categorias, key="cat_mov_act")

                df_filtrado_mov = df_a_mov.copy()
                if busqueda_mov:
                    df_filtrado_mov = df_filtrado_mov[df_filtrado_mov['codigo_unico'].str.contains(busqueda_mov) | df_filtrado_mov['nombre'].str.contains(busqueda_mov)]
                if filtro_ubi != "TODAS":
                    df_filtrado_mov = df_filtrado_mov[df_filtrado_mov['UBICACION'] == filtro_ubi]
                if filtro_cat != "TODAS":
                    df_filtrado_mov = df_filtrado_mov[df_filtrado_mov['categoria'] == filtro_cat]

                if df_filtrado_mov.empty:
                    st.warning("⚠️ No se encontraron activos con estos filtros.")
                    if st.button("❌ Cancelar", key="btn_cancel_mov_empty"): st.session_state.modo_activo = "NADA"; st.rerun()
                else:
                    opciones_act_mov = df_filtrado_mov.apply(lambda r: f"{r['codigo_unico']} - {r['nombre']} ({r['UBICACION']})", axis=1).tolist()
                    act_mov_sel = st.selectbox("Selecciona el Activo exacto:", opciones_act_mov)

                    if act_mov_sel:
                        cod_seleccionado = act_mov_sel.split(" - ")[0]
                        datos_act = df_filtrado_mov[df_filtrado_mov['codigo_unico'] == cod_seleccionado].iloc[0]
                        id_act = str(datos_act['id'])
                        ubi_actual_str = datos_act['UBICACION']

                        st.info(f"📍 **Ubicación Actual:** {ubi_actual_str}")

                        # 🚀 USAMOS CONTENEDOR DINÁMICO (Sin st.form para que los menús reaccionen en vivo)
                        with st.container():
                            st.write("**Nueva Ubicación Física**")
                            c5, c6, c7 = st.columns(3)
                            
                            n_ubic_tipo = c5.selectbox("Destino *", ["Bodega", "Zona Común", "Unidad"], key="n_ubi_tipo_din")
                            n_id_inm_sel, n_id_uni_sel = None, None
                            
                            if n_ubic_tipo in ["Zona Común", "Unidad"]:
                                n_inm_sel = c6.selectbox("Edificio Destino *", df_inm_act['nombre'].tolist(), key="n_inm_sel_din")
                                n_id_inm_sel = df_inm_act[df_inm_act['nombre'] == n_inm_sel].iloc[0]['id']
                                
                                if n_ubic_tipo == "Unidad":
                                    res_u = supabase.table("unidades").select("id, nombre").eq("id_inmueble", int(n_id_inm_sel)).eq("estado", "ACTIVO").execute()
                                    df_u = pd.DataFrame(res_u.data) if res_u.data else pd.DataFrame()
                                    if not df_u.empty:
                                        n_uni_sel = c7.selectbox("Unidad Destino *", df_u['nombre'].tolist(), key="n_uni_sel_din")
                                        n_id_uni_sel = df_u[df_u['nombre'] == n_uni_sel].iloc[0]['id']
                                    else:
                                        c7.warning("El edificio destino no tiene unidades.")
                            
                            motivo_mov = st.text_input("Motivo del traslado *", placeholder="Ej: Solicitud de inquilino, reubicación de bodega, etc.", key="motivo_mov")

                            st.markdown("---")
                            col_b1, col_b2, _ = st.columns([2.0, 1.5, 6.5]) 
                            
                            if col_b1.button("💾 Ejecutar Traslado", key="btn_save_mov"):
                                if not motivo_mov:
                                    st.error("❌ Debes indicar el motivo del traslado.")
                                elif n_ubic_tipo == "Unidad" and not n_id_uni_sel:
                                    st.error("❌ Selecciona una unidad destino válida.")
                                else:
                                    with st.spinner("Registrando movimiento logístico..."):
                                        try:
                                            # 1. Actualizamos la tabla maestra de activos
                                            upd_loc = {
                                                "ubicacion_tipo": n_ubic_tipo,
                                                "inmueble_id": int(n_id_inm_sel) if n_id_inm_sel else None,
                                                "unidad_id": int(n_id_uni_sel) if n_id_uni_sel else None
                                            }
                                            supabase.table("activos").update(upd_loc).eq("id", id_act).execute()
                                            
                                            # 2. Guardamos la auditoría estricta del movimiento
                                            var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
                                            usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
                                            
                                            supabase.table("activos_movimientos").insert({
                                                "activo_id": id_act,
                                                "origen_tipo": f"Desde: {ubi_actual_str}", 
                                                "destino_tipo": n_ubic_tipo,
                                                "motivo": motivo_mov.strip(),
                                                "usuario_responsable": usuario_actual
                                            }).execute()

                                            # 3. Disparamos la alerta al LOG GLOBAL
                                            log_accion(supabase, usuario_actual, "TRASLADO ACTIVO", f"{datos_act['codigo_unico']} -> Movido a {n_ubic_tipo}")

                                            st.success("✅ Traslado completado y registrado con éxito.")
                                            time.sleep(1.5)
                                            st.session_state.modo_activo = "NADA"
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error técnico: {e}")

                            if col_b2.button("❌ Cancelar", key="btn_cancel_mov"):
                                st.session_state.modo_activo = "NADA"
                                st.rerun()

# --- PANEL: REPORTES DE ACTIVOS ---
        elif st.session_state.modo_activo == "REPORTES":
            st.markdown("---")
            st.markdown("### 📊 Centro de Reportes y Auditoría de Activos")
            
            var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
            usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

            try: 
                res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
                df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
            except: df_ops = pd.DataFrame()

            # 🚀 LOS 10 REPORTES DE GRADO DIRECTOR
            tipo_rep = st.selectbox("Selecciona el tipo de reporte financiero/operativo:", [
                "1. Inventario Global (Todos los activos)",
                "2. Origen: Aportaciones de Socios",
                "3. Origen: Compras de la Empresa",
                "4. Propiedad: Activos del Propietario (Terceros)",
                "5. Auditoría: Activos sin Factura",
                "6. Inversión por Inmueble (Edificios)",
                "7. Detalle Fino por Unidad (Habitaciones)",
                "8. Activos Improductivos (En Bodega)",
                "9. Control de Garantías",
                "10. Historial de Movimientos"
            ])

            res_act_rep = supabase.table("activos").select("*, operadores(nombre), inmuebles(nombre), unidades(nombre)").eq("moneda", moneda_sesion).order("codigo_unico", desc=True).execute()
            df_a_rep = pd.DataFrame(res_act_rep.data) if res_act_rep.data else pd.DataFrame()
            
            if df_a_rep.empty:
                st.warning("No hay activos registrados en esta región para generar reportes.")
            else:
                def format_rep(df_in):
                    df_out = df_in.copy()
                    df_out['DUEÑO'] = df_out.apply(lambda r: r['operadores'].get('nombre', 'Operador') if r.get('propiedad') == 'Empresa' and isinstance(r.get('operadores'), dict) else "Propietario", axis=1)
                    df_out['UBICACIÓN'] = df_out.apply(lambda r: f"{r['inmuebles'].get('nombre', '')}: Común" if str(r.get('ubicacion_tipo')) == 'Zona Común' and isinstance(r.get('inmuebles'), dict) else (f"{r['inmuebles'].get('nombre', '') if isinstance(r.get('inmuebles'), dict) else ''}: {r['unidades'].get('nombre', '')}" if str(r.get('ubicacion_tipo')) == 'Unidad' and isinstance(r.get('unidades'), dict) else str(r.get('ubicacion_tipo', 'Bodega'))), axis=1)
                    df_out['VALOR'] = pd.to_numeric(df_out['valor_compra']).fillna(0).apply(lambda x: f"{simbolo_mon} {x:,.2f}" if x > 0 else "-")
                    df_out.rename(columns={'codigo_unico': 'CÓDIGO', 'nombre': 'ACTIVO', 'categoria': 'CATEGORÍA', 'estado': 'ESTADO', 'inicio_garantia': 'COMPRA', 'fin_garantia': 'FIN GARANTÍA'}, inplace=True)
                    
                    # Filtros Ocultos para cálculos
                    df_out['ORIGEN'] = df_out.get('origen', 'PROPIETARIO')
                    df_out['SOPORTE'] = df_out.get('factura_url', None).apply(lambda x: "SIN FACTURA" if pd.isna(x) or str(x).strip() == "" else "CON FACTURA")
                    df_out['INM_NOMBRE'] = df_out.apply(lambda r: r['inmuebles'].get('nombre', 'Sin Inmueble') if isinstance(r.get('inmuebles'), dict) else 'Sin Inmueble', axis=1)
                    
                    return df_out[['CÓDIGO', 'ACTIVO', 'CATEGORÍA', 'DUEÑO', 'ORIGEN', 'UBICACIÓN', 'ESTADO', 'VALOR', 'SOPORTE', 'COMPRA', 'FIN GARANTÍA', 'ubicacion_tipo', 'propiedad', 'INM_NOMBRE', 'valor_compra']]

                df_base_rep = format_rep(df_a_rep)
                df_export = pd.DataFrame()
                nombre_pdf = ""
                
                # Columnas estándar para que el PDF no se desborde
                columnas_estandar = ['CÓDIGO', 'ACTIVO', 'CATEGORÍA', 'UBICACIÓN', 'ESTADO', 'VALOR']

                if "1. Inventario Global" in tipo_rep:
                    df_export = df_base_rep[columnas_estandar]
                    nombre_pdf = "inventario_global"

                elif "2. Origen: Aportaciones" in tipo_rep:
                    df_export = df_base_rep[df_base_rep['ORIGEN'] == 'APORTACIÓN DE SOCIO']
                    val_tot = df_export['valor_compra'].sum()
                    st.success(f"💰 **Total Patrimonio Aportado en Especie:** {simbolo_mon} {val_tot:,.2f}")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "aportaciones_socios"

                elif "3. Origen: Compras" in tipo_rep:
                    df_export = df_base_rep[df_base_rep['ORIGEN'] == 'COMPRA DIRECTA']
                    val_tot = df_export['valor_compra'].sum()
                    st.success(f"💸 **Total Activos Comprados por la Empresa:** {simbolo_mon} {val_tot:,.2f}")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "compras_empresa"

                elif "4. Propiedad: Activos del Propietario" in tipo_rep:
                    df_export = df_base_rep[df_base_rep['propiedad'] == 'Propietario']
                    st.info("💡 Estos activos pertenecen al dueño del inmueble, no aumentan tu patrimonio ni se deprecian en tu empresa.")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "activos_propietario"

                elif "5. Auditoría: Activos sin Factura" in tipo_rep:
                    df_export = df_base_rep[df_base_rep['SOPORTE'] == 'SIN FACTURA']
                    val_tot = df_export[df_export['propiedad'] == 'Empresa']['valor_compra'].sum()
                    st.error(f"🚨 **Atención:** Hay {len(df_export)} activos sin soporte documental físico. Valor sin sustento: {simbolo_mon} {val_tot:,.2f}")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "auditoria_sin_factura"

                elif "6. Inversión por Inmueble" in tipo_rep:
                    lista_inm = df_base_rep[df_base_rep['ubicacion_tipo'].isin(['Zona Común', 'Unidad'])]['INM_NOMBRE'].unique().tolist()
                    if lista_inm:
                        inm_sel = st.selectbox("Selecciona el Inmueble a evaluar:", lista_inm)
                        df_export = df_base_rep[df_base_rep['INM_NOMBRE'] == inm_sel]
                        val_tot = df_export[df_export['propiedad'] == 'Empresa']['valor_compra'].sum()
                        st.success(f"🏢 **Inversión total de la Empresa en este inmueble:** {simbolo_mon} {val_tot:,.2f}")
                    else:
                        st.warning("No hay activos asignados a inmuebles.")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "inversion_inmueble"

                elif "7. Detalle Fino por Unidad" in tipo_rep:
                    df_export = df_base_rep[df_base_rep['ubicacion_tipo'] == 'Unidad']
                    lista_inm = df_export['INM_NOMBRE'].unique().tolist()
                    if lista_inm:
                        inm_sel = st.selectbox("Filtra por Edificio:", ["Todos"] + lista_inm)
                        if inm_sel != "Todos": df_export = df_export[df_export['INM_NOMBRE'] == inm_sel]
                        val_tot = df_export[df_export['propiedad'] == 'Empresa']['valor_compra'].sum()
                        st.info(f"🛏️ **Inversión en unidades filtradas:** {simbolo_mon} {val_tot:,.2f}")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "activos_unidades_fino"

                elif "8. Activos Improductivos" in tipo_rep:
                    df_export = df_base_rep[(df_base_rep['ubicacion_tipo'] == 'Bodega') | (df_base_rep['ESTADO'] == 'En bodega')]
                    val_tot = df_export[df_export['propiedad'] == 'Empresa']['valor_compra'].sum()
                    st.warning(f"📦 **Capital inmovilizado en Bodega (Improductivo):** {simbolo_mon} {val_tot:,.2f}")
                    df_export = df_export[columnas_estandar]
                    nombre_pdf = "activos_improductivos"

                elif "9. Control de Garantías" in tipo_rep:
                    df_export = df_base_rep[['CÓDIGO', 'ACTIVO', 'DUEÑO', 'UBICACIÓN', 'COMPRA', 'FIN GARANTÍA']].copy()
                    nombre_pdf = "control_garantias_activos"
                    st.info("💡 Muestra las fechas de compra y fin de garantía para gestionar mantenimientos.")

                elif "10. Historial de Movimientos" in tipo_rep:
                    res_mov = supabase.table("activos_movimientos").select("*, activos(codigo_unico, nombre)").order("fecha_movimiento", desc=True).execute()
                    df_m = pd.DataFrame(res_mov.data) if res_mov.data else pd.DataFrame()
                    if not df_m.empty:
                        df_m['FECHA'] = pd.to_datetime(df_m['fecha_movimiento']).dt.strftime('%d/%m/%Y %H:%M')
                        df_m['ACTIVO'] = df_m['activos'].apply(lambda x: f"{x.get('codigo_unico','')} - {x.get('nombre','')}" if isinstance(x, dict) else "N/A")
                        df_export = df_m[['FECHA', 'ACTIVO', 'origen_tipo', 'destino_tipo', 'motivo', 'usuario_responsable']].copy()
                        df_export.rename(columns={'origen_tipo': 'ORIGEN', 'destino_tipo': 'DESTINO', 'motivo': 'MOTIVO', 'usuario_responsable': 'USUARIO'}, inplace=True)
                    nombre_pdf = "trazabilidad_logistica"
                    st.info("💡 Registro de auditoría inmutable de traslados y bajas.")

                # --- 🚀 LANZAR EL GENERADOR DE REPORTES UNIVERSAL ---
                if not df_export.empty:
                    if "10. Historial" in tipo_rep:
                        panel_reportes_y_compartir(df_export, nombre_pdf, "Historial Activos", generar_pdf_movimientos, df_ops, supabase, usuario_actual, "modo_activo")
                    elif "9. Control de Garantías" in tipo_rep:
                        panel_reportes_y_compartir(df_export, nombre_pdf, "Reporte Garantías", generar_pdf_garantias, df_ops, supabase, usuario_actual, "modo_activo")
                    else:
                        panel_reportes_y_compartir(df_export, nombre_pdf, "Reporte Activos", generar_pdf_activos, df_ops, supabase, usuario_actual, "modo_activo")
                else:
                    st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")

            st.markdown("---")
            if st.button("❌ Cerrar Panel"): st.session_state.modo_activo = "NADA"; st.rerun()