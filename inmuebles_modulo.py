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
    cw = [15, 60, 30, 40, 50, 40]
    headers = ["ID", "NOMBRE", "TIPO", "CIUDAD", "ASEGURADORA", "POLIZA"]
    for i, h in enumerate(headers):
        pdf.cell(cw[i], 8, h, 1, 0, "C", True)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        textos = [
            str(row.get('ID', '')), str(row.get('NOMBRE', '')), str(row.get('TIPO', '')),
            str(row.get('CIUDAD', '')), str(row.get('ASEGURADORA', '')), str(row.get('numero_poliza', ''))
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
        st.info("💡 Aquí gestionamos los edificios o casas principales (El Cascarón).")
        
        # --- Cargar Operadores para los envíos ---
        try:
            res_ops = supabase.table("operadores").select("nombre, correo, telefono, estado").eq("estado", "ACTIVO").execute()
            df_ops = pd.DataFrame(res_ops.data) if res_ops.data else pd.DataFrame()
        except:
            df_ops = pd.DataFrame()

        # --- Lógica dinámica de tipos ---
        moneda_sesion = st.session_state.get("moneda_usuario", "ALL")
        if moneda_sesion == "EUR": opciones_tipo = ["PISO"]
        elif moneda_sesion == "COP": opciones_tipo = ["APARTAMENTO", "OFICINA", "LOCAL"]
        else: opciones_tipo = ["PISO", "APARTAMENTO", "OFICINA", "LOCAL" ]

        # --- 1. FORMULARIO NUEVA PROPIEDAD (CREATE) ---
        with st.expander("➕ Añadir Nueva Propiedad", expanded=False):
            with st.form("form_nueva_propiedad"):
                st.write("Datos Generales del Inmueble")
                c1, c2, c3 = st.columns(3)
                n_nom = c1.text_input("Nombre / Dirección Principal *", placeholder="Ej: Edificio Central o Piso 5A")
                n_tip = c2.selectbox("Tipo de Propiedad *", opciones_tipo)
                n_ciu = c3.text_input("Ciudad *")
                
                st.write("Datos del Seguro (Opcional)")
                c4, c5, c6 = st.columns(3)
                n_ase = c4.text_input("Aseguradora")
                n_pol = c5.text_input("Número de Póliza")
                n_tel_ase = c6.text_input("Teléfono Aseguradora")
                
                if st.form_submit_button("💾 Guardar Propiedad"):
                    if n_nom and n_ciu:
                        datos_insert = {
                            "nombre": n_nom.strip().upper(), "tipo": n_tip, "ciudad": n_ciu.strip().upper(),
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

        # --- 2. LECTURA DE DATOS (READ) ---
        res_inm = supabase.table("inmuebles").select("*").eq("estado", "ACTIVO").order("id", desc=True).execute()
        df_inm = pd.DataFrame(res_inm.data) if res_inm.data else pd.DataFrame()
        
        if not df_inm.empty:
            df_display = df_inm[['id', 'nombre', 'tipo', 'ciudad', 'aseguradora', 'numero_poliza']].copy()
            df_display.rename(columns={'id': 'ID', 'nombre': 'NOMBRE', 'tipo': 'TIPO', 'ciudad': 'CIUDAD', 'aseguradora': 'ASEGURADORA'}, inplace=True)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # --- 3. GESTIONAR PROPIEDAD (UPDATE / DELETE) ---
            with st.expander("⚙️ Gestionar / Editar Propiedad", expanded=False):
                prop_sel = st.selectbox("Seleccione la propiedad a editar:", df_display['NOMBRE'].tolist())
                if prop_sel:
                    datos_p = df_inm[df_inm['nombre'] == prop_sel].iloc[0]
                    with st.form("form_editar_prop"):
                        e_nom = st.text_input("Nombre", datos_p['nombre'])
                        e_ciu = st.text_input("Ciudad", datos_p['ciudad'])
                        e_ase = st.text_input("Aseguradora", str(datos_p.get('aseguradora', '')))
                        e_pol = st.text_input("Número Póliza", str(datos_p.get('numero_poliza', '')))
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.form_submit_button("📝 Guardar Cambios"):
                            datos_upd = {
                                "nombre": e_nom.strip().upper(), "ciudad": e_ciu.strip().upper(),
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

            # --- 4. EXPORTAR Y COMPARTIR ---
            st.markdown("---")
            st.markdown("### 📄 Exportar y Compartir")
            
            formato_archivo = st.radio("Formato de Exportación:", ["PDF", "Excel"], horizontal=True, key="radio_form_inm")
            
            if formato_archivo == "PDF":
                archivo_bytes = generar_pdf_propiedades(df_display)
                ext, mime = "pdf", "application/pdf"
            else:
                archivo_bytes = generar_excel_bytes(df_display, "Propiedades")
                ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
            nombre_final_archivo = f"directorio_propiedades.{ext}"
            
            st.download_button(f"⬇️ Descargar en {formato_archivo}", data=archivo_bytes, file_name=nombre_final_archivo, mime=mime, use_container_width=True)
            
            st.markdown("#### 📤 Compartir a Operadores")
            cols_env = st.columns(2)
            lista_correos = [f"{r['nombre']} - {r['correo']}" for _, r in df_ops.iterrows() if pd.notna(r.get('correo')) and r['correo']]
            lista_telefonos = [f"{r['nombre']} - {r['telefono']}" for _, r in df_ops.iterrows() if pd.notna(r.get('telefono')) and r['telefono']]
            
            with cols_env[0]:
                st.info("📧 Email")
                sel_em = st.selectbox("Operador (Correo)", ["-- Seleccione --"] + lista_correos, key="em_inm")
                if st.button("Enviar por Correo", use_container_width=True, key="btn_em_inm"):
                    if sel_em != "-- Seleccione --":
                        dest = sel_em.split(" - ")[-1].strip()
                        with st.spinner(f"Enviando {formato_archivo}..."):
                            if enviar_reporte_correo(dest, archivo_bytes, nombre_final_archivo, "Propiedades Base", ext):
                                st.success("¡Enviado!"); log_accion(supabase, usuario_actual, "ENVIO REPORTE", f"Propiedades a {dest}")
                    else: st.warning("Elige un operador.")
                    
            with cols_env[1]:
                st.success("💬 WhatsApp")
                sel_wa = st.selectbox("Operador (WhatsApp)", ["-- Seleccione --"] + lista_telefonos, key="wa_inm")
                if sel_wa != "-- Seleccione --":
                    if st.button("Generar Link WA", use_container_width=True, key="btn_wa_inm"):
                        with st.spinner("Subiendo..."):
                            tel = re.sub(r'\D', '', sel_wa.split(" - ")[-1].strip())
                            try:
                                path = f"propiedades_{int(time.time())}.{ext}"
                                supabase.storage.from_("reportes").upload(path=path, file=archivo_bytes, file_options={"content-type": mime})
                                url = supabase.storage.from_("reportes").get_public_url(path)
                                msg = urllib.parse.quote(f"Hola, te comparto el Directorio de Propiedades: {url}")
                                st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">Abrir WhatsApp</button></a>', unsafe_allow_html=True)
                                log_accion(supabase, usuario_actual, "ENVIO WA", f"Propiedades a {sel_wa}")
                            except Exception as e: st.error(f"Error: {e}")
                else: st.button("Generar Link WA", disabled=True, use_container_width=True)

        else:
            st.info("ℹ️ Aún no hay propiedades registradas o activas.")
    # ==========================================
    # TAB 2: UNIDADES (Las Divisiones)
    # ==========================================
    with tab2:
        st.subheader("Gestión de Unidades Rentables")
        st.info("💡 Aquí dividiremos la propiedad seleccionada en Apartamentos, Locales o Habitaciones para poder alquilarlas.")
        st.button("➕ Simular Botón: Añadir Unidad", disabled=True)

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