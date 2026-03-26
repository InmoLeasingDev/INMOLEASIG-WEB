import streamlit as st
import pandas as pd

def mostrar_modulo_bancos(supabase):
    st.header("🏦 Gestión de Bancos y Tesorería")
    st.caption("Control de Cuentas, Extractos, Notas Bancarias y Conciliación.")

    # --- Identificar al usuario ---
    var_sesion = st.session_state.get("usuario_actual", st.session_state.get("usuario", "ADMINISTRADOR"))
    usuario_actual = var_sesion.get("nombre", "ADMINISTRADOR") if isinstance(var_sesion, dict) else str(var_sesion)

    # --- LAS 3 PESTAÑAS MAESTRAS DE TESORERÍA ---
    tab1, tab2, tab3 = st.tabs([
        "💳 Mis Cuentas Bancarias", 
        "📝 Extractos y Notas (ND/NC)", 
        "⚖️ Conciliación Bancaria"
    ])

    with tab1:
        st.subheader("🏦 Cuentas Bancarias de la Empresa")
        
        # --- LECTURA DE CUENTAS BANCARIAS ---
        try:
            res_bancos = supabase.table("fin_cuentas_bancarias").select("*").eq("estado", "ACTIVO").execute()
            df_bancos = pd.DataFrame(res_bancos.data) if res_bancos.data else pd.DataFrame()
        except Exception as e:
            df_bancos = pd.DataFrame()
            st.error(f"Error al conectar con tesorería: {e}")

        # --- CUADRÍCULA VISUAL ---
        if not df_bancos.empty:
            df_bancos_view = df_bancos[['nombre_interno', 'banco', 'iban', 'moneda', 'saldo_actual']].copy()
            df_bancos_view.columns = ['CUENTA (INTERNO)', 'ENTIDAD', 'IBAN', 'MONEDA', 'SALDO CONTABLE']
            
            df_bancos_view['SALDO CONTABLE'] = df_bancos_view.apply(
                lambda row: f"{'€' if row['MONEDA'] == 'EUR' else '$'} {float(row['SALDO CONTABLE']):,.2f}", axis=1
            )
            
            st.dataframe(df_bancos_view, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No hay cuentas bancarias registradas. Añade la primera.")

        st.markdown("---")
        
        # ---- FORMULARIO PARA AÑADIR NUEVA CUENTA ----
        with st.expander("➕ Añadir Nueva Cuenta Bancaria", expanded=df_bancos.empty):
            with st.form("form_nuevo_banco", clear_on_submit=True):
                c1, c2 = st.columns(2)
                b_nombre = c1.text_input("Nombre Interno *", placeholder="Ej: BBVA Operaciones")
                b_entidad = c2.text_input("Entidad Bancaria *", placeholder="Ej: BBVA")
              
                
                c3, c4, c5, c6 = st.columns([2, 1, 1.5, 1])
                b_iban = c3.text_input("IBAN / Número de Cuenta *")
                b_moneda = c4.selectbox("Moneda", ["EUR", "COP"])
                b_fecha_ap = c5.date_input("Fecha Saldo Inicial")
                b_saldo = c6.number_input("Saldo Inicial", min_value=0.0, step=50.0)
                st.caption("💡 Esta cuenta se vinculará automáticamente a la cuenta contable NIIF '1110 - Bancos Nacionales'.")
                
                if st.form_submit_button("💾 Registrar Banco"):
                    if b_nombre and b_entidad and b_iban:
                        try:
                            res_cta = supabase.table("fin_cuentas_contables").select("id").eq("codigo", "1110").execute()
                            id_cta_banco = res_cta.data[0]['id'] if res_cta.data else None
                            
                            datos_banco = {
                                "nombre_interno": b_nombre.strip().upper(),
                                "banco": b_entidad.strip().upper(),
                                "iban": b_iban.strip().upper().replace(" ", ""),
                                "moneda": b_moneda,
                                "saldo_actual": float(b_saldo),
                                "fecha_apertura": str(b_fecha_ap), # <-- LÍNEA NUEVA
                                "id_cuenta_contable": id_cta_banco
                            }
                            # 1. Guardar la cuenta bancaria y capturar su ID
                            res_insert = supabase.table("fin_cuentas_bancarias").insert(datos_banco).execute()
                            nueva_cuenta_id = res_insert.data[0]['id']

                            # 2. Registrar el "Movimiento Cero" (El ingreso del saldo inicial)
                            if float(b_saldo) > 0:
                                mov_inicial = {
                                    "id_cuenta_bancaria": nueva_cuenta_id,
                                    "fecha_movimiento": str(b_fecha_ap),
                                    "tipo": "INGRESO",
                                    "monto": float(b_saldo),
                                    "concepto": "SALDO INICIAL - APERTURA ERP",
                                    "estado_conciliacion": "CONCILIADO"
                                }
                                supabase.table("fin_movimientos_banco").insert(mov_inicial).execute()

                            st.success("✅ Cuenta registrada y Movimiento Inicial asentado en Tesorería.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar: {e}")
                    else:
                        st.warning("⚠️ Rellena los campos obligatorios (*).")

    
    with tab2:
        st.subheader("📝 Extractos y Auditoría de Movimientos")
        st.caption("Consulta todos los ingresos y egresos registrados en cada cuenta.")
        
        # 1. Selector de Cuenta
        try:
            res_cta_ext = supabase.table("fin_cuentas_bancarias").select("id, nombre_interno, banco, moneda, saldo_actual").eq("estado", "ACTIVO").execute()
            df_cta_ext = pd.DataFrame(res_cta_ext.data) if res_cta_ext.data else pd.DataFrame()
        except:
            df_cta_ext = pd.DataFrame()
            
        if not df_cta_ext.empty:
            opciones_bancos = [f"{r['nombre_interno']} ({r['banco']}) - Saldo: {r['saldo_actual']} {r['moneda']}" for _, r in df_cta_ext.iterrows()]
            banco_seleccionado = st.selectbox("Selecciona la cuenta a auditar:", opciones_bancos)
            
            if banco_seleccionado:
                # Extraemos el ID de la cuenta elegida
                idx_b = opciones_bancos.index(banco_seleccionado)
                id_banco_elegido = df_cta_ext.iloc[idx_b]['id']
                simbolo_moneda = "€" if df_cta_ext.iloc[idx_b]['moneda'] == "EUR" else "$"
                
                # 2. Consultar Movimientos
                st.markdown("---")
                try:
                    # Traemos los movimientos ordenados por fecha de más reciente a más antiguo
                    res_movs = supabase.table("fin_movimientos_banco").select("*").eq("id_cuenta_bancaria", int(id_banco_elegido)).order("fecha_movimiento", desc=True).execute()
                    df_movs = pd.DataFrame(res_movs.data) if res_movs.data else pd.DataFrame()
                except Exception as e:
                    df_movs = pd.DataFrame()
                    st.error(f"Error al cargar extractos: {e}")
                    
                if not df_movs.empty:
                    # Preparar vista para el usuario
                    df_movs_view = df_movs[['fecha_movimiento', 'concepto', 'tipo', 'monto', 'estado_conciliacion']].copy()
                    
                    # Formatear el monto con el símbolo de la moneda y color visual
                    def formatear_monto_tipo(row):
                        monto_str = f"{simbolo_moneda} {float(row['monto']):,.2f}"
                        if row['tipo'] == 'INGRESO': return f"🟢 +{monto_str}"
                        elif row['tipo'] == 'EGRESO': return f"🔴 -{monto_str}"
                        return monto_str
                        
                    df_movs_view['VALOR'] = df_movs_view.apply(formatear_monto_tipo, axis=1)
                    
                    # Limpiar columnas finales
                    df_movs_view.rename(columns={
                        'fecha_movimiento': 'FECHA', 
                        'concepto': 'CONCEPTO / DESCRIPCIÓN',
                        'estado_conciliacion': 'ESTADO'
                    }, inplace=True)
                    
                    # Mostramos solo las columnas relevantes
                    st.dataframe(df_movs_view[['FECHA', 'CONCEPTO / DESCRIPCIÓN', 'VALOR', 'ESTADO']], use_container_width=True, hide_index=True)
                else:
                    st.info("No hay movimientos registrados en esta cuenta bancaria.")
        else:
            st.warning("No hay cuentas bancarias creadas. Ve a la primera pestaña.")
    with tab3:
        st.subheader("Conciliación Bancaria Mensual")
        st.info("Aquí cruzaremos los movimientos del banco con las facturas cobradas/pagadas (Módulo Contabilidad).")