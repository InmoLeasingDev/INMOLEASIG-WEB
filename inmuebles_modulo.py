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

    # =========================================
    # TAB 3: MANDATOS (Dueños y Porcentajes)
    # =========================================
# ========================================
    # TAB 3: MANDATOS (Contratos y Finanzas)
    # ========================================
    with tab3:
        if 'modo_mandato' not in st.session_state:
            st.session_state.modo_mandato = "NADA"

        st.markdown("### 🤝 Contratos de Gestión Integral")

        # --- 1. Carga de Datos Base ---
        try:
            # Traemos inmuebles y propietarios para los selectores
            res_inm = supabase.table("inmuebles").select("id, nombre, moneda").eq("estado", "ACTIVO").execute()
            df_inm_m = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
            
            res_prop = supabase.table("propietarios").select("id, nombre, cuenta_banco").eq("estado", "ACTIVO").execute()
            df_prop_m = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
            
            # Traemos los mandatos activos (Cruzando IDs con nombres para la Grid)
            res_man = supabase.table("mandatos").select("*").neq("estado_contrato", "FINALIZADO").execute()
            df_man = pd.DataFrame(res_man.data) if res_man.data else pd.DataFrame()
        except Exception as e:
            # Si las tablas aún no existen en Supabase, evitamos que la app colapse
            df_inm_m, df_prop_m, df_man = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            st.warning("⚠️ Asegúrate de haber creado las tablas 'mandatos', 'historial_mandatos' y 'pagos_mandatos' en Supabase.")

        # --- 2. GRID DE MANDATOS (LECTURA) ---
        if not df_man.empty and not df_inm_m.empty and not df_prop_m.empty:
            # Hacemos un "Merge" (cruce) para mostrar nombres en vez de números de ID
            df_view = df_man.merge(df_inm_m[['id', 'nombre']], left_on='id_inmueble', right_on='id', how='left')
            df_view = df_view.merge(df_prop_m[['id', 'nombre']], left_on='id_propietario', right_on='id', how='left', suffixes=('_inm', '_prop'))
            
            df_view_display = df_view[['nombre_inm', 'nombre_prop', 'porcentaje_propiedad', 'ingreso_garantizado', 'estado_contrato', 'estado_financiero']].copy()
            df_view_display.rename(columns={
                'nombre_inm': 'INMUEBLE', 'nombre_prop': 'PROPIETARIO', 
                'porcentaje_propiedad': '% PROP.', 'ingreso_garantizado': 'ALQUILER GARANT.',
                'estado_contrato': 'ESTADO LEGAL', 'estado_financiero': 'ESTADO FINANZAS'
            }, inplace=True)
            
            st.dataframe(df_view_display, use_container_width=True, hide_index=True)
        else:
            #st.session_state.modo_mandato = "NADA" # Escudo anti-crash
            st.info("ℹ️ No hay mandatos vigentes. Crea uno nuevo para empezar a gestionar contratos.")

        # --- 3. BARRA DE HERRAMIENTAS MODO PRO ---
        st.markdown("---")
        m_c1, m_c2, m_c3, m_c4, m_esp = st.columns([1.5, 1.5, 2.0, 1.5, 3.5])
        if m_c1.button("➕ Nuevo", key="btn_nuevo_man", use_container_width=True):
            st.session_state.modo_mandato = "CREAR"
            st.rerun()
            
        if not df_man.empty:
            if m_c2.button("⚙️ Gestionar", key="btn_edit_man", use_container_width=True):
                st.session_state.modo_mandato = "EDITAR"
                st.rerun()
            if m_c3.button("💰 Pagos & Soportes", key="btn_pagos_man", use_container_width=True):
                st.session_state.modo_mandato = "PAGOS"
                st.rerun()
            if m_c4.button("📊 Reportes", key="btn_rep_man", use_container_width=True):
                st.session_state.modo_mandato = "REPORTES"
                st.rerun()

        # --- 4. PANELES DINÁMICOS ---
        
        # ==========================================
        # PANEL: CREAR MANDATO (DISEÑO VERTICAL)
        # ==========================================
        if st.session_state.modo_mandato == "CREAR":
            st.markdown("---")
            if df_inm_m.empty or df_prop_m.empty:
                st.error("❌ Necesitas al menos un Inmueble y un Propietario registrados para crear un mandato.")
                if st.button("❌ Cerrar Panel"):
                    st.session_state.modo_mandato = "NADA"
                    st.rerun()
            else:
                with st.form("form_nuevo_mandato", clear_on_submit=False):
                    st.markdown("### 📝 Redactar Nuevo Contrato de Gestión")
                    st.info("💡 Completa todas las secciones desplazándote hacia abajo antes de guardar.")
                    
                    # --- SECCIÓN 1: FINANZAS ---
                    st.markdown("#### 💼 1. Vínculo y Finanzas")
                    c1, c2, c3 = st.columns([2, 2, 1])
                    m_inm_sel = c1.selectbox("Inmueble *", df_inm_m['nombre'].tolist())
                    
                    # Ayuda visual para múltiples dueños
                    m_prop_sel = c2.selectbox("Propietario / Representante *", df_prop_m['nombre'].tolist(), 
                                              help="Si son varios dueños, crea un perfil conjunto en Propietarios (Ej: 'Angel y Antonio') o elige al representante.")
                    m_porcentaje = c3.number_input("% Propiedad", min_value=1.0, max_value=100.0, value=100.0)
                    
                    st.markdown("**Acuerdo Económico**")
                    c4, c5, c6 = st.columns(3)
                    m_alquiler = c4.number_input("Ingreso Mensual Garantizado *", min_value=0.0, step=50.0)
                    m_fianza = c5.number_input("Fianza a Entregar *", min_value=0.0, step=50.0)
                    
                    # Campo explícito para la cuenta conjunta
                    m_iban = c6.text_input("IBAN / Cuenta de Pago *", 
                                           placeholder="Ej: ES25 2100...", 
                                           help="Coloca aquí la cuenta bancaria conjunta a la que se transferirá.")
                    
                    st.markdown("**Actualización Anual**")
                    c7, c8, c9 = st.columns(3)
                    m_tipo_act = c7.selectbox("Método de Actualización", ["IPC", "FIJO", "NO APLICA"])
                    m_porc_act = c8.number_input("% Fijo (Si aplica)", min_value=0.0, step=0.1)
                    
                    st.markdown("---")
                    
                    # --- SECCIÓN 2: CRONOGRAMA ---
                    st.markdown("#### 📅 2. Cronograma del Contrato")
                    cc1, cc2 = st.columns(2)
                    m_f_suscripcion = cc1.date_input("Fecha de Suscripción (Firma)")
                    m_f_entrega = cc2.date_input("Fecha de Entrega / Recibo (Llaves)")
                    
                    cc3, cc4 = st.columns(2)
                    m_f_fin_carencia = cc3.date_input("Fecha Fin de Carencia")
                    m_f_inicio_pago = cc4.date_input("Fecha Inicio de Pagos")
                    
                    cc5, cc6 = st.columns(2)
                    m_f_terminacion = cc5.date_input("Fecha de Terminación (Vencimiento)")
                    m_f_aviso = cc6.date_input("Fecha Límite Aviso No Renovación")
                    
                    st.markdown("---")
                    
                    # --- SECCIÓN 3: DOCUMENTOS ---
                    st.markdown("#### 📁 3. Documentos Básicos")
                    st.write("Sube los documentos escaneados (Max 5MB c/u. PDF o Imagen).")
                    cd1, cd2 = st.columns(2)
                    doc_contrato = cd1.file_uploader("Contrato Firmado", type=["pdf", "jpg", "png"], key="doc_cont")
                    doc_empadrona = cd2.file_uploader("Autorización Empadronamiento", type=["pdf", "jpg", "png"], key="doc_emp")
                    
                    cd3, cd4 = st.columns(2)
                    doc_inventario = cd3.file_uploader("Acta de Inventario", type=["pdf", "jpg", "png"], key="doc_inv")
                    doc_suministros = cd4.file_uploader("Recibos Suministros (Agua/Luz)", type=["pdf", "jpg", "png"], key="doc_sum")
                        
                    st.markdown("---")
                    col_b1, col_b2, col_esp = st.columns([2.0, 1.5, 6.5])
                    
                    if col_b1.form_submit_button("💾 Generar Mandato"):
                        with st.spinner("Creando mandato y subiendo documentos a la bóveda..."):
                            try:
                                id_inm = df_inm_m[df_inm_m['nombre'] == m_inm_sel].iloc[0]['id']
                                id_prop = df_prop_m[df_prop_m['nombre'] == m_prop_sel].iloc[0]['id']
                                
                                def subir_pdf(archivo_st, prefijo_nombre):
                                    if archivo_st is None: return None
                                    ext = archivo_st.name.split('.')[-1].lower()
                                    tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                    nombre_nube = f"{prefijo_nombre}_{id_inm}_{id_prop}_{int(time.time())}.{ext}"
                                    supabase.storage.from_("documentos_mandatos").upload(
                                        path=nombre_nube, file=archivo_st.getvalue(), file_options={"content-type": tipo_mime}
                                    )
                                    return supabase.storage.from_("documentos_mandatos").get_public_url(nombre_nube)

                                url_c = subir_pdf(doc_contrato, "contrato")
                                url_e = subir_pdf(doc_empadrona, "empadronamiento")
                                url_i = subir_pdf(doc_inventario, "inventario")
                                url_s = subir_pdf(doc_suministros, "suministros")

                                datos_mandato = {
                                    "id_inmueble": int(id_inm), "id_propietario": int(id_prop),
                                    "porcentaje_propiedad": m_porcentaje, "ingreso_garantizado": m_alquiler,
                                    "valor_fianza": m_fianza, "cuenta_pago": m_iban.strip() if m_iban else None,
                                    "tipo_actualizacion": m_tipo_act, "porcentaje_actualizacion": m_porc_act,
                                    "fecha_suscripcion": str(m_f_suscripcion), "fecha_entrega": str(m_f_entrega),
                                    "fecha_fin_carencia": str(m_f_fin_carencia), "fecha_inicio_pagos": str(m_f_inicio_pago),
                                    "fecha_terminacion": str(m_f_terminacion), "fecha_aviso_no_renovacion": str(m_f_aviso),
                                    "url_contrato": url_c, "url_empadronamiento": url_e,
                                    "url_inventario": url_i, "url_suministros": url_s,
                                    "estado_contrato": "FIRMADO", "estado_financiero": "PENDIENTE_FIANZA"
                                }

                                res_insert = supabase.table("mandatos").insert(datos_mandato).execute()
                                id_nuevo_mandato = res_insert.data[0]['id']

                                supabase.table("historial_mandatos").insert({
                                    "id_mandato": id_nuevo_mandato,
                                    "accion": "CREACIÓN DE MANDATO Y FIRMA DE CONTRATO",
                                    "usuario": usuario_actual
                                }).execute()

                                log_accion(supabase, usuario_actual, "NUEVO MANDATO", f"{m_inm_sel} - {m_prop_sel}")
                                st.success("✅ Mandato generado, documentos encriptados y fechas programadas.")
                                st.session_state.modo_mandato = "NADA"
                                time.sleep(1.5)
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Ocurrió un error en la transacción: {e}")
                                
                    if col_b2.form_submit_button("❌ Cancelar"):
                        st.session_state.modo_mandato = "NADA"
                        st.rerun()

        # ==========================================
        # PANEL: GESTIONAR (Placeholder para edición)
        # ==========================================
        elif st.session_state.modo_mandato == "EDITAR":
            st.markdown("---")
            st.info("⚙️ Módulo de edición de mandatos en construcción. Aquí cambiaremos estados y renovaremos contratos.")
            if st.button("❌ Cerrar"):
                st.session_state.modo_mandato = "NADA"
                st.rerun()
                
        # ==========================================
        # PANEL: PAGOS Y SOPORTES 
        # ==========================================
        elif st.session_state.modo_mandato == "PAGOS" and not df_man.empty:
            st.markdown("---")
            st.markdown("### 💰 Gestión de Pagos y Soportes Bancarios")
            
            # 1. Selector del Contrato
            opciones_man = df_view_display.apply(lambda row: f"{row['INMUEBLE']} - {row['PROPIETARIO']}", axis=1).tolist()
            man_sel = st.selectbox("Selecciona el Mandato a pagar:", opciones_man)
            
            if man_sel:
                idx = opciones_man.index(man_sel)
                id_man_real = df_man.iloc[idx]['id']
                datos_m = df_man.iloc[idx]
                
                st.info(f"**Acuerdo Actual:** Alquiler Garantizado: **{datos_m['ingreso_garantizado']}** | Fianza: **{datos_m['valor_fianza']}** | Estado Financiero: **{datos_m['estado_financiero']}**")
                
                c_form, c_hist = st.columns([1.2, 1])
                
                # --- COLUMNA IZQ: REGISTRAR NUEVO PAGO ---
                with c_form:
                    with st.form(f"form_pago_{id_man_real}", clear_on_submit=True):
                        st.subheader("📤 Registrar Nuevo Pago")
                        
                        sug_concepto = "PAGO FIANZA" if datos_m['estado_financiero'] == "PENDIENTE_FIANZA" else f"ALQUILER {datetime.now().strftime('%B %Y').upper()}"
                        sug_monto = float(datos_m['valor_fianza']) if datos_m['estado_financiero'] == "PENDIENTE_FIANZA" else float(datos_m['ingreso_garantizado'])
                        
                        p_concepto = st.text_input("Concepto de Pago *", value=sug_concepto)
                        
                        c_monto, c_fecha = st.columns(2)
                        p_monto = c_monto.number_input("Monto Transferido *", min_value=0.0, step=50.0, value=sug_monto)
                        p_fecha = c_fecha.date_input("Fecha de Transferencia")
                        
                        p_soporte = st.file_uploader("Adjuntar Soporte del Banco (PDF/IMG)", type=["pdf", "jpg", "png"])
                        
                        st.markdown("---")
                        if st.form_submit_button("💾 Guardar y Subir Soporte"):
                            if p_concepto and p_monto > 0:
                                with st.spinner("Procesando transacción en la nube..."):
                                    try:
                                        url_sop = None
                                        if p_soporte:
                                            ext = p_soporte.name.split('.')[-1].lower()
                                            tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                            nombre_nube = f"soporte_{id_man_real}_{int(time.time())}.{ext}"
                                            
                                            supabase.storage.from_("soportes_pagos").upload(
                                                path=nombre_nube, file=p_soporte.getvalue(), file_options={"content-type": tipo_mime}
                                            )
                                            url_sop = supabase.storage.from_("soportes_pagos").get_public_url(nombre_nube)
                                            
                                        # Insertar pago
                                        supabase.table("pagos_mandatos").insert({
                                            "id_mandato": int(id_man_real), "concepto": p_concepto.strip().upper(),
                                            "monto": p_monto, "fecha_pago": str(p_fecha),
                                            "url_soporte_bancario": url_sop, "estado_envio": "PENDIENTE"
                                        }).execute()
                                        
                                        # Cambiar estado del contrato
                                        supabase.table("mandatos").update({"estado_financiero": "AL_DIA"}).eq("id", int(id_man_real)).execute()
                                        
                                        # Guardar huella en historial
                                        supabase.table("historial_mandatos").insert({
                                            "id_mandato": int(id_man_real), "accion": f"REGISTRO PAGO: {p_concepto.strip().upper()} ({p_monto})",
                                            "usuario": usuario_actual
                                        }).execute()
                                        
                                        st.success("✅ Transferencia registrada exitosamente.")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error en la transacción: {e}")
                            else:
                                st.warning("⚠️ Debes ingresar un Concepto y un Monto mayor a 0.")

                # --- COLUMNA DER: HISTORIAL BANCARIO ---
                with c_hist:
                    st.subheader("📚 Historial del Contrato")
                    try:
                        res_pagos = supabase.table("pagos_mandatos").select("*").eq("id_mandato", int(id_man_real)).order("fecha_pago", desc=True).execute()
                        df_pagos = pd.DataFrame(res_pagos.data) if res_pagos.data else pd.DataFrame()
                    except:
                        df_pagos = pd.DataFrame()
                        
                    if not df_pagos.empty:
                        for _, pg in df_pagos.iterrows():
                            with st.expander(f"✅ {pg['fecha_pago']} - {pg['concepto']} ({pg['monto']})"):
                                st.write(f"**Estado de envío:** {pg['estado_envio']}")
                                c_btn_1, c_btn_2 = st.columns(2)
                                if pg['url_soporte_bancario']:
                                    c_btn_1.markdown(f"**[🔍 Ver PDF del Banco]({pg['url_soporte_bancario']})**")
                                else:
                                    c_btn_1.info("Sin soporte adjunto.")
                                    
                                if c_btn_2.button("📲 Compartir", key=f"btn_comp_{pg['id']}", use_container_width=True):
                                    st.toast("Módulo de envío a propietario en construcción 🚧", icon="⏳")
                    else:
                        st.info("Aún no se han registrado pagos para este contrato.")
                        
            st.markdown("---")
            if st.button("❌ Cerrar Panel", key="btn_cerrar_pagos"):
                st.session_state.modo_mandato = "NADA"
                st.rerun()

        # ==========================================
        # PANEL: REPORTES (Placeholder)
        # ==========================================
        elif st.session_state.modo_mandato == "REPORTES":
            st.markdown("---")
            st.info("📊 Módulo de Reportes de Mandatos en construcción.")
            if st.button("❌ Cerrar"):
                st.session_state.modo_mandato = "NADA"
                st.rerun()
    # ==========================================
    # TAB 4: INVENTARIOS (Mobiliario)
    # ==========================================
    with tab4:
        st.subheader("Control de Bienes y Mobiliario")
        st.info("💡 Control de activos. Si dejas la 'Unidad' en blanco, el sistema sabrá que pertenece a las Zonas Comunes del edificio.")
        st.button("➕ Simular Botón: Registrar Mobiliario", disabled=True)