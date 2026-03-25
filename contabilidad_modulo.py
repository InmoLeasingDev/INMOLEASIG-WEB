import streamlit as st
import pandas as pd

def mostrar_modulo_contabilidad(supabase):
    st.header("📖 Contabilidad y Finanzas")
    st.caption("Control de Facturación, Tesorería, Impuestos y Libros Contables.")

    # --- Identificar al usuario y su Entorno Operativo ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)
    
    # 🛡️ Entorno Operativo Estricto
    moneda_sesion = st.session_state.get("moneda_usuario", "EUR")

    # --- LAS 5 PESTAÑAS MAESTRAS DEL MÓDULO ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🧾 Facturación (CxC)", 
        "💸 Tesorería (CxP y Bancos)", 
        "📚 Libro Diario",
        "🏛️ Estados Financieros y Cierres"
    ])

    with tab1:
        st.subheader(f"Resumen Financiero ({moneda_sesion})")
        st.info("Aquí irán los gráficos de ingresos, gastos y cuentas por cobrar filtrados por tu entorno operativo.")

    with tab2:
        st.subheader("🧾 Emisión de Documentos y Cuentas por Cobrar")
        st.caption("Genera facturas a propietarios (honorarios) o clientes temporales.")
        
        try:
            # Filtramos propietarios por la moneda de la sesión
            res_prop = supabase.table("propietarios").select("id, nombre, identificacion").eq("estado", "ACTIVO").eq("moneda", moneda_sesion).execute()
            df_prop = pd.DataFrame(res_prop.data) if res_prop.data else pd.DataFrame()
        except:
            df_prop = pd.DataFrame()

        with st.expander("✨ Crear Nuevo Documento de Cobro", expanded=True):
            with st.form("form_facturacion_erp", clear_on_submit=True):
                st.markdown("#### 1. Datos del Cliente")
                c1, c2 = st.columns(2)
                tipo_cliente = c1.radio("Facturar a:", ["Propietario Registrado", "Cliente Manual (Temporal)"], horizontal=True)
                
                nombre_entidad = ""
                if tipo_cliente == "Propietario Registrado":
                    if not df_prop.empty:
                        opciones_prop = [f"{r['nombre']} (ID: {r['identificacion']})" for _, r in df_prop.iterrows()]
                        sel_prop = c2.selectbox("Selecciona el Propietario *", opciones_prop)
                        nombre_entidad = sel_prop.split(" (ID:")[0] 
                    else:
                        c2.warning(f"No hay propietarios activos en {moneda_sesion}.")
                else:
                    nombre_entidad = c2.text_input("Nombre del Cliente / Inquilino *", placeholder="Ej: Juan Pérez")

                st.markdown("#### 2. Datos del Documento")
                c3, c4, c5 = st.columns([2, 2, 1])
                tipo_doc = c3.selectbox("Tipo de Documento", ["CUENTA DE COBRO", "FACTURA", "RECIBO", "NOTA DE DÉBITO"])
                n_doc = c4.text_input("Número de Documento *", placeholder="Ej: FAC-001")
                f_emi = c5.date_input("Fecha Emisión")
                
                st.markdown("#### 3. Conceptos a Cobrar")
                col_d1, col_d2, col_d3 = st.columns([3, 1, 1])
                concepto_1 = col_d1.text_input("Concepto Principal *", placeholder="Ej: Honorarios de Gestión Mes Marzo")
                cant_1 = col_d2.number_input("Cantidad", value=1.0, min_value=0.1)
                simbolo = "€" if moneda_sesion == "EUR" else "$"
                precio_1 = col_d3.number_input(f"Precio Unitario ({simbolo}) *", value=0.0, min_value=0.0, step=10.0)
                
                st.markdown("---")
                if st.form_submit_button("🚀 Emitir Documento y Registrar Deuda"):
                    if nombre_entidad and n_doc and concepto_1 and precio_1 > 0:
                        total_final = cant_1 * precio_1
                        try:
                            # 1. Guardar el Documento (Con sello de Moneda)
                            doc_data = {
                                "tipo_documento": tipo_doc, 
                                "numero_documento": n_doc.strip().upper(),
                                "fecha_emision": str(f_emi), 
                                "nombre_entidad": nombre_entidad.upper(),
                                "total": float(total_final), 
                                "moneda": moneda_sesion,      # <-- BLINDAJE
                                "estado": "PENDIENTE"
                            }
                            res_doc = supabase.table("fin_documentos").insert(doc_data).execute()
                            
                            # 2. Registrar en Cuentas por Cobrar (Con sello de Moneda)
                            cxc_data = {
                                "id_documento": res_doc.data[0]['id'], 
                                "nombre_entidad": nombre_entidad.upper(),
                                "monto_total": float(total_final), 
                                "saldo_pendiente": float(total_final),
                                "moneda": moneda_sesion,      # <-- BLINDAJE
                                "estado": "PENDIENTE"
                            }
                            supabase.table("fin_cuentas_cobrar").insert(cxc_data).execute()
                            
                            # (Opcional en el futuro: Disparar el asiento contable aquí)
                            
                            st.success(f"✅ Documento {n_doc} emitido por {simbolo} {total_final:,.2f}. Registrado en Cartera ({moneda_sesion}).")
                        except Exception as e:
                            st.error(f"❌ Error en la base de datos: {e}")
                    else:
                        st.warning("⚠️ Rellena todos los campos obligatorios (*) y usa un precio mayor a 0.")

    with tab3:
        st.subheader("Gestión de Bancos y Pagos a Proveedores/Propietarios")
        st.info(f"Aquí registraremos salidas de dinero, comisiones y conciliación para el entorno {moneda_sesion}.")

    with tab4:
        st.subheader("📚 Libro Diario (Asientos Contables)")
        st.caption(f"Auditoría en tiempo real de Débitos y Créditos (Entorno: {moneda_sesion}).")
        
        c1, c2 = st.columns([1, 3])
        mes_filtro = c1.selectbox("Filtrar por Mes:", ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"], index=0)
        st.markdown("---")
        
        try:
            # Filtramos los asientos para que solo muestre los de la moneda de la sesión
            res_asientos = supabase.table("fin_asientos").select("id, numero_asiento, fecha_contable, descripcion, origen, estado, moneda").eq("moneda", moneda_sesion).order("fecha_contable", desc=True).execute()
            df_asientos = pd.DataFrame(res_asientos.data) if res_asientos.data else pd.DataFrame()
        except:
            df_asientos = pd.DataFrame()
            
        if not df_asientos.empty:
            if mes_filtro != "Todos":
                num_mes = mes_filtro.split(" - ")[0]
                # Filtramos por mes asegurándonos de que la fecha existe
                df_asientos = df_asientos[df_asientos['fecha_contable'].astype(str).str[5:7] == num_mes]
                
            if not df_asientos.empty:
                for _, asiento in df_asientos.iterrows():
                    with st.expander(f"🧾 Asiento ID: {asiento['id']} | Fecha: {asiento['fecha_contable']} | {asiento['descripcion']}"):
                        try:
                            res_ap = supabase.table("fin_apuntes").select("id_cuenta_contable, debito, credito").eq("id_asiento", int(asiento['id'])).execute()
                            df_ap = pd.DataFrame(res_ap.data) if res_ap.data else pd.DataFrame()
                        except:
                            df_ap = pd.DataFrame()
                            
                        if not df_ap.empty:
                            # Solo traemos las cuentas de esta moneda para hacer el cruce
                            res_ctas = supabase.table("fin_cuentas_contables").select("id, codigo, nombre").eq("moneda", moneda_sesion).execute()
                            df_ctas = pd.DataFrame(res_ctas.data)
                            
                            df_ap = df_ap.merge(df_ctas, left_on='id_cuenta_contable', right_on='id', how='left')
                            # Si no encuentra la cuenta (por error de datos viejos), pone "DESCONOCIDA"
                            df_ap['CUENTA'] = df_ap['codigo'].fillna("???") + " - " + df_ap['nombre'].fillna("CUENTA DESCONOCIDA")
                            
                            df_view = df_ap[['CUENTA', 'debito', 'credito']].copy()
                            simbolo_view = "€" if moneda_sesion == "EUR" else "$"
                            
                            df_view['DEBE'] = df_view['debito'].apply(lambda x: f"{simbolo_view} {float(x):,.2f}" if float(x) > 0 else "")
                            df_view['HABER'] = df_view['credito'].apply(lambda x: f"{simbolo_view} {float(x):,.2f}" if float(x) > 0 else "")
                            
                            st.dataframe(df_view[['CUENTA', 'DEBE', 'HABER']], use_container_width=True, hide_index=True)
                            
                            tot_d, tot_c = df_ap['debito'].sum(), df_ap['credito'].sum()
                            if tot_d == tot_c: 
                                st.success(f"✅ Partida Doble Cuadrada: {simbolo_view} {tot_d:,.2f}")
                            else: 
                                st.error(f"❌ Descuadre: DEBE ({simbolo_view} {tot_d:,.2f}) vs HABER ({simbolo_view} {tot_c:,.2f})")
                        else:
                            st.info("Este asiento no tiene líneas de apunte.")
            else:
                st.info(f"No hay asientos registrados en el mes seleccionado para {moneda_sesion}.")
        else:
            st.info(f"ℹ️ El Libro Diario de {moneda_sesion} está vacío. Aún no se han generado asientos contables.")

    # --- LA NUEVA PESTAÑA PARA EL CFO ---
    with tab5:
        st.subheader("Reportes Oficiales y Cierres de Periodo")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📄 Estados Financieros")
            st.button("⚖️ Generar Balance General", disabled=True)
            st.button("📈 Generar Estado de Resultados (P&G)", disabled=True)
            
        with c2:
            st.markdown("#### 🔒 Cierres Contables")
            st.button("🔐 Ejecutar Cierre de Mes", disabled=True)
            st.button("📆 Ejecutar Cierre de Año", disabled=True)
            st.info("Un mes cerrado bloqueará cualquier modificación pasada para proteger la contabilidad.")