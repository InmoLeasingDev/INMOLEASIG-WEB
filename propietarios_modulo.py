import streamlit as st
import pandas as pd
import re
import time
import urllib.parse
from fpdf import FPDF
import zoneinfo
from datetime import datetime
# --- NUESTRA LIBRERÍA MAESTRA ---
from herramientas import log_accion, enviar_reporte_correo, generar_excel_bytes

# ==========================================
# 1. FUNCIONES AUXILIARES
# ==========================================
def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'ignore').decode('latin-1') if pd.notna(texto) else ""

# ==========================================
# 2. MOTORES PDF (Básico y Detallado)
# ==========================================
def generar_pdf_propietarios(df, detallado=False):
    pdf = FPDF(orientation="L" if detallado else "P") # Horizontal si es detallado
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    titulo = "INMOLEASING - PROPIETARIOS (DETALLADO)" if detallado else "INMOLEASING - PROPIETARIOS (BASICO)"
    pdf.cell(0, 10, titulo, ln=True, align="C"); pdf.ln(5)
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 220, 255)
    
    if detallado:
        cw = [50, 25, 30, 45, 20, 45, 60]
        headers = ["NOMBRE", "ID", "MOVIL", "CORREO", "MONEDA", "BANCO", "CUENTA"]
    else:
        cw = [60, 30, 40, 60]
        headers = ["NOMBRE", "ID", "MOVIL", "CORREO"]
        
    for i, h in enumerate(headers): 
        pdf.cell(cw[i], 10, h, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        if detallado:
            textos = [row['nombre'], row['identificacion'], row['movil'], row['correo'], row['moneda'], row['banco'], row['cuenta_banco']]
        else:
            textos = [row['nombre'], row['identificacion'], row['movil'], row['correo']]
            
        textos = [limpiar_texto_pdf(t) for t in textos]
        h_fila = 5 * max([len(pdf.multi_cell(cw[i], 5, txt, split_only=True)) for i, txt in enumerate(textos)])
        if pdf.get_y() + h_fila > (190 if detallado else 270): pdf.add_page()
        
        x, y = pdf.get_x(), pdf.get_y()
        for i, txt in enumerate(textos):
            pdf.set_xy(x, y); pdf.rect(x, y, cw[i], h_fila)
            pdf.multi_cell(cw[i], 5, txt, align='L'); x += cw[i]
        pdf.set_xy(10, y + h_fila)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. MÓDULO PRINCIPAL CRUD
# ==========================================
def mostrar_modulo_propietarios(supabase):
    st.header("🔑 Gestión de Propietarios")
    st.caption("Administración de dueños e inversores de la cadena InmoLeasing")

    # --- Sesión y Filtros Silenciosos ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    moneda_sesion = st.session_state.get("moneda_usuario", "ALL")

    # --- Carga de Datos ---
    try:
        res_prop = supabase.table("propietarios").select("*").eq("estado", "ACTIVO").execute()
        df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        
        res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
        df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        df_prop, df_ops = pd.DataFrame(), pd.DataFrame()

    # Filtro automático por moneda
    if not df_prop.empty and moneda_sesion != "ALL":
        df_prop = df_prop[df_prop['moneda'] == moneda_sesion]

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Propietario", "⚙️ Gestionar"])

    # ===========================================
    # TAB 1: DIRECTORIO Y REPORTES
    # ===========================================
    with tab1:
        if not df_prop.empty:
            busqueda = st.text_input("🔍 Buscar por nombre o ID...").upper().strip()
            df_display = df_prop.sort_values('nombre')
            
            #st.dataframe(df_display[['nombre', 'tipo_id', 'identificacion', 'movil', 'correo', 'moneda']], use_container_width=True, hide_index=True)
            if busqueda:
                mask = df_display['nombre'].str.contains(busqueda) | df_display['identificacion'].str.contains(busqueda)
                df_display = df_display[mask]
                
            # Mostramos la tabla configurando la columna de URL como un enlace interactivo
            st.dataframe(
                df_display[['nombre', 'tipo_id', 'identificacion', 'movil', 'correo', 'moneda', 'url_documento']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "nombre": "NOMBRE",
                    "tipo_id": "TIPO ID",
                    "identificacion": "IDENTIFICACIÓN",
                    "movil": "MÓVIL",
                    "correo": "CORREO",
                    "moneda": "MON",
                    "url_documento": st.column_config.LinkColumn(
                        "📄 DOCUMENTO",
                        help="Haz clic para abrir el documento de identidad",
                        display_text="🔍 Ver Archivo"
                    )
                }
            )

            # ==========================================
            # NUEVO PANEL DE EXPORTACIÓN TAB 1 (FLEXIBLE)
            # ==========================================
            st.markdown("---")
            st.markdown("### 📄 Exportar y Compartir Reportes")
            
            # --- 1. Opciones de Generación ---
            st.write("**1. Selecciona el contenido del reporte:**")
            tipo_contenido = st.radio(
                "Contenido:", 
                ["Reporte Básico", "Reporte Detallado"], 
                horizontal=True, 
                label_visibility="collapsed",
                key="radio_cont_prop"
            )
            
            st.write("**2. Selecciona el formato:**")
            formato_archivo = st.radio(
                "Formato:", 
                ["PDF", "Excel"], 
                horizontal=True, 
                label_visibility="collapsed",
                key="radio_form_prop"
            )

            # --- 2. Preparar los datos según la elección ---
            es_detallado = (tipo_contenido == "Reporte Detallado")
            nombre_base = "propietarios_detallado" if es_detallado else "propietarios_basico"
            
            if formato_archivo == "PDF":
                archivo_bytes = generar_pdf_propietarios(df_display, detallado=es_detallado)
                ext, mime = "pdf", "application/pdf"
            else: # Excel
                if es_detallado:
                    df_excel = df_display[['nombre', 'identificacion', 'movil', 'correo', 'moneda', 'banco', 'cuenta_banco']].copy()
                    df_excel.rename(columns={'nombre':'NOMBRE', 'identificacion':'ID', 'movil':'MOVIL', 'correo':'CORREO', 'moneda':'MONEDA', 'banco':'BANCO', 'cuenta_banco':'CUENTA'}, inplace=True)
                else:
                    df_excel = df_display[['nombre', 'identificacion', 'movil', 'correo']].copy()
                    df_excel.rename(columns={'nombre':'NOMBRE', 'identificacion':'ID', 'movil':'MOVIL', 'correo':'CORREO'}, inplace=True)
                
                archivo_bytes = generar_excel_bytes(df_excel, "Propietarios")
                ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            nombre_final_archivo = f"{nombre_base}.{ext}"

            # --- 3. Botón de Descarga Directa ---
            st.write("**3. Descargar al equipo:**")
            st.download_button(
                label=f"⬇️ Descargar {tipo_contenido} en {formato_archivo}",
                data=archivo_bytes,
                file_name=nombre_final_archivo,
                mime=mime,
                use_container_width=True
            )

            # --- 4. Compartir ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📤 Compartir a Operadores")
            st.write(f"*(Se enviará el archivo: **{nombre_final_archivo}**)*")
            
            cols_env_t1 = st.columns(2)
            
            # Preparar listas de contactos
            lista_correos = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if r['correo']]
            lista_telefonos = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if r['telefono']]
            
            # Correo
            with cols_env_t1[0]:
                st.info("📧 Email")
                if lista_correos:
                    sel_em_t1 = st.selectbox("Operador (Correo)", ["-- Seleccione --"] + lista_correos, key="em_prop_t1")
                    if st.button("Enviar por Correo", use_container_width=True, key="btn_em_prop"):
                        if sel_em_t1 != "-- Seleccione --":
                            dest = sel_em_t1.split(" - ")[-1].strip()
                            with st.spinner(f"Enviando {formato_archivo}..."):
                                if enviar_reporte_correo(dest, archivo_bytes, nombre_final_archivo, tipo_contenido, ext):
                                    st.success("¡Enviado!")
                                    log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"{tipo_contenido} a {dest}")
                        else: 
                            st.warning("Elige un operador.")
                else:
                    st.warning("No hay operadores con correo.")

            # WhatsApp
            with cols_env_t1[1]:
                st.success("💬 WhatsApp")
                if lista_telefonos:
                    sel_wa_t1 = st.selectbox("Operador (WhatsApp)", ["-- Seleccione --"] + lista_telefonos, key="wa_prop_t1")
                    if sel_wa_t1 != "-- Seleccione --":
                        if st.button("Generar Link WhatsApp", use_container_width=True, key="btn_wa_prop"):
                            with st.spinner("Subiendo a la nube..."):
                                tel = re.sub(r'\D', '', sel_wa_t1.split(" - ")[-1].strip())
                                try:
                                    ts = int(time.time())
                                    path = f"{nombre_base}_{ts}.{ext}"
                                    supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes, file_options={"content-type": mime})
                                    link = supabase.storage.from_("reportes").get_public_url(path)
                                    msg = urllib.parse.quote(f"Hola, te comparto el {tipo_contenido} de Propietarios. Puedes descargarlo aquí: {link}")
                                    st.markdown(f'''<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold;">Abrir WhatsApp</button></a>''', unsafe_allow_html=True)
                                    log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"{tipo_contenido} WA a {sel_wa_t1}")
                                except Exception as e: 
                                    st.error(f"Error al subir: {e}")
                    else: 
                        st.button("Generar Link WhatsApp", disabled=True, use_container_width=True, key="btn_wa_prop_dis")
                else:
                    st.warning("No hay operadores con teléfono.")
        else:
            st.info("ℹ️ No hay propietarios registrados o activos en tu región.")
    # ==========================================
    # TAB 2: NUEVO PROPIETARIO
    # ==========================================
    with tab2:
        with st.form("form_nuevo_prop"):
            st.subheader("Datos Personales")
            c1, c2, c3 = st.columns([2, 1, 1])
            n_nom = c1.text_input("Nombre Completo / Razón Social *")
            n_tid = c2.selectbox("Tipo ID *", ["CC", "NIT", "DNI", "NIE", "CIF", "OTRO"])
            n_id = c3.text_input("Número de Identificación *")
            
            c4, c5 = st.columns(2)
            n_mov = c4.text_input("Móvil Principal")
            n_cor = c5.text_input("Correo Principal")
            
            st.subheader("Datos Financieros")
            c6, c7, c8 = st.columns([1, 2, 2])
            n_mon = c6.selectbox("Moneda *", ["EUR", "COP"])
            n_ban = c7.text_input("Banco")
            n_tcu = c8.selectbox("Tipo de Cuenta", ["IBAN", "AHORROS", "CORRIENTE", "NEQUI", "DAVIPLATA"])
            n_cba = st.text_input("Número de Cuenta / IBAN")
            
            # --- NUEVO: GESTIÓN DOCUMENTAL ---
            st.subheader("📄 Identificacion Propietario")
            doc_subido = st.file_uploader("Escáner de Identificación (Max 5MB - PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
            
            st.markdown("*Campos obligatorios marcados con asterisco (*)*")
            
            if st.form_submit_button("💾 Guardar Propietario"):
                if n_nom and n_id:
                    url_doc = None
                    hubo_error_archivo = False
                    
                    # --- Lógica de subida del archivo ---
                    if doc_subido is not None:
                        if doc_subido.size > 5 * 1024 * 1024:
                            st.error("❌ El documento supera el límite de 5MB. Por favor, redúcelo.")
                            hubo_error_archivo = True
                        else:
                            with st.spinner("Subiendo documento a la bóveda..."):
                                try:
                                    ext = doc_subido.name.split('.')[-1].lower()
                                    # Detectar el tipo de archivo (MIME)
                                    tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                    ruta_doc = f"id_{n_id.strip()}_{int(time.time())}.{ext}"
                                    supabase.storage.from_("documentos").upload(path=ruta_doc, file=doc_subido.getvalue(), file_options={"content-type": tipo_mime})
                                    url_doc = supabase.storage.from_("documentos").get_public_url(ruta_doc)
                                except Exception as e:
                                    st.error(f"❌ Error al subir el archivo: {e}")
                                    hubo_error_archivo = True

                    # --- Guardar en Base de Datos (Solo si el archivo subió bien) ---
                    if not hubo_error_archivo:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(),
                            "tipo_id": n_tid,
                            "identificacion": n_id.strip().upper(),
                            "movil": n_mov.strip(),
                            "correo": n_cor.strip().lower(),
                            "moneda": n_mon,
                            "banco": n_ban.strip().upper(),
                            "tipo_cuenta": n_tcu,
                            "cuenta_banco": n_cba.strip().upper(),
                            "url_documento": url_doc,
                            "estado": "ACTIVO"
                        }
                        supabase.table("propietarios").insert(datos_insert).execute()
                        log_accion(supabase, usuario_actual, "CREAR PROPIETARIO", n_nom.strip().upper())
                        st.success("✅ Propietario registrado con éxito.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("⚠️ El Nombre y el Número de Identificación son obligatorios.")
    # ==========================================
    # TAB 3: GESTIONAR (Refresh Dinámico y Auto-Limpieza)
    # ==========================================
    with tab3:
        if not df_prop.empty:
            prop_sel = st.selectbox("🔍 Selecciona un propietario para editar:", df_prop['nombre'].tolist(), key="sel_prop_tab3")
            datos_p = df_prop[df_prop['nombre'] == prop_sel].iloc[0]
            p_id = str(datos_p.get('id', '0')) # Obtenemos el ID para forzar el refresco
            
            # 1. AL INICIO: Forzamos que cada formulario sea único por propietario
            with st.form(key=f"form_edit_{p_id}"):
                st.subheader("Editar Información Personal")
                c1, c2, c3 = st.columns([2, 1, 1])
                # 2. Atamos cada input al ID del propietario para que se limpie al cambiar
                e_nom = c1.text_input("Nombre", str(datos_p.get('nombre', '')), key=f"nom_{p_id}")
                
                lista_tid = ["CC", "NIT", "DNI", "NIE", "CIF", "OTRO"]
                val_tid = datos_p.get('tipo_id')
                idx_tid = lista_tid.index(val_tid) if pd.notna(val_tid) and val_tid in lista_tid else 0
                e_tid = c2.selectbox("Tipo ID", lista_tid, index=idx_tid, key=f"tid_{p_id}")
                
                e_id = c3.text_input("Número de Identificación", str(datos_p.get('identificacion', '')), key=f"id_{p_id}")
                
                c4, c5 = st.columns(2)
                e_mov = c4.text_input("Móvil", str(datos_p.get('movil', '')), key=f"mov_{p_id}")
                e_cor = c5.text_input("Correo", str(datos_p.get('correo', '')), key=f"cor_{p_id}")
                
                st.subheader("Finanzas")
                c6, c7 = st.columns([1, 2])
                
                lista_mon = ["EUR", "COP"]
                val_mon = datos_p.get('moneda')
                idx_mon = lista_mon.index(val_mon) if pd.notna(val_mon) and val_mon in lista_mon else 0
                e_mon = c6.selectbox("Moneda", lista_mon, index=idx_mon, key=f"mon_{p_id}")
                
                e_ban = c7.text_input("Banco", str(datos_p.get('banco', '')), key=f"ban_{p_id}")
                
                c8, c9 = st.columns([1, 2])
                lista_tcu = ["IBAN", "AHORROS", "CORRIENTE", "NEQUI", "DAVIPLATA"]
                val_tcu = datos_p.get('tipo_cuenta')
                idx_tcu = lista_tcu.index(val_tcu) if pd.notna(val_tcu) and val_tcu in lista_tcu else 0
                e_tcu = c8.selectbox("Tipo de Cuenta", lista_tcu, index=idx_tcu, key=f"tcu_{p_id}")
                
                e_cba = c9.text_input("Número de Cuenta / IBAN", str(datos_p.get('cuenta_banco', '')), key=f"cba_{p_id}")
                
                # --- GESTIÓN DOCUMENTAL ---
                st.subheader("📄 Identificacion Propietario")
                
                # Limpieza de valores nulos o "NaN" de Pandas para que funcione siempre
                url_actual = datos_p.get('url_documento')
                if pd.isna(url_actual) or str(url_actual).strip() == "" or str(url_actual).lower() == "nan":
                    url_actual = None
                
                if url_actual:
                    # Extraemos el nombre real del archivo cortando la URL desde la última barra '/'
                    nombre_archivo = urllib.parse.unquote(url_actual.split('/')[-1])
                    st.markdown(f"**Documento actual:** `{nombre_archivo}` - [🔍 Abrir y Ver Archivo]({url_actual})")
                else:
                    st.info("ℹ️ No hay documento registrado para este propietario.")
                
                               
                # El file_uploader también atado al ID para que suelte el PDF anterior
                doc_edit = st.file_uploader("Actualizar/Subir nuevo documento (Max 5MB - PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"], key=f"doc_{p_id}")
                
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.form_submit_button("📝 Actualizar Datos"):
                    if e_nom and e_id:
                        url_doc_upd = url_actual 
                        hubo_error_archivo = False
                        
                        if doc_edit is not None:
                            if doc_edit.size > 5 * 1024 * 1024:
                                st.error("❌ El documento supera el límite de 5MB. Por favor, redúcelo.")
                                hubo_error_archivo = True
                            else:
                                with st.spinner("Actualizando documento en la bóveda..."):
                                    try:
                                        ext = doc_edit.name.split('.')[-1].lower()
                                        tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                        ruta_doc_nueva = f"id_{e_id.strip()}_{int(time.time())}.{ext}"
                                        supabase.storage.from_("documentos").upload(path=ruta_doc_nueva, file=doc_edit.getvalue(), file_options={"content-type": tipo_mime})
                                        url_doc_upd = supabase.storage.from_("documentos").get_public_url(ruta_doc_nueva)
                                        
                                        # Auto-Limpieza
                                        if url_actual:
                                            try:
                                                ruta_vieja = url_actual.split('/documentos/')[-1]
                                                supabase.storage.from_("documentos").remove([ruta_vieja])
                                            except:
                                                pass 
                                                
                                    except Exception as e:
                                        st.error(f"❌ Error al subir el archivo: {e}")
                                        hubo_error_archivo = True

                        if not hubo_error_archivo:
                            datos_upd = {
                                "nombre": e_nom.strip().upper(),
                                "tipo_id": e_tid,
                                "identificacion": e_id.strip().upper(),
                                "movil": e_mov.strip(),
                                "correo": e_cor.strip().lower(),
                                "moneda": e_mon,
                                "banco": e_ban.strip().upper(),
                                "tipo_cuenta": e_tcu,
                                "cuenta_banco": e_cba.strip().upper(),
                                "url_documento": url_doc_upd
                            }
                            supabase.table("propietarios").update(datos_upd).eq("id", int(p_id)).execute()
                            log_accion(supabase, usuario_actual, "EDITAR PROPIETARIO", e_nom.strip().upper())
                            st.success("✅ Actualizado correctamente.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("⚠️ El Nombre y el Número de Identificación son obligatorios.")
                        
            # --- SEGURO DE ELIMINACIÓN TAB 3 ---
            st.markdown("---")
            st.subheader("🚨 Zona de Peligro")
            st.warning("⚠️ **Atención:** Dar de baja a este propietario lo ocultará del sistema y afectará los mandatos vinculados.")
            confirmar_baja_prop = st.checkbox("Confirmo que deseo dar de baja a este propietario.", key=f"conf_prop_{p_id}")
            
            if st.button("🗑️ Dar de Baja (Eliminar)", disabled=not confirmar_baja_prop, key=f"btn_baja_{p_id}"):
                supabase.table("propietarios").update({"estado": "INACTIVO"}).eq("id", int(p_id)).execute()
                log_accion(supabase, usuario_actual, "ELIMINAR PROPIETARIO", datos_p['nombre'])
                st.success("✅ Propietario dado de baja.")
                time.sleep(1)
                st.rerun()