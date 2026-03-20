import streamlit as st
import pandas as pd
import time
import urllib.parse
import re
from fpdf import FPDF
# --- NUESTRA LIBRERÍA MAESTRA ---
from herramientas import log_accion, enviar_reporte_correo, generar_excel_bytes

# ==========================================
# 1. MOTOR PDF PROPIEDADES
# ==========================================
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
# 2. MOTOR PDF UNIDADES
# ==========================================
def generar_pdf_unidades(df):
    pdf = FPDF() # Vertical
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "INMOLEASING - DIRECTORIO DE UNIDADES", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    cw = [80, 60, 50]
    headers = ["PROPIEDAD", "UNIDAD", "TIPO"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        textos = [str(row.get('PROPIEDAD', '')), str(row.get('UNIDAD', '')), str(row.get('TIPO', ''))]
        textos = [t.encode('latin-1', 'ignore').decode('latin-1') for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > 270: pdf.add_page()
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
        st.subheader("Catálogo de Propiedades Base")
        st.info("💡 Aquí gestionamos los inmuebles principales (Ej: Piso 2B, Oficina 1202, Local S02).")
        
        # Lógica dinámica de región
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

        # --- FORMULARIO NUEVA PROPIEDAD ---
        with st.expander("➕ Añadir Nueva Propiedad", expanded=False):
            with st.form("form_nueva_propiedad"):
                st.write("Datos Generales del Inmueble")
                c1, c2 = st.columns(2)
                n_nom = c1.text_input("Nombre / Dirección Principal *", placeholder="Ej: Piso 2B Calle Mayor")
                n_tip = c2.selectbox("Tipo de Propiedad *", opciones_tipo)
                
                c3, c4, c5 = st.columns(3)
                n_ciu = c3.text_input("Ciudad *")
                n_mon = c4.selectbox("Región / Moneda *", opciones_moneda)
                n_cat = c5.text_input(label_catastro)
                
                st.write("Datos del Seguro (Opcional)")
                c6, c7, c8 = st.columns(3)
                n_ase = c6.text_input("Aseguradora")
                n_pol = c7.text_input("Número de Póliza")
                n_tel_ase = c8.text_input("Teléfono Aseguradora")
                
                if st.form_submit_button("💾 Guardar Propiedad"):
                    if n_nom and n_ciu:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(), "tipo": n_tip, "ciudad": n_ciu.strip().upper(),
                            "moneda": n_mon, "referencia_catastral": n_cat.strip().upper(),
                            "aseguradora": n_ase.strip().upper(), "numero_poliza": n_pol.strip().upper(), 
                            "telefono_aseguradora": n_tel_ase.strip(), "estado": "ACTIVO"
                        }
                        supabase.table("inmuebles").insert(datos_insert).execute()
                        log_accion(supabase, usuario_actual, "CREAR PROPIEDAD", n_nom.strip().upper())
                        st.success("✅ Propiedad registrada con éxito.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ Los campos con asterisco (*) son obligatorios.")

        # --- LECTURA DE DATOS (READ) ---
        query = supabase.table("inmuebles").select("*").eq("estado", "ACTIVO")
        if moneda_sesion != "ALL": query = query.eq("moneda", moneda_sesion)
            
        res_inm = query.execute()
        df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
        
        if not df_inm.empty:
            df_inm = df_inm.sort_values(by=['moneda', 'nombre'], ascending=[True, True])
            
            df_display = df_inm[['id', 'nombre', 'tipo', 'ciudad', 'moneda', 'referencia_catastral']].copy()
            df_display.rename(columns={'nombre': 'NOMBRE', 'tipo': 'TIPO', 'ciudad': 'CIUDAD', 'moneda': 'MONEDA', 'referencia_catastral': label_catastro.upper()}, inplace=True)
            st.dataframe(df_display.drop(columns=['id']), use_container_width=True, hide_index=True)
            
            # --- GESTIONAR PROPIEDAD ---
            with st.expander("⚙️ Gestionar / Editar Propiedad", expanded=False):
                prop_sel = st.selectbox("Seleccione la propiedad a editar:", df_display['NOMBRE'].tolist())
                if prop_sel:
                    datos_p = df_inm[df_inm['nombre'] == prop_sel].iloc[0]
                    with st.form("form_editar_prop"):
                        st.write("Actualizar Datos")
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
                        
                        if st.form_submit_button("📝 Guardar Cambios"):
                            datos_upd = {
                                "nombre": e_nom.strip().upper(), "ciudad": e_ciu.strip().upper(),
                                "moneda": e_mon, "referencia_catastral": e_cat.strip().upper(),
                                "aseguradora": e_ase.strip().upper(), "numero_poliza": e_pol.strip().upper()
                            }
                            supabase.table("inmuebles").update(datos_upd).eq("id", int(datos_p['id'])).execute()
                            log_accion(supabase, usuario_actual, "EDITAR PROPIEDAD", e_nom.strip().upper())
                            st.success("✅ Actualizado correctamente.")
                            time.sleep(1)
                            st.rerun()
                            
                    if st.button("🚫 Dar de Baja (Eliminar)"):
                        supabase.table("inmuebles").update({"estado": "INACTIVO"}).eq("id", int(datos_p['id'])).execute()
                        log_accion(supabase, usuario_actual, "ELIMINAR PROPIEDAD", datos_p['nombre'])
                        st.success("✅ Propiedad dada de baja.")
                        time.sleep(1)
                        st.rerun()

            # --- EXPORTAR ---
            st.markdown("---")
            st.markdown("### 📄 Exportar Listado")
            formato_archivo = st.radio("Formato de Exportación:", ["PDF", "Excel"], horizontal=True, key="radio_form_inm")
            if formato_archivo == "PDF":
                archivo_bytes = generar_pdf_propiedades(df_display) # Usa tu misma función de arriba
                ext, mime = "pdf", "application/pdf"
            else:
                archivo_bytes = generar_excel_bytes(df_display.drop(columns=['id']), "Propiedades")
                ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            st.download_button(f"⬇️ Descargar en {formato_archivo}", data=archivo_bytes, file_name=f"directorio_propiedades.{ext}", mime=mime, use_container_width=True)

        else:
            st.info("ℹ️ Aún no hay propiedades registradas o activas en tu región.")

    # ==========================================
    # TAB 2: UNIDADES (Subdivisión de Propiedades)
    # ==========================================
    with tab2:
        st.subheader("Subdivisión de Espacios Rentables")
        st.info("💡 Aquí dividimos la propiedad (Ej: Piso 2B) en las unidades que vamos a alquilar (Ej: Habitación 1, Suite 3). Si se alquila completo, ponle el mismo nombre del local.")
        
        # --- Cargar Operadores para los envíos ---
        try:
            res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()

        # 1. Traer los inmuebles activos
        query_inm = supabase.table("inmuebles").select("id, nombre").eq("estado", "ACTIVO")
        moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
        if moneda_sesion != "ALL": query_inm = query_inm.eq("moneda", moneda_sesion)
        res_prop = query_inm.order("nombre").execute()
        df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        
        if df_prop.empty:
            st.warning("⚠️ Primero debes crear una Propiedad Base (Tab 1).")
        else:
            dict_prop = dict(zip(df_prop['id'], df_prop['nombre']))
            opciones_prop = ["-- Seleccione --"] + df_prop['nombre'].tolist()
            
            # --- 1. FORMULARIO NUEVA UNIDAD (CREATE) ---
            with st.expander("➕ Añadir Nueva Unidad", expanded=False):
                with st.form("form_nueva_unidad"):
                    c1, c2, c3 = st.columns(3)
                    u_prop = c1.selectbox("Pertenece a la Propiedad *", opciones_prop)
                    u_nom = c2.text_input("Nombre de la Unidad *", placeholder="Ej: Habitación 1, PH 2, S02")
                    u_tip = c3.selectbox("Tipo *", ["HABITACIÓN", "SUITE", "OFICINA", "PROPIEDAD COMPLETA", "PARQUEADERO", "OTRO"])
                    
                    if st.form_submit_button("💾 Guardar Unidad"):
                        if u_prop != "-- Seleccione --" and u_nom:
                            id_inmueble_sel = df_prop[df_prop['nombre'] == u_prop]['id'].values[0]
                            datos_u = {
                                "id_inmueble": int(id_inmueble_sel), "nombre": u_nom.strip().upper(),
                                "tipo": u_tip, "estado": "ACTIVO"
                            }
                            supabase.table("unidades").insert(datos_u).execute()
                            log_accion(supabase, usuario_actual, "CREAR UNIDAD", f"{u_nom.upper()} en {u_prop}")
                            st.success("✅ Unidad registrada con éxito.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ Debes seleccionar una propiedad y darle un nombre a la unidad.")
            
            st.markdown("---")
            
            # --- 2. LECTURA DE DATOS (READ) ---
            res_uni = supabase.table("unidades").select("id, id_inmueble, nombre, tipo").eq("estado", "ACTIVO").execute()
            df_uni = pd.DataFrame(res_uni.data) if res_uni.data else pd.DataFrame()
            
            if not df_uni.empty:
                df_uni = df_uni[df_uni['id_inmueble'].isin(df_prop['id'])].copy()
                if not df_uni.empty:
                    df_uni['PROPIEDAD'] = df_uni['id_inmueble'].map(dict_prop)
                    df_uni['selector'] = df_uni['PROPIEDAD'] + " - " + df_uni['nombre']
                    
                    df_uni_display = df_uni[['PROPIEDAD', 'nombre', 'tipo']].copy()
                    df_uni_display.rename(columns={'nombre': 'UNIDAD', 'tipo': 'TIPO'}, inplace=True)
                    df_uni_display = df_uni_display.sort_values(by=['PROPIEDAD', 'UNIDAD'])
                    
                    st.dataframe(df_uni_display, use_container_width=True, hide_index=True)
                    
                    # --- 3. GESTIONAR UNIDAD (UPDATE / DELETE) ---
                    with st.expander("⚙️ Gestionar / Editar Unidad", expanded=False):
                        uni_sel = st.selectbox("Seleccione la unidad a editar:", df_uni['selector'].sort_values().tolist())
                        if uni_sel:
                            datos_u_edit = df_uni[df_uni['selector'] == uni_sel].iloc[0]
                            with st.form("form_editar_uni"):
                                st.write(f"Actualizando: **{datos_u_edit['PROPIEDAD']}**")
                                e_c1, e_c2 = st.columns(2)
                                e_nom = e_c1.text_input("Nombre de la Unidad", datos_u_edit['nombre'])
                                lista_tipos = ["HABITACIÓN", "SUITE", "OFICINA", "PROPIEDAD COMPLETA", "PARQUEADERO", "OTRO"]
                                idx_tip = lista_tipos.index(datos_u_edit['tipo']) if datos_u_edit['tipo'] in lista_tipos else 0
                                e_tip = e_c2.selectbox("Tipo", lista_tipos, index=idx_tip)
                                
                                col_btn1, col_btn2 = st.columns(2)
                                if col_btn1.form_submit_button("📝 Guardar Cambios"):
                                    datos_upd = {"nombre": e_nom.strip().upper(), "tipo": e_tip}
                                    supabase.table("unidades").update(datos_upd).eq("id", int(datos_u_edit['id'])).execute()
                                    log_accion(supabase, usuario_actual, "EDITAR UNIDAD", e_nom.strip().upper())
                                    st.success("✅ Actualizado correctamente.")
                                    time.sleep(1)
                                    st.rerun()
                                    
                            if st.button("🚫 Dar de Baja (Eliminar) Unidad"):
                                supabase.table("unidades").update({"estado": "INACTIVO"}).eq("id", int(datos_u_edit['id'])).execute()
                                log_accion(supabase, usuario_actual, "ELIMINAR UNIDAD", datos_u_edit['nombre'])
                                st.success("✅ Unidad dada de baja.")
                                time.sleep(1)
                                st.rerun()

                    # --- 4. EXPORTAR Y COMPARTIR ---
                    st.markdown("---")
                    st.markdown("### 📄 Exportar y Compartir Listado")
                    formato_archivo_u = st.radio("Formato de Exportación:", ["PDF", "Excel"], horizontal=True, key="radio_form_uni")
                    if formato_archivo_u == "PDF":
                        archivo_bytes_u = generar_pdf_unidades(df_uni_display)
                        ext_u, mime_u = "pdf", "application/pdf"
                    else:
                        archivo_bytes_u = generar_excel_bytes(df_uni_display, "Unidades")
                        ext_u, mime_u = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    
                    nombre_final_u = f"directorio_unidades.{ext_u}"
                    st.download_button(f"⬇️ Descargar en {formato_archivo_u}", data=archivo_bytes_u, file_name=nombre_final_u, mime=mime_u, use_container_width=True)

                    st.markdown("#### 📤 Compartir a Operadores")
                    cols_env = st.columns(2)
                    lista_correos = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if pd.notna(r.get('correo')) and r['correo']]
                    lista_telefonos = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if pd.notna(r.get('telefono')) and r['telefono']]
                    
                    with cols_env[0]:
                        st.info("📧 Email")
                        sel_em = st.selectbox("Operador (Correo)", ["-- Seleccione --"] + lista_correos, key="em_uni")
                        if st.button("Enviar por Correo", use_container_width=True, key="btn_em_uni"):
                            if sel_em != "-- Seleccione --":
                                dest = sel_em.split(" - ")[-1].strip()
                                with st.spinner(f"Enviando {formato_archivo_u}..."):
                                    if enviar_reporte_correo(dest, archivo_bytes_u, nombre_final_u, "Unidades", ext_u):
                                        st.success("¡Enviado!"); log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Unidades a {dest}")
                            else: st.warning("Elige un operador.")
                            
                    with cols_env[1]:
                        st.success("💬 WhatsApp")
                        sel_wa = st.selectbox("Operador (WhatsApp)", ["-- Seleccione --"] + lista_telefonos, key="wa_uni")
                        if sel_wa != "-- Seleccione --":
                            if st.button("Generar Link WA", use_container_width=True, key="btn_wa_uni"):
                                with st.spinner("Subiendo..."):
                                    tel = re.sub(r'\D', '', sel_wa.split(" - ")[-1].strip())
                                    try:
                                        path = f"unidades_{int(time.time())}.{ext_u}"
                                        supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes_u, file_options={"content-type": mime_u})
                                        url = supabase.storage.from_("reportes").get_public_url(path)
                                        msg = urllib.parse.quote(f"Hola, te comparto el Directorio de Unidades: {url}")
                                        st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">Abrir WhatsApp</button></a>', unsafe_allow_html=True)
                                        log_accion(supabase, usuario_actual, "ENVIO WA", f"Unidades a {sel_wa}")
                                    except Exception as e: st.error(f"Error: {e}")
                        else: st.button("Generar Link WA", disabled=True, use_container_width=True)

                else: st.info("No hay unidades registradas para las propiedades actuales.")
            else: st.info("Aún no hay unidades registradas en el sistema.")
    # ==========================================
    # TAB 3: MANDATOS (Dueños y Porcentajes)
    # ==========================================
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