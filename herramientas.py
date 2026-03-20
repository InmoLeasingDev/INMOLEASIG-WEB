import zoneinfo
from datetime import datetime

def log_accion(supabase, usuario, accion, detalle):
    """
    Subrutina centralizada para registrar logs de actividad.
    Se llama desde cualquier módulo del sistema.
    """
    try:
        # Filtro Inteligente: extrae el nombre si mandan el diccionario completo
        if isinstance(usuario, dict):
            nombre_limpio = usuario.get("nombre", "Usuario Desconocido")
        else:
            nombre_limpio = str(usuario)

        # Hora exacta de Madrid
        zona_madrid = zoneinfo.ZoneInfo("Europe/Madrid")
        hora_exacta = datetime.now(zona_madrid).strftime("%Y-%m-%d %H:%M:%S")
        
        # Insertar en la Base de Datos
        supabase.table("logs_actividad").insert({
            "usuario": nombre_limpio, 
            "accion": accion, 
            "detalle": detalle,
            "fecha": hora_exacta
        }).execute()
    except Exception as e:
        print(f"Error al registrar log: {e}")