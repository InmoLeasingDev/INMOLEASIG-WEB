import streamlit as st
import pandas as pd
from fpdf import FPDF

# ==========================================
# 1. FUNCIÓN PARA GENERAR EL REPORTE PDF
# ==========================================
# Ahora recibe el dataframe y el diccionario de roles dinámico
def generar_pdf_usuarios(df, diccionario_roles):
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "INMOLEASING - REPORTE DE USUARIOS", ln=True, align="C")
    pdf.ln(10)
    
    # Cabeceras de tabla
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    
    pdf.cell(60, 10, "NOMBRE", border=1, fill=True)
    pdf.cell(70, 10, "EMAIL", border=1, fill=True)
    pdf.cell(50, 10, "ROL", border=1, fill=True)
    pdf.ln()
    
    # Filas de datos
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        # Traducimos el ID de rol a nombre para el PDF consultando el diccionario
        rol_texto = diccionario_roles.get(row['id_rol'], "SIN ROL")
        
        pdf.cell(60, 10, str(row['nombre']), border=1)
        pdf.cell(70, 10, str(row['email']), border=1)
        pdf.cell(50, 10, str(rol_texto), border=1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. MÓDULO PRINCIPAL DE USUARIOS
# ==========================================
def mostrar_modulo_usuarios(supabase):
    st.header("👤 Gestión de Usuarios")
    
    # --- 🌟 CARGA DINÁMICA DE ROLES DESDE SUPABASE ---
    try:
        res_roles = supabase.table("roles").select("id, nombre_rol").execute()
        # Creamos el diccionario leyendo directamente tu base de datos: {1: 'SUPER_ADMIN', 2: 'GESTOR_ESPAÑA', ...}
        DICCIONARIO_ROLES = {rol['id']: rol['nombre_rol'] for rol in res_roles.data}
    except Exception as e:
        st.error(f"Error al cargar roles: {e}")
        DICCIONARIO_ROLES = {} # Evita que se rompa si falla la conexión
        
    # --- CARGA DE DATOS DE USUARIOS ---
    try:
        res = supabase.table("usuarios").select("id, nombre, email, moneda, id_rol").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        df_raw = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["📋 Directorio", "➕ Nuevo Usuario", "⚙️ Gestionar"])

    # --- TAB 1: REPORTE Y VISTA ---
    with tab1:
        if not df_raw.empty:
            # Mostramos la tabla con los nombres de roles en lugar de números
            df_ver = df_raw.copy()
            df_ver['Rol'] = df_ver['id_rol'].map(DICCIONARIO_ROLES)
            
            # Limpiamos visualmente por si algún id_rol no existe en la tabla roles
            df_ver['Rol'] = df_ver['Rol'].fillna("DESCONOCIDO")
            
            st.dataframe(df_ver[["nombre", "email", "moneda", "Rol"]], use_container_width=True)
            
            # Botón PDF (Pasamos los datos y el diccionario)
            pdf_bytes = generar_pdf_usuarios(df_raw, DICCIONARIO_ROLES)
            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name="reporte_usuarios.pdf",
                mime="application/pdf"
            )
        else:
            st.info("No hay usuarios registrados aún.")

    # --- TAB 2: REGISTRO CON VALIDACIÓN ---
    with tab2:
        st.subheader("Crear nueva cuenta")
        # Sin 'clear_on_submit' para que no borre los datos si hay error de validación
        with st.form("form_registro"):
            col1, col2 = st.columns(2)
            with col1:
                n_nombre = st.text_input("Nombre Completo")
                n_email = st.text_input("Correo Electrónico")
            with col2:
                n_pass = st.text_input("Contraseña Temporal", type="password")
                n_moneda = st.selectbox("Moneda", ["COP", "USD", "EUR", "ALL"])
            
            # Selector de Rol dinámico (lee de la base de datos)
            if DICCIONARIO_ROLES:
                opciones_rol = list(DICCIONARIO_ROLES.items()) 
                n_rol_sel = st.selectbox(
                    "Asignar Rol", 
                    options=opciones_rol, 
                    format_func=lambda x: x[1] # Muestra el nombre real de tu base de datos
                )
            else:
                st.warning("No hay roles configurados en la base de datos.")
                n_rol_sel = None

            if st.form_submit_button("🚀 Registrar Usuario"):
                if not n_rol_sel:
                    st.error("No se puede registrar usuarios sin roles disponibles.")
                else:
                    # Limpieza de datos
                    nombre_final = n_nombre.strip().upper()
                    email_final = n_email.strip().lower()

                    # Validaciones
                    if not n_nombre or not n_email or not n_pass:
                        st.error("⚠️ Los campos con (*) son obligatorios.")
                    elif "@" not in email_final or "." not in email_final:
                        st.error("❌ El correo electrónico no tiene un formato válido.")
                    elif len(n_pass) < 4:
                        st.error("❌ La contraseña debe tener al menos 4 caracteres.")
                    else:
                        # Inserción en Supabase
                        try:
                            nuevo_user = {
                                "nombre": nombre_final,
                                "email": email_final,
                                "password": n_pass,
                                "moneda": n_moneda,
                                "id_rol": n_rol_sel[0] # Guardamos el ID (número)
                            }
                            supabase.table("usuarios").insert(nuevo_user).execute()
                            st.success(f"✅ Usuario {nombre_final} creado correctamente.")
                            st.rerun() # Solo reinicia si tuvo éxito
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    # --- TAB 3: GESTIÓN (ELIMINAR) ---
    with tab3:
        st.subheader("Eliminar acceso")
        if not df_raw.empty:
            usuario_a_borrar = st.selectbox("Seleccione un usuario", df_raw['nombre'].tolist())
            id_borrar = df_raw[df_raw['nombre'] == usuario_a_borrar]['id'].values[0]
            
            if st.button(f"🗑️ Eliminar a {usuario_a_borrar}", type="primary"):
                supabase.table("usuarios").delete().eq("id", id_borrar).execute()
                st.warning("Usuario eliminado.")
                st.rerun()