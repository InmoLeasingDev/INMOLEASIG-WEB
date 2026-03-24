import streamlit as st
import pandas as pd
import time
import urllib.parse
import re
from fpdf import FPDF

# --- NUESTRA LIBRERÍA MAESTRA ---
from herramientas import log_accion, enviar_reporte_correo, generar_excel_bytes, panel_reportes_y_compartir, panel_gestor_galeria
# =========================================
# 1. MOTOR PDF PROPIEDADES
# =========================================
def generar_pdf_propiedades(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE PROPIEDADES", ln=True, align="C")
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
def generar_pdf_unidades(df):
    pdf = FPDF(orientation="L") # Horizontal (Landscape)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE UNIDADES", ln=True, align="C")
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
def generar_pdf_mandatos(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE MANDATOS Y CONTRATOS", ln=True, align="C")
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
def generar_pdf_ficha_mandato(df):
    # 💡 EL TRUCO: Extraemos la única fila del DataFrame y la volvemos diccionario
    datos = df.iloc[0].to_dict()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 15)

    pdf.cell(0, 10, "INMOLEASING - FICHA TECNICA DE CONTRATO", ln=True, align="C")
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
def generar_pdf_historial_mandato(df):
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - HISTORIAL DE AUDITORIA DEL CONTRATO", ln=True, align="C")
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
# MÓDULO PRINCIPAL: INMUEBLES
# ==========================================
def mostrar_modulo_inmuebles(supabase):
    st.header("🏢 Gestión de Inmuebles e Inventarios")
    MOD_VERSION = "v1.0  )"
    st.caption(f"⚙️ Módulo Inmuebles {MOD_VERSION} | Control de Propiedades, Unidades, Mandatos e Inventarios.")

    # --- Identificar al usuario para los logs ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- CREACIÓN DE LAS 4 PESTAÑAS MAESTRAS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 1. Propiedades", 
        "🚪 2. Unidades", 
        "🤝 3. Mandatos", 
        "🛋️ 4. Inventarios"
    ])

   
    # ==========================================
    # TAB 1: PROPIEDADES (CRUD + REPORTES)
    # ==========================================
    with tab1:
        # 1. Inicializador de estado para los paneles
        if 'modo_propiedad' not in st.session_state:
            st.session_state.modo_propiedad = "NADA"

        # 2. Cargar Operadores (para uso de reportes)
        try:
            res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()

        # 3. Lógica dinámica de región
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

        # --- LECTURA DE DATOS (LA CUADRÍCULA) ---
        query = supabase.table("inmuebles").select("*").eq("estado", "ACTIVO")
        if moneda_sesion != "ALL": query = query.eq("moneda", moneda_sesion)
            
        res_inm = query.execute()
        df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
        
        st.write("") # Pequeño respiro visual
        
        if not df_inm.empty:
            df_inm = df_inm.sort_values(by=['moneda', 'nombre'], ascending=[True, True])
            
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
            st.session_state.modo_propiedad = "NADA"  # 🛡️ Cierra los paneles si la tabla se vacía
            st.info("ℹ️ Aún no hay propiedades registradas o activas en tu región.")

        
        # ==========================================
        # 🛠️ BARRA DE HERRAMIENTAS (MODO PRO - 4 BOTONES)
        # ==========================================
        t_c1, t_c2, t_c3, t_c4, t_c5 = st.columns([1.5, 1.5, 1.5, 1.5, 4.0]) 
        
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
                
            if t_c4.button("📊 Reportes", key="btn_rep_prop", use_container_width=True):
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
                
                st.markdown("---")
                # Botonera Minimalista
                col_b1, col_b2, col_esp = st.columns([1.5, 1.2, 7.3])
                
                if col_b1.form_submit_button("💾 Guardar"):
                    if n_nom and n_ciu:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(), "tipo": n_tip, "ciudad": n_ciu.strip().upper(),
                            "moneda": n_mon, "referencia_catastral": n_cat.strip().upper(),
                            "aseguradora": n_ase.strip().upper(), "numero_poliza": n_pol.strip().upper(), 
                            "telefono_aseguradora": n_tel_ase.strip(), "estado": "ACTIVO"
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
                    
                    st.markdown("---")
                    # Botonera Minimalista de Gestión
                    col_b1, col_b2, col_esp = st.columns([1.5, 1.2, 7.3])
                    
                    if col_b1.form_submit_button("💾 Guardar"):
                        datos_upd = {
                            "nombre": e_nom.strip().upper(), "ciudad": e_ciu.strip().upper(),
                            "moneda": e_mon, "referencia_catastral": e_cat.strip().upper(),
                            "aseguradora": e_ase.strip().upper(), "numero_poliza": e_pol.strip().upper()
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
            # Llamamos a nuestra super herramienta de reportes
            panel_reportes_y_compartir(
                df_datos=df_display.drop(columns=['id']), 
                nombre_base=f"propiedades_activas",
                modulo_origen="Propiedades",
                funcion_pdf=generar_pdf_propiedades,
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

        # --- Cargar Operadores (para uso de reportes) ---
        try:
            res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()

        # 1. Traer los inmuebles activos CON SU MONEDA
        query_inm = supabase.table("inmuebles").select("id, nombre, moneda").eq("estado", "ACTIVO")
        moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
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
                
                # 🛡️ ESCUDO 3: Si la propiedad no tiene unidades, forzamos cierre de paneles
                if df_uni.empty:
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
                                # Cruzar unidades con propiedades para heredar el nombre del edificio y su moneda
                                df_cruce = df_all.merge(df_prop[['id', 'nombre', 'moneda']], left_on='id_inmueble', right_on='id', how='left')
                                
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
                            # 🚀 LÁNZALO A NUESTRO MOTOR CENTRAL
                            panel_reportes_y_compartir(
                                df_datos=df_final, 
                                nombre_base=f"unidades_{etiqueta_prop}_{etiqueta_est}",
                                modulo_origen=f"Unidades",
                                funcion_pdf=generar_pdf_unidades,
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

        st.markdown("### 🤝 Contratos de Gestión Integral")

        # --- 1. CARGA DE DATOS BASE ---
        try:
            res_inm = supabase.table("inmuebles").select("id, nombre, moneda").eq("estado", "ACTIVO").execute()
            df_inm_m = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
            
            res_prop = supabase.table("propietarios").select("id, nombre, cuenta_banco").eq("estado", "ACTIVO").execute()
            df_prop_m = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
            
            res_man = supabase.table("mandatos").select("*").neq("estado_contrato", "FINALIZADO").execute()
            df_man = pd.DataFrame(res_man.data) if res_man.data else pd.DataFrame()
        except Exception as e:
            df_inm_m, df_prop_m, df_man = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            st.warning("⚠️ Conectando con las tablas de mandatos...")

        # --- 2. GRID DE MANDATOS (CON VISOR DE DOCUMENTOS 📄) ---
        if not df_man.empty and not df_inm_m.empty and not df_prop_m.empty:
            df_view = df_man.merge(df_inm_m[['id', 'nombre']], left_on='id_inmueble', right_on='id', how='left')
            df_view = df_view.merge(df_prop_m[['id', 'nombre']], left_on='id_propietario', right_on='id', how='left', suffixes=('_inm', '_prop'))
            
            def visor_docs(row):
                iconos = []
                if row.get('url_contrato'): iconos.append("📄")
                if row.get('url_empadronamiento'): iconos.append("🏠")
                if row.get('url_inventario'): iconos.append("📦")
                if row.get('url_suministros'): iconos.append("💧")
                return " ".join(iconos) if iconos else "➖"

            df_view['DOCS'] = df_view.apply(visor_docs, axis=1)
            
            df_view_display = df_view[['nombre_inm', 'nombre_prop', 'porcentaje_pago_1', 'ingreso_garantizado', 'estado_financiero', 'DOCS']].copy()
            df_view_display.rename(columns={
                'nombre_inm': 'INMUEBLE', 'nombre_prop': 'TITULAR', 
                'porcentaje_pago_1': '% COBRO', 'ingreso_garantizado': 'RENTA',
                'estado_financiero': 'FINANZAS'
            }, inplace=True)
            
            st.dataframe(df_view_display, use_container_width=True, hide_index=True)
            st.caption("Legenda DOCS: 📄 Contrato | 🏠 Empadronamiento | 📦 Inventario | 💧 Suministros")
        else:
            st.info("ℹ️ No hay mandatos vigentes. Crea uno nuevo para empezar a gestionar contratos.")

        # --- 3. BARRA DE HERRAMIENTAS ---
        st.markdown("---")
        # Ajustamos las columnas para que quepan 6 botones elegantemente
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns([1.5, 1.5, 1.8, 1.5, 1.6, 1.7])
        
        if m_c1.button("➕ Nuevo", key="btn_nuevo_man", use_container_width=True):
            st.session_state.modo_mandato = "CREAR"
            st.rerun()
            
        if not df_man.empty:
            if m_c2.button("⚙️ Gestionar", key="btn_edit_man", use_container_width=True):
                st.session_state.modo_mandato = "EDITAR"
                st.rerun()
            if m_c3.button("📁 Documentos", key="btn_docs_man", use_container_width=True):
                st.session_state.modo_mandato = "DOCUMENTOS"
                st.rerun()
            if m_c4.button("💰 Pagos", key="btn_pagos_man", use_container_width=True):
                st.session_state.modo_mandato = "PAGOS"
                st.rerun()
            if m_c5.button("📜 Historial", key="btn_hist_man", use_container_width=True):
                st.session_state.modo_mandato = "HISTORIAL"
                st.rerun()
            if m_c6.button("📊 Reportes", key="btn_rep_man", use_container_width=True):
                st.session_state.modo_mandato = "REPORTES"
                st.rerun()

        # --- 4. PANEL CREAR (DISEÑO PRO) ---
        if st.session_state.modo_mandato == "CREAR":
            from dateutil.relativedelta import relativedelta
            st.markdown("---")
            with st.form("form_nuevo_mandato_pro", clear_on_submit=False):
                st.markdown("### 📝 Redactar Nuevo Contrato de Gestión")
                
                # SECCIÓN 1: VÍNCULO Y CUENTAS
                st.markdown("#### 💼 1. Titularidad y Distribución de Pagos")
                m_inm_sel = st.selectbox("Inmueble a gestionar *", df_inm_m['nombre'].tolist())
                
                st.write("**Titular 1 (Principal)**")
                c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 4.6])
                m_prop_sel_1 = c1.selectbox("Propietario 1 *", df_prop_m['nombre'].tolist(), key="p1")
                
                # ARRASTRE AUTOMÁTICO DE IBAN
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

                
                # SECCIÓN 2: CRONOGRAMA AUTOMÁTICO
                st.markdown("#### 📅 2. Cronograma Automático (Smart Dates)")
                
                # Fila 1: Lo primero que ocurre es la Firma
                d1, d2, d3 = st.columns(3)
                f_suscripcion = d1.date_input("Fecha de Suscripción / Firma *")
                duracion_anos = d2.number_input("Duración Contrato (Años)", 1, 20, 5)
                meses_aviso = d3.number_input("Meses Preaviso No Renovación", 1, 12, 2)
                
                # Fila 2: Luego se entregan las llaves y empiezan a contar los pagos/carencia
                d4, d5, d6 = st.columns(3)
                f_entrega = d4.date_input("Fecha Entrega Llaves *")
                meses_carencia = d5.number_input("Meses de Carencia", 0, 12, 0)
                f_vencimiento = f_suscripcion + relativedelta(years=duracion_anos)
                f_inicio_pagos = f_entrega + relativedelta(months=meses_carencia)
                f_limite_aviso = f_vencimiento - relativedelta(months=meses_aviso)

                # --- FILA DE RESUMEN CON BOTÓN DE RECÁLCULO ---
                c_res1, c_res2 = st.columns([8.5, 1.5])
                c_res1.success(f"🗓️ **Resumen:** Pagos inician: **{f_inicio_pagos}** | Vence: **{f_vencimiento}** | Preaviso: **{f_limite_aviso}**")
                
                # Este botón de "form_submit_button" actualiza la pantalla sin guardar nada
                c_res2.form_submit_button("🔄 Recalcular")
                # SECCIÓN 3: ACUERDO ECONÓMICO Y PENALIZACIÓN
                st.markdown("#### 💰 3. Acuerdo Económico")
                e1, e2, e3 = st.columns(3)
                m_renta = e1.number_input("Renta Garantizada *", min_value=0.0, step=50.0)
                m_fianza = e2.number_input("Fianza a Entregar *", min_value=0.0, step=50.0)
                m_act = e3.selectbox("Actualización Anual", ["IPC", "FIJO", "NO APLICA"])

                # --- LÓGICA DE INDEMNIZACIÓN Y AMORTIZACIÓN ---
                st.info("🛡️ Cláusula de protección (Amortización de Mejoras)")
                c_ind1, c_ind2 = st.columns([2, 1])
                
                m_tipo_ind_ui = c_ind1.selectbox(
                    "Modalidad de Penalización", 
                    ["NO APLICA", "MONTO FIJO (Cualquier momento)", "AMORTIZACIÓN DECRECIENTE (5 Años)"]
                )
                
                # Traductor para la base de datos
                mapa_ind = {
                    "NO APLICA": "NINGUNA", 
                    "MONTO FIJO (Cualquier momento)": "FIJA", 
                    "AMORTIZACIÓN DECRECIENTE (5 Años)": "DECRECIENTE_5Y"
                }
                m_tipo_ind_db = mapa_ind[m_tipo_ind_ui]

                m_indemnizacion = c_ind2.number_input(
                    "Monto Base 100% (€)", 
                    min_value=0.0, step=50.0, 
                    help="Costo total de la mejora. Si es decreciente, se calculará el % según el año."
                )

                # SECCIÓN 4: DOCUMENTOS
                st.markdown("#### 📁 4. Documentación Escaneada")
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
                        st.error("❌ Los porcentajes superan el 100%. Por favor revísalos.")
                    else:
                        with st.spinner("Subiendo archivos y registrando en base de datos..."):
                            try:
                                id_inm = df_inm_m[df_inm_m['nombre'] == m_inm_sel].iloc[0]['id']
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
                                    "porcentaje_propiedad": m_porc_prop_1, "porcentaje_propiedad_2": m_porc_prop_2,
                                    "porcentaje_pago_1": m_porc_pago_1, "porcentaje_pago_2": m_porc_pago_2,
                                    "cuenta_pago": m_iban_1, "cuenta_pago_2": m_iban_2,
                                    "ingreso_garantizado": m_renta, "valor_fianza": m_fianza,
                                    "tipo_actualizacion": m_act, 
                                    "tipo_indemnizacion": m_tipo_ind_db, 
                                    "indemnizacion_anticipada": m_indemnizacion,
                                    "fecha_suscripcion": str(f_suscripcion), "fecha_entrega": str(f_entrega),
                                    "fecha_inicio_pagos": str(f_inicio_pagos), "fecha_terminacion": str(f_vencimiento),
                                    "fecha_aviso_no_renovacion": str(f_limite_aviso),
                                    "url_contrato": url_c, "url_empadronamiento": url_e,
                                    "url_inventario": url_i, "url_suministros": url_s,
                                    "estado_contrato": "FIRMADO", "estado_financiero": "PENDIENTE_FIANZA"
                                }
                                res = supabase.table("mandatos").insert(datos).execute()
                                
                                # Usamos la variable 'usuario_actual' global que definimos al inicio del módulo
                                # Inyectamos la fecha legal de suscripción en el texto descriptivo del historial
                                supabase.table("historial_mandatos").insert({
                                "id_mandato": res.data[0]['id'], 
                                "accion": f"CREACIÓN DE MANDATO (Firma Legal: {f_suscripcion})",
                                "usuario": usuario_actual
                            }).execute()

                                st.success("✅ Mandato registrado con éxito.")
                                st.session_state.modo_mandato = "NADA"
                                time.sleep(1.5); st.rerun()
                            except Exception as e: st.error(f"❌ Error al guardar: {e}")

                if col_b2.form_submit_button("❌ Cancelar"):
                    st.session_state.modo_mandato = "NADA"; st.rerun()

        # --- 5. PANEL PAGOS (VERSIÓN ERP CON CASCADA FINANCIERA) ---
        elif st.session_state.modo_mandato == "PAGOS" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 💰 Gestión de Pagos y Soportes Bancarios")
            
            # 1. Cargar Cuentas Bancarias Activas (Para elegir de dónde sale el dinero)
            try:
                res_bancos = supabase.table("fin_cuentas_bancarias").select("id, nombre_interno, banco, saldo_actual").eq("estado", "ACTIVO").execute()
                df_cuentas = pd.DataFrame(res_bancos.data) if res_bancos.data else pd.DataFrame()
            except:
                df_cuentas = pd.DataFrame()

            op_man = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel = st.selectbox("Selecciona el Mandato a pagar:", op_man)
            
            if m_sel:
                idx = op_man.index(m_sel)
                id_m = df_man.iloc[idx]['id']
                d_m = df_man.iloc[idx]
                
                st.info(f"**Acuerdo Actual:** Renta: **{d_m['ingreso_garantizado']}** | Fianza: **{d_m['valor_fianza']}** | Estado: **{d_m['estado_financiero']}**")
                
                c_f, c_h = st.columns([1.2, 1])
                with c_f:
                    with st.form(f"form_pago_{id_m}", clear_on_submit=True):
                        st.subheader("📤 Registrar Egreso / Pago")
                        
                        p_c1, p_c2 = st.columns(2)
                        conc = p_c1.text_input("Concepto", value="PAGO FIANZA" if d_m['estado_financiero'] == "PENDIENTE_FIANZA" else "ALQUILER MES")
                        fecha_pago = p_c2.date_input("Fecha del Pago") # <- IMPORTANTE PARA BACKDATING (Ej: 18/03/2026)
                        
                        p_c3, p_c4 = st.columns(2)
                        monto = p_c3.number_input("Monto (€/$)", value=float(d_m['valor_fianza'] if d_m['estado_financiero'] == "PENDIENTE_FIANZA" else d_m['ingreso_garantizado']))
                        
                        # Selector de cuenta bancaria
                        if not df_cuentas.empty:
                            opciones_cta = [f"{r['nombre_interno']} ({r['banco']}) - Saldo: {r['saldo_actual']}" for _, r in df_cuentas.iterrows()]
                            cta_sel = p_c4.selectbox("Cuenta de Origen *", opciones_cta)
                        else:
                            cta_sel = p_c4.selectbox("Cuenta de Origen *", ["No hay cuentas registradas"])
                            
                        sop = st.file_uploader("Adjuntar Soporte del Banco", type=["pdf", "jpg", "png"])
                        
                        if st.form_submit_button("💾 Ejecutar Pago y Actualizar Bancos"):
                            if df_cuentas.empty:
                                st.error("❌ Debes crear una cuenta bancaria primero en el módulo Tesorería.")
                            else:
                                with st.spinner("Procesando cascada financiera..."):
                                    try:
                                        # Identificar la cuenta seleccionada
                                        idx_cta = opciones_cta.index(cta_sel)
                                        id_cta = df_cuentas.iloc[idx_cta]['id']
                                        saldo_anterior = float(df_cuentas.iloc[idx_cta]['saldo_actual'])
                                        
                                        # 1. Subir soporte al Bucket
                                        u_s = None
                                        if sop:
                                            ext = sop.name.split('.')[-1].lower()
                                            # 💡 SOLUCIÓN: Le decimos explícitamente al navegador qué tipo de archivo es
                                            tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                            n_s = f"soporte_{id_m}_{int(time.time())}.{ext}"
                                            supabase.storage.from_("soportes_pagos").upload(n_s, sop.getvalue(), file_options={"content-type": tipo_mime})
                                            u_s = supabase.storage.from_("soportes_pagos").get_public_url(n_s)                                            
                                        # 2. Registrar en pagos_mandatos (Historial de la propiedad)
                                        supabase.table("pagos_mandatos").insert({
                                            "id_mandato": int(id_m), "concepto": conc, "monto": monto, 
                                            "fecha_pago": str(fecha_pago), "url_soporte_bancario": u_s, 
                                            "estado_envio": "PENDIENTE"
                                        }).execute()
                                        
                                        # 3. Registrar Movimiento Bancario (EGRESO EN TESORERÍA)
                                        supabase.table("fin_movimientos_banco").insert({
                                            "id_cuenta_bancaria": int(id_cta),
                                            "fecha_movimiento": str(fecha_pago),
                                            "tipo": "EGRESO",
                                            "monto": monto,
                                            "concepto": f"{conc} - MANDATO {id_m}",
                                            "estado_conciliacion": "PENDIENTE"
                                        }).execute()
                                        
                                        # 4. Actualizar Saldo de la Cuenta Bancaria (La matemática real)
                                        nuevo_saldo = saldo_anterior - monto
                                        supabase.table("fin_cuentas_bancarias").update({"saldo_actual": nuevo_saldo}).eq("id", int(id_cta)).execute()

                                        # 4.5 ¡MAGIA ERP! GENERAR ASIENTO CONTABLE AUTOMÁTICO (Partida Doble)
                                        id_cta_banco = supabase.table("fin_cuentas_contables").select("id").eq("codigo", "1110").execute().data[0]['id']
                                        # Lógica básica: Si es fianza a la 2505, si es alquiler a la 4105 (Ingresos)
                                        codigo_contra = "2505" if "FIANZA" in conc.upper() else "4105"
                                        id_cta_contra = supabase.table("fin_cuentas_contables").select("id").eq("codigo", codigo_contra).execute().data[0]['id']
                                        
                                        # A. Cabecera (Enviando doble concepto para evitar error NOT NULL)
                                        res_ast = supabase.table("fin_asientos").insert({
                                            "fecha_contable": str(fecha_pago),
                                            "descripcion": f"{conc} - MANDATO {id_m}",
                                            "concepto_general": f"{conc} - MANDATO {id_m}",
                                            "origen": "MODULO_PAGOS",
                                            "estado": "CONTABILIZADO"
                                        }).execute()
                                        id_ast_nuevo = res_ast.data[0]['id']
                                        
                                        # B. Apuntes
                                        supabase.table("fin_apuntes").insert({
                                            "id_asiento": id_ast_nuevo, "id_cuenta_contable": id_cta_banco,
                                            "debito": 0.0, "credito": float(monto), "descripcion_linea": "Salida de Tesorería"
                                        }).execute()
                                        supabase.table("fin_apuntes").insert({
                                            "id_asiento": id_ast_nuevo, "id_cuenta_contable": id_cta_contra,
                                            "debito": float(monto), "credito": 0.0, "descripcion_linea": conc
                                        }).execute()

                                        # 5. Actualizar Estado del Mandato
                                        supabase.table("mandatos").update({"estado_financiero": "AL_DIA"}).eq("id", int(id_m)).execute()
                                        
                                        # 6. Registrar en Historial Específico
                                        supabase.table("historial_mandatos").insert({
                                            "id_mandato": int(id_m), 
                                            "accion": f"PAGO REGISTRADO: {conc} ({monto}). Saldo banco actualizado y Asiento generado.",
                                            "usuario": usuario_actual
                                        }).execute()
                                        
                                        # 7. Registrar en el Log General de Usuarios
                                        log_accion(supabase, usuario_actual, "PAGO REGISTRADO", f"{conc} - Mandato ID: {id_m}")

                                        st.success("✅ ¡Cascada Financiera ejecutada! Banco y Contabilidad actualizados.")
                                        time.sleep(2); st.rerun()
                                    except Exception as e: 
                                        st.error(f"Error en la Cascada Financiera: {e}")

                with c_h:
                    # 💡 AÑADIMOS EL CONTENEDOR CON BORDE 
                    with st.container(border=True):
                        st.subheader("📚 Historial de Pagos")
                        try:
                            res_p = supabase.table("pagos_mandatos").select("*").eq("id_mandato", int(id_m)).order("fecha_pago", desc=True).execute()
                            df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
                        except: df_p = pd.DataFrame()
                            
                        if not df_p.empty:
                            for _, p in df_p.iterrows():
                                with st.expander(f"✅ {p['fecha_pago']} - {p['concepto']} ({p['monto']})"):
                                    if p['url_soporte_bancario']: st.markdown(f"**[🔍 Ver PDF del Banco]({p['url_soporte_bancario']})**")
                                    if st.button("📲 Compartir a Propietario", key=f"btn_comp_{p['id']}", use_container_width=True):
                                        st.toast("Módulo de envío en construcción 🚧", icon="⏳")
                        else: st.info("Sin pagos registrados.")
            st.markdown("---")
            if st.button("❌ Cerrar Panel"): st.session_state.modo_mandato = "NADA"; st.rerun()
        # --- PANEL: BÓVEDA DE DOCUMENTOS ---
        elif st.session_state.modo_mandato == "DOCUMENTOS" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 📁 Bóveda de Documentos Legales")
            
            # Selector del Contrato
            op_man_docs = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_doc = st.selectbox("Selecciona el Mandato para ver sus archivos:", op_man_docs)
            
            if m_sel_doc:
                idx = op_man_docs.index(m_sel_doc)
                d_m = df_man.iloc[idx]
                
                st.write("") # Espaciador
                c1, c2, c3, c4 = st.columns(4)
                
                def tarjeta_doc(columna, titulo, url_doc, icono):
                    with columna:
                        st.markdown(f"**{icono} {titulo}**")
                        if url_doc and str(url_doc).strip() != "None" and str(url_doc).strip() != "":
                            st.success("✅ Guardado en Nube")
                            st.markdown(f"[📥 Abrir / Ver Documento]({url_doc})")
                        else:
                            st.warning("❌ Pendiente")
                            
                tarjeta_doc(c1, "Contrato Firmado", d_m.get('url_contrato'), "📄")
                tarjeta_doc(c2, "Empadronamiento", d_m.get('url_empadronamiento'), "🏠")
                tarjeta_doc(c3, "Acta Inventario", d_m.get('url_inventario'), "📦")
                tarjeta_doc(c4, "Suministros", d_m.get('url_suministros'), "💧")
                
            st.markdown("---")
            if st.button("❌ Cerrar Bóveda", key="btn_cerrar_docs"): 
                st.session_state.modo_mandato = "NADA"
                st.rerun()
        # --- PANEL: HISTORIAL DE MANDATOS ---
        elif st.session_state.modo_mandato == "HISTORIAL" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 📜 Historial y Auditoría del Contrato")
            
            # Selector del Contrato
            op_man_hist = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_hist = st.selectbox("Selecciona el Mandato para ver su actividad:", op_man_hist)
            
            if m_sel_hist:
                idx = op_man_hist.index(m_sel_hist)
                id_m = df_man.iloc[idx]['id']
                
                try:
                    # Extraemos usando la columna real 'fecha_evento'
                    res_hist = supabase.table("historial_mandatos").select("fecha_evento, accion, usuario").eq("id_mandato", int(id_m)).order("fecha_evento", desc=True).execute()
                    df_h = pd.DataFrame(res_hist.data) if res_hist.data else pd.DataFrame()
                except Exception as e:
                    df_h = pd.DataFrame()
                    st.error(f"Error técnico al cargar historial: {e}")
                    
                if not df_h.empty:
                    # Formateamos la fecha correctamente
                    df_h['FECHA'] = pd.to_datetime(df_h['fecha_evento']).dt.strftime('%d/%m/%Y %H:%M')
                    df_h_display = df_h[['FECHA', 'accion', 'usuario']].copy()    
                    st.dataframe(df_h_display, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ No hay registros en el historial para este mandato todavía.")
            
            st.markdown("---")
            if st.button("❌ Cerrar Historial", key="btn_cerrar_hist"):
                st.session_state.modo_mandato = "NADA"
                st.rerun()

        # --- 6. PANELES EDITAR  ---
        elif st.session_state.modo_mandato == "EDITAR" and not df_man.empty:
            st.markdown("---")
            st.markdown("### ⚙️ Gestionar y Modificar Contrato")
            
            # Selector
            op_man_edit = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
            m_sel_edit = st.selectbox("Selecciona el Mandato a gestionar:", op_man_edit)

            if m_sel_edit:
                idx = op_man_edit.index(m_sel_edit)
                d_m = df_man.iloc[idx]
                id_m = str(d_m['id'])

                with st.form(f"form_edit_man_{id_m}", clear_on_submit=False):
                    st.write("**Actualizar Condiciones Financieras**")
                    c1, c2, c3 = st.columns(3)
                    e_renta = c1.number_input("Renta Garantizada (€/$)", value=float(d_m.get('ingreso_garantizado', 0.0)), step=50.0)
                    e_fianza = c2.number_input("Fianza (€/$)", value=float(d_m.get('valor_fianza', 0.0)), step=50.0)
                    
                    lista_act = ["IPC", "FIJO", "NO APLICA"]
                    idx_act = lista_act.index(d_m.get('tipo_actualizacion', 'IPC')) if d_m.get('tipo_actualizacion') in lista_act else 0
                    e_act = c3.selectbox("Actualización Anual", lista_act, index=idx_act)

                    st.write("**Actualizar Cuentas de Pago (IBAN)**")
                    c4, c5 = st.columns(2)
                    e_cta1 = c4.text_input("Cuenta / IBAN Principal", value=str(d_m.get('cuenta_pago', '')))
                    e_cta2 = c5.text_input("Cuenta / IBAN Secundaria", value=str(d_m.get('cuenta_pago_2', '')).replace("None", ""))

                    st.markdown("---")
                    col_b1, col_b2, _ = st.columns([2, 1.5, 6.5])
                    
                    if col_b1.form_submit_button("💾 Guardar Cambios"):
                        datos_upd = {
                            "ingreso_garantizado": e_renta,
                            "valor_fianza": e_fianza,
                            "tipo_actualizacion": e_act,
                            "cuenta_pago": e_cta1.strip(),
                            "cuenta_pago_2": e_cta2.strip()
                        }
                        supabase.table("mandatos").update(datos_upd).eq("id", int(id_m)).execute()
                        
                        # Guardar historial
                        supabase.table("historial_mandatos").insert({
                            "id_mandato": int(id_m), 
                            "accion": f"CONDICIONES ACTUALIZADAS: Renta {e_renta}, Fianza {e_fianza}, Act: {e_act}",
                            "usuario": usuario_actual
                        }).execute()
                        log_accion(supabase, usuario_actual, "EDITAR MANDATO", m_sel_edit)
                        
                        st.success("✅ Contrato actualizado correctamente.")
                        st.session_state.modo_mandato = "NADA"
                        time.sleep(1)
                        st.rerun()
                        
                    if col_b2.form_submit_button("❌ Cerrar"):
                        st.session_state.modo_mandato = "NADA"
                        st.rerun()

                # --- ZONA DE PELIGRO (Fuera del form para evitar clicks accidentales) ---
                st.write("")
                st.error("🚨 Zona de Peligro: Finalización de Contrato")
                c_del1, c_del2 = st.columns([7, 3])
                confirmar_fin = c_del1.checkbox("⚠️ Confirmo que deseo FINALIZAR este contrato (Pasará a histórico y no generará más pagos).", key=f"chk_fin_{id_m}")
                
                if c_del2.button("🛑 Finalizar Contrato", disabled=not confirmar_fin, use_container_width=True):
                    # Actualizamos el estado a FINALIZADO
                    supabase.table("mandatos").update({"estado_contrato": "FINALIZADO"}).eq("id", int(id_m)).execute()
                    
                    supabase.table("historial_mandatos").insert({
                        "id_mandato": int(id_m), "accion": "CONTRATO FINALIZADO POR EL USUARIO", "usuario": usuario_actual
                    }).execute()
                    log_accion(supabase, usuario_actual, "FINALIZAR MANDATO", m_sel_edit)
                    
                    st.success("✅ El contrato ha sido finalizado y archivado.")
                    st.session_state.modo_mandato = "NADA"
                    time.sleep(1.5)
                    st.rerun()

        # --- 6.1 PANELES  REPORTES ---
        elif st.session_state.modo_mandato == "REPORTES" and not df_man.empty:
            st.markdown("---")
            st.markdown("## Centro de Reportes de Mandatos")

            # 💡 CAMBIO A SELECTBOX (Más elegante y escalable)
            tipo_rep = st.selectbox("Elige el tipo de reporte:", [
                "Ficha Detallada (Un Contrato)", 
                "Historial de Auditoría (Un Contrato)",
                "Directorio Global (Todos los Contratos)"
            ])

            if tipo_rep == "Directorio Global (Todos los Contratos)":
                try:
                    res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
                    df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
                except: df_ops = pd.DataFrame()

                df_rep = df_view_display.copy()
                if 'DOCS' in df_rep.columns: df_rep = df_rep.drop(columns=['DOCS'])

                panel_reportes_y_compartir(
                    df_datos=df_rep,
                    nombre_base="directorio_mandatos_activos",
                    modulo_origen="Mandatos",
                    funcion_pdf=generar_pdf_mandatos,
                    df_operadores=df_ops,
                    supabase=supabase,
                    usuario_actual=usuario_actual,
                    clave_estado_cerrar="modo_mandato"
                )

            elif tipo_rep == "Ficha Detallada (Un Contrato)":
                op_man_rep = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
                m_sel_rep = st.selectbox("Selecciona el Mandato a exportar:", op_man_rep)

                if m_sel_rep:
                    idx = op_man_rep.index(m_sel_rep)
                    d_m = df_man.iloc[idx]
                    d_v = df_view_display.iloc[idx]

                    datos_ficha = {
                        'inmueble': d_v['INMUEBLE'], 'propietario_1': d_v['TITULAR'],
                        'porc_prop_1': d_m.get('porcentaje_propiedad', 0), 'porc_pago_1': d_m.get('porcentaje_pago_1', 0),
                        'iban_1': d_m.get('cuenta_pago', ''), 'porc_prop_2': d_m.get('porcentaje_propiedad_2', 0),
                        'porc_pago_2': d_m.get('porcentaje_pago_2', 0), 'iban_2': d_m.get('cuenta_pago_2', ''),
                        'f_suscripcion': d_m.get('fecha_suscripcion', ''), 'f_entrega': d_m.get('fecha_entrega', ''),
                        'f_pagos': d_m.get('fecha_inicio_pagos', ''), 'f_vence': d_m.get('fecha_terminacion', ''),
                        'f_aviso': d_m.get('fecha_aviso_no_renovacion', ''), 'renta': d_m.get('ingreso_garantizado', 0),
                        'actualizacion': d_m.get('tipo_actualizacion', ''), 'fianza': d_m.get('valor_fianza', 0),
                        'tipo_ind': d_m.get('tipo_indemnizacion', ''), 'monto_ind': d_m.get('indemnizacion_anticipada', 0),
                        'estado_fin': d_m.get('estado_financiero', ''), 'url_c': d_m.get('url_contrato', ''),
                        'url_e': d_m.get('url_empadronamiento', ''), 'url_i': d_m.get('url_inventario', ''),
                        'url_s': d_m.get('url_suministros', '')
                    }

                    df_ficha_unica = pd.DataFrame([datos_ficha])

                    try:
                        res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
                        df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
                    except: df_ops = pd.DataFrame()

                    panel_reportes_y_compartir(
                        df_datos=df_ficha_unica,
                        nombre_base=f"Ficha_Mandato_{d_v['INMUEBLE'].replace(' ', '_')}",
                        modulo_origen="Ficha de Mandato",
                        funcion_pdf=generar_pdf_ficha_mandato,
                        df_operadores=df_ops,
                        supabase=supabase,
                        usuario_actual=usuario_actual,
                        clave_estado_cerrar="modo_mandato"
                    )

            elif tipo_rep == "Historial de Auditoría (Un Contrato)":
                op_man_aud = df_view_display.apply(lambda r: f"{r['INMUEBLE']} - {r['TITULAR']}", axis=1).tolist()
                m_sel_aud = st.selectbox("Selecciona el Mandato para auditar:", op_man_aud)

                if m_sel_aud:
                    idx = op_man_aud.index(m_sel_aud)
                    id_m = df_man.iloc[idx]['id']
                    
                    try:
                        res_hist = supabase.table("historial_mandatos").select("fecha_evento, accion, usuario").eq("id_mandato", int(id_m)).order("fecha_evento", desc=True).execute()
                        df_h = pd.DataFrame(res_hist.data) if res_hist.data else pd.DataFrame()
                    except Exception as e:
                        df_h = pd.DataFrame()

                    if not df_h.empty:
                        df_h['FECHA'] = pd.to_datetime(df_h['fecha_evento']).dt.strftime('%d/%m/%Y %H:%M')
                        df_h_rep = df_h[['FECHA', 'accion', 'usuario']].copy()
                        df_h_rep.rename(columns={'accion': 'ACCION REGISTRADA', 'usuario': 'USUARIO'}, inplace=True)

                        try:
                            res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
                            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
                        except: df_ops = pd.DataFrame()

                        panel_reportes_y_compartir(
                            df_datos=df_h_rep,
                            nombre_base=f"Auditoria_Mandato_{id_m}",
                            modulo_origen="Historial Mandato",
                            funcion_pdf=generar_pdf_historial_mandato,
                            df_operadores=df_ops,
                            supabase=supabase,
                            usuario_actual=usuario_actual,
                            clave_estado_cerrar="modo_mandato"
                        )
                    else:
                        st.info("ℹ️ No hay registros de auditoría para este contrato todavía.")

            st.markdown("---")
            if st.button("❌ Cerrar Panel"): st.session_state.modo_mandato = "NADA"; st.rerun()

    # ==========================================
    # TAB 4: INVENTARIOS (Mobiliario)
    # ==========================================
    with tab4:
        st.subheader("Control de Bienes y Mobiliario")
        st.info("💡 Control de activos. Si dejas la 'Unidad' en blanco, el sistema sabrá que pertenece a las Zonas Comunes del edificio.")
        st.button("➕ Simular Botón: Registrar Mobiliario", disabled=True)