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
    MOD_VERSION = "v1.0 (Esqueleto)"
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
            df_display = df_inm[['id', 'nombre', 'tipo', 'ciudad', 'moneda', 'referencia_catastral']].copy()
            df_display.rename(columns={'nombre': 'NOMBRE', 'tipo': 'TIPO', 'ciudad': 'CIUDAD', 'moneda': 'MONEDA', 'referencia_catastral': label_catastro.upper()}, inplace=True)
            st.dataframe(df_display.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
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
            
            if prop_maestra != "-- Seleccione --":
                # Extraemos la moneda dinámicamente
                prop_data = df_prop[df_prop['nombre'] == prop_maestra].iloc[0]
                id_prop_maestra = prop_data['id']
                moneda_prop = prop_data.get('moneda', 'EUR') 
                simbolo_mon = "€" if moneda_prop == "EUR" else "$"
                
                res_uni = supabase.table("unidades").select("*").eq("estado", "ACTIVO").eq("id_inmueble", int(id_prop_maestra)).execute()
                df_uni = pd.DataFrame(res_uni.data) if res_uni.data else pd.DataFrame()
                
                               
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
                            # --- FILA DE ACCIONES COMPACTA (AJUSTE PERFECTO) ---
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
    # TAB 3: MANDATOS (Dueños y Porcentajes)
    # ========================================
    with tab3:
        st.subheader("Distribución de Propiedad (Relación N:M)")
        st.info("💡 Aquí usaremos la tabla puente 'inmuebles_propietarios' para definir qué % de la renta le toca a cada dueño y a qué cuenta se paga.")
        st.button("➕ Simular Botón: Asignar Propietario a Inmueble", disabled=True)

    # ==========================================
    # TAB 4: INVENTARIOS (Mobiliario)
    # ==========================================
    with tab4:
        st.subheader("Control de Bienes y Mobiliario")
        st.info("💡 Control de activos. Si dejas la 'Unidad' en blanco, el sistema sabrá que pertenece a las Zonas Comunes del edificio.")
        st.button("➕ Simular Botón: Registrar Mobiliario", disabled=True)