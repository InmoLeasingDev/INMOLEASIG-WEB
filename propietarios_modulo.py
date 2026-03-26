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
# 3. MÓDULO PRINCIPAL CRUD (ESTILO MODO PRO)
# ==========================================
def mostrar_modulo_propietarios(supabase):
    st.header("🔑 Gestión de Propietarios")
    st.caption("Administración de dueños e inversores de la cadena InmoLeasing")

    # --- Sesión y Filtros Silenciosos ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    
    # 🛡️ Entorno operativo estricto
    moneda_sesion = st.session_state.get("moneda_usuario", "EUR")

    # 1. Inicializador de estado para los paneles
    if 'modo_propietario' not in st.session_state:
        st.session_state.modo_propietario = "NADA"

    # --- Carga de Datos ---
    try:
        res_prop = supabase.table("propietarios").select("*").eq("estado", "ACTIVO").execute()
        df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        
        res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
        df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        df_prop, df_ops = pd.DataFrame(), pd.DataFrame()

    # Filtro automático por moneda (ESTRICTO)
    if not df_prop.empty:
        df_prop = df_prop[df_prop['moneda'] == moneda_sesion]

    # --- LECTURA DE DATOS (LA CUADRÍCULA) ---
    if not df_prop.empty:
        busqueda = st.text_input("🔍 Buscar por nombre o ID...").upper().strip()
        df_display = df_prop.sort_values('nombre')
        
        if busqueda:
            mask = df_display['nombre'].str.contains(busqueda) | df_display['identificacion'].str.contains(busqueda)
            df_display = df_display[mask]
            
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
    else:
        st.info("ℹ️ No hay propietarios registrados o activos en tu región.")

    # ==========================================
    # 🛠️ BARRA DE HERRAMIENTAS (MODO PRO - 3 BOTONES)
    # ==========================================
    t_c1, t_c2, t_c3, t_c5 = st.columns([1.5, 1.5, 1.5, 5.5]) 
    
    if t_c1.button("➕ Nuevo", key="btn_nuevo_prop", use_container_width=True):
        st.session_state.modo_propietario = "CREAR"
        st.rerun()
        
    if not df_prop.empty:
        if t_c2.button("⚙️ Gestionar", key="btn_edit_prop", use_container_width=True):
            st.session_state.modo_propietario = "EDITAR"
            st.rerun()
            
        if t_c3.button("📊 Reportes", key="btn_rep_prop", use_container_width=True):
            st.session_state.modo_propietario = "REPORTES"
            st.rerun()

    # =========================================
    # 🗂️ PANELES DINÁMICOS
    # =========================================
    
    # --- PANEL: CREAR NUEVO PROPIETARIO ---
    if st.session_state.modo_propietario == "CREAR":
        st.markdown("---")
        with st.form("form_nuevo_prop", clear_on_submit=True):
            st.markdown("**✨ Añadir Nuevo Propietario**")
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
            
            # Asignación automática de moneda
            n_mon = moneda_sesion
            c6.text_input("Entorno Operativo", value=n_mon, disabled=True)
            n_ban = c7.text_input("Banco")
            n_tcu = c8.selectbox("Tipo de Cuenta", ["IBAN", "AHORROS", "CORRIENTE","LLAVE"])
            n_cba = st.text_input("Número de Cuenta / IBAN")


            st.subheader("📄 Identificación Propietario")
            doc_subido = st.file_uploader("Escáner de Identificación (Max 5MB - PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
            st.markdown("*Campos obligatorios marcados con asterisco (*)*")
            
            st.markdown("---")
            col_b1, col_b2, col_esp = st.columns([1.5, 1.2, 7.3])
            
            if col_b1.form_submit_button("💾 Guardar"):
                if n_nom and n_id:
                    url_doc = None
                    hubo_error_archivo = False
                    
                    if doc_subido is not None:
                        if doc_subido.size > 5 * 1024 * 1024:
                            st.error("❌ El documento supera el límite de 5MB.")
                            hubo_error_archivo = True
                        else:
                            with st.spinner("Subiendo..."):
                                try:
                                    ext = doc_subido.name.split('.')[-1].lower()
                                    tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                    ruta_doc = f"id_{n_id.strip()}_{int(time.time())}.{ext}"
                                    supabase.storage.from_("documentos").upload(path=ruta_doc, file=doc_subido.getvalue(), file_options={"content-type": tipo_mime})
                                    url_doc = supabase.storage.from_("documentos").get_public_url(ruta_doc)
                                except Exception as e:
                                    st.error(f"❌ Error al subir: {e}")
                                    hubo_error_archivo = True

                    if not hubo_error_archivo:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(), "tipo_id": n_tid, "identificacion": n_id.strip().upper(),
                            "movil": n_mov.strip(), "correo": n_cor.strip().lower(), "moneda": n_mon,
                            "banco": n_ban.strip().upper(), "tipo_cuenta": n_tcu, "cuenta_banco": n_cba.strip().upper(),
                            "url_documento": url_doc, "estado": "ACTIVO"
                        }
                        supabase.table("propietarios").insert(datos_insert).execute()
                        log_accion(supabase, usuario_actual, "CREAR PROPIETARIO", n_nom.strip().upper())
                        st.session_state.modo_propietario = "NADA"
                        st.success("✅ Propietario registrado.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("⚠️ Nombre e Identificación son obligatorios.")
                    
            if col_b2.form_submit_button("❌ Cerrar"):
                st.session_state.modo_propietario = "NADA"
                st.rerun()

    # --- PANEL: GESTIONAR PROPIETARIO ---
    elif st.session_state.modo_propietario == "EDITAR" and not df_prop.empty:
        st.markdown("---")
        st.markdown("**⚙️ Gestionar Propietario**")
        
        prop_sel = st.selectbox("Selecciona un propietario para editar:", df_prop['nombre'].tolist())
        if prop_sel:
            datos_p = df_prop[df_prop['nombre'] == prop_sel].iloc[0]
            p_id = str(datos_p.get('id', '0'))
            
            with st.form(key=f"form_edit_{p_id}"):
                st.subheader("Información Personal")
                c1, c2, c3 = st.columns([2, 1, 1])
                e_nom = c1.text_input("Nombre", str(datos_p.get('nombre', '')), key=f"nom_{p_id}")
                
                lista_tid = ["CC", "NIT", "DNI", "NIE", "CIF", "OTRO"]
                val_tid = datos_p.get('tipo_id')
                e_tid = c2.selectbox("Tipo ID", lista_tid, index=lista_tid.index(val_tid) if pd.notna(val_tid) and val_tid in lista_tid else 0, key=f"tid_{p_id}")
                e_id = c3.text_input("Número de Identificación", str(datos_p.get('identificacion', '')), key=f"id_{p_id}")
                
                c4, c5 = st.columns(2)
                e_mov = c4.text_input("Móvil", str(datos_p.get('movil', '')), key=f"mov_{p_id}")
                e_cor = c5.text_input("Correo", str(datos_p.get('correo', '')), key=f"cor_{p_id}")
                
                st.subheader("Finanzas")
                c6, c7 = st.columns([1, 2])
                
                # Moneda bloqueada
                e_mon = datos_p.get('moneda', moneda_sesion)
                c6.text_input("Entorno (Bloqueado)", value=e_mon, disabled=True)
                e_ban = c7.text_input("Banco", str(datos_p.get('banco', '')), key=f"ban_{p_id}")
                c8, c9 = st.columns([1, 2])
                lista_tcu = ["IBAN", "AHORROS", "CORRIENTE", "NEQUI", "DAVIPLATA"]
                val_tcu = datos_p.get('tipo_cuenta')
                e_tcu = c8.selectbox("Tipo de Cuenta", lista_tcu, index=lista_tcu.index(val_tcu) if pd.notna(val_tcu) and val_tcu in lista_tcu else 0, key=f"tcu_{p_id}")
                e_cba = c9.text_input("Número de Cuenta", str(datos_p.get('cuenta_banco', '')), key=f"cba_{p_id}")
                
                st.subheader("📄 Identificación")
                url_actual = datos_p.get('url_documento')
                if pd.isna(url_actual) or str(url_actual).strip() == "" or str(url_actual).lower() == "nan": url_actual = None
                
                if url_actual:
                    nombre_archivo = urllib.parse.unquote(url_actual.split('/')[-1])
                    st.markdown(f"**Documento actual:** `{nombre_archivo}` - [🔍 Abrir]({url_actual})")
                else:
                    st.info("No hay documento registrado.")
                
                doc_edit = st.file_uploader("Actualizar/Subir nuevo", type=["pdf", "jpg", "jpeg", "png"], key=f"doc_{p_id}")
                
                st.markdown("---")
                # Nuevo ordens táctico: Actualizar | Borrar | Cerrar
                col_btn1, col_btn2, col_btn3, col_esp = st.columns([2.0, 2.5, 1.5, 4.0])
                
                btn_actualizar = col_btn1.form_submit_button("📝 Actualizar")
                
                btn_borrar_doc = False
                if url_actual:
                    btn_borrar_doc = col_btn2.form_submit_button("🗑️ Borrar Documento")
                    
                btn_cerrar = col_btn3.form_submit_button("❌ Cerrar")

                if btn_cerrar:
                    st.session_state.modo_propietario = "NADA"
                    st.rerun()

                elif btn_borrar_doc:
                    with st.spinner("Eliminando..."):
                        try:
                            supabase.storage.from_("documentos").remove([url_actual.split('/documentos/')[-1]])
                        except: pass
                        supabase.table("propietarios").update({"url_documento": None}).eq("id", int(p_id)).execute()
                        st.success("✅ Documento eliminado.")
                        time.sleep(1)
                        st.rerun()

                elif btn_actualizar:
                    if e_nom and e_id:
                        url_doc_upd = url_actual 
                        hubo_error = False
                        if doc_edit is not None:
                            if doc_edit.size > 5 * 1024 * 1024:
                                st.error("❌ Límite 5MB.")
                                hubo_error = True
                            else:
                                with st.spinner("Actualizando..."):
                                    try:
                                        ext = doc_edit.name.split('.')[-1].lower()
                                        tipo_mime = "application/pdf" if ext == "pdf" else f"image/{ext.replace('jpg', 'jpeg')}"
                                        ruta_nueva = f"id_{e_id.strip()}_{int(time.time())}.{ext}"
                                        supabase.storage.from_("documentos").upload(path=ruta_nueva, file=doc_edit.getvalue(), file_options={"content-type": tipo_mime})
                                        url_doc_upd = supabase.storage.from_("documentos").get_public_url(ruta_nueva)
                                        if url_actual:
                                            try: supabase.storage.from_("documentos").remove([url_actual.split('/documentos/')[-1]])
                                            except: pass
                                    except Exception as e:
                                        st.error(f"❌ Error: {e}")
                                        hubo_error = True

                        if not hubo_error:
                            datos_upd = {
                                "nombre": e_nom.strip().upper(), "tipo_id": e_tid, "identificacion": e_id.strip().upper(),
                                "movil": e_mov.strip(), "correo": e_cor.strip().lower(), "moneda": e_mon,
                                "banco": e_ban.strip().upper(), "tipo_cuenta": e_tcu, "cuenta_banco": e_cba.strip().upper(),
                                "url_documento": url_doc_upd
                            }
                            supabase.table("propietarios").update(datos_upd).eq("id", int(p_id)).execute()
                            log_accion(supabase, usuario_actual, "EDITAR PROPIETARIO", e_nom.strip().upper())
                            st.session_state.modo_propietario = "NADA"
                            st.success("✅ Actualizado.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("⚠️ Nombre e ID obligatorios.")

            st.write("")
            c_del1, c_del2 = st.columns([7, 3])
            confirmar_baja = c_del1.checkbox("⚠️ Confirmo baja.", key=f"del_chk_p_{p_id}")
            if c_del2.button("🚫 Dar de Baja", disabled=not confirmar_baja, key=f"del_btn_p_{p_id}"):
                supabase.table("propietarios").update({"estado": "INACTIVO"}).eq("id", int(p_id)).execute()
                log_accion(supabase, usuario_actual, "ELIMINAR PROPIETARIO", datos_p['nombre'])
                st.session_state.modo_propietario = "NADA"
                st.success("✅ Propietario inactivo.")
                time.sleep(1)
                st.rerun()

    # --- PANEL: REPORTES ---
    elif st.session_state.modo_propietario == "REPORTES" and not df_prop.empty:
        st.markdown("---")
        st.markdown("### 📄 Exportar y Compartir Reportes")
        
        col_exp1, col_exp2, col_exp3 = st.columns([2, 1.5, 3])
        with col_exp1:
            tipo_contenido = st.selectbox("Contenido del reporte:", ["Reporte Básico", "Reporte Detallado"], key="sel_cont_prop", label_visibility="collapsed")
        with col_exp2:
            formato_archivo = st.selectbox("Formato:", ["PDF", "Excel"], key="sel_form_prop", label_visibility="collapsed")

        es_detallado = (tipo_contenido == "Reporte Detallado")
        nombre_base = "propietarios_detallado" if es_detallado else "propietarios_basico"
        
        if formato_archivo == "PDF":
            archivo_bytes = generar_pdf_propietarios(df_display, detallado=es_detallado)
            ext, mime = "pdf", "application/pdf"
        else:
            if es_detallado:
                df_excel = df_display[['nombre', 'identificacion', 'movil', 'correo', 'moneda', 'banco', 'cuenta_banco']].copy()
                df_excel.rename(columns={'nombre':'NOMBRE', 'identificacion':'ID', 'movil':'MOVIL', 'correo':'CORREO', 'moneda':'MONEDA', 'banco':'BANCO', 'cuenta_banco':'CUENTA'}, inplace=True)
            else:
                df_excel = df_display[['nombre', 'identificacion', 'movil', 'correo']].copy()
                df_excel.rename(columns={'nombre':'NOMBRE', 'identificacion':'ID', 'movil':'MOVIL', 'correo':'CORREO'}, inplace=True)
            archivo_bytes = generar_excel_bytes(df_excel, "Propietarios")
            ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        with col_exp3:
            st.download_button(
                label=f"⬇️ Descargar {formato_archivo}",
                data=archivo_bytes,
                file_name=f"{nombre_base}.{ext}",
                mime=mime,
                use_container_width=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📤 Compartir a Operadores")
        cols_env = st.columns([4, 4, 2])
        
        lista_correos = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if r['correo']]
        with cols_env[0]:
            sel_em = st.selectbox("Email", ["-- Seleccione --"] + lista_correos, key="em_prop_t1")
            if st.button("Enviar por Correo", use_container_width=True):
                if sel_em != "-- Seleccione --":
                    dest = sel_em.split(" - ")[-1].strip()
                    with st.spinner("Enviando..."):
                        if enviar_reporte_correo(dest, archivo_bytes, f"{nombre_base}.{ext}", tipo_contenido, ext):
                            st.success("¡Enviado!")
                else: st.warning("Elige un operador.")
                
        lista_tels = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if r['telefono']]
        with cols_env[1]:
            sel_wa = st.selectbox("WhatsApp", ["-- Seleccione --"] + lista_tels, key="wa_prop_t1")
            if st.button("Generar Link WA", use_container_width=True):
                if sel_wa != "-- Seleccione --":
                    with st.spinner("Subiendo..."):
                        try:
                            tel = re.sub(r'\D', '', sel_wa.split(" - ")[-1].strip())
                            path = f"{nombre_base}_{int(time.time())}.{ext}"
                            supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes, file_options={"content-type": mime})
                            link = supabase.storage.from_("reportes").get_public_url(path)
                            msg = urllib.parse.quote(f"Hola, te comparto el {tipo_contenido}. Descárgalo aquí: {link}")
                            st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:5px;">Abrir WA</button></a>', unsafe_allow_html=True)
                        except Exception as e: st.error(f"Error: {e}")
                else: st.warning("Elige un operador.")
        
        with cols_env[2]:
            st.write("")
            st.write("")
            if st.button("❌ Cerrar Panel", use_container_width=True):
                st.session_state.modo_propietario = "NADA"
                st.rerun()