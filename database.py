import json
import os
import uuid
from datetime import datetime, timedelta
import calendar

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memoria_caises.json")

DEFAULT_UNIDADES = [
    "CAISES Guanajuato",
    "UMAPS Puentecillas",
    "UMAPS Yerbabuena",
    "UMAPS El Cambio",
    "UMAPS Marfil",
    "UMAPS Santa Teresa"
]

DEFAULT_CATEGORIAS = [
    "Informes y Reportes",
    "Inventarios y Medicamentos",
    "Supervisión y Auditoría",
    "Cadena de Frío",
    "Vacunación",
    "Mantenimiento",
    "Personal / General"
]

DEFAULT_CONFIG = {
    "pin_acceso": "2602",
    "telegram_token": "",
    "telegram_chat_id": "",
    "hora_notificacion_diaria": "08:00",
    "dias_aviso_defecto": 5,
    "recordatorios_por_dia_defecto": 1
}

FRECUENCIAS = {
    "unica": "Única vez",
    "diaria": "Diaria",
    "semanal": "Semanal",
    "quincenal": "Quincenal",
    "mensual": "Mensual",
    "bimensual": "Bimensual (cada 2 meses)",
    "trimestral": "Trimestral (cada 3 meses)",
    "cuatrimestral": "Cuatrimestral (cada 4 meses)",
    "semestral": "Semestral (cada 6 meses)",
    "anual": "Anual (cada año)"
}


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day).date()


def calcular_siguiente_fecha(fecha_str, frecuencia):
    try:
        dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except Exception:
        dt = datetime.now().date()

    if frecuencia == "diaria":
        return str(dt + timedelta(days=1))
    elif frecuencia == "semanal":
        return str(dt + timedelta(days=7))
    elif frecuencia == "quincenal":
        return str(dt + timedelta(days=15))
    elif frecuencia == "mensual":
        return str(add_months(dt, 1))
    elif frecuencia == "bimensual":
        return str(add_months(dt, 2))
    elif frecuencia == "trimestral":
        return str(add_months(dt, 3))
    elif frecuencia == "cuatrimestral":
        return str(add_months(dt, 4))
    elif frecuencia == "semestral":
        return str(add_months(dt, 6))
    elif frecuencia == "anual":
        return str(add_months(dt, 12))
    else:
        return str(dt)


class DatabaseManager:
    def __init__(self, file_path=DATA_FILE):
        self.file_path = file_path
        self._inicializar()

    def _inicializar(self):
        if not os.path.exists(self.file_path):
            datos_iniciales = {
                "unidades": DEFAULT_UNIDADES,
                "categorias": DEFAULT_CATEGORIAS,
                "configuracion": DEFAULT_CONFIG,
                "tareas": [],
                "historial": []
            }
            self.guardar_datos(datos_iniciales)
        else:
            # Migration check
            datos = self.cargar_datos()
            modificado = False
            if "unidades" not in datos or not datos["unidades"]:
                datos["unidades"] = DEFAULT_UNIDADES
                modificado = True
            if "categorias" not in datos or not datos["categorias"]:
                datos["categorias"] = DEFAULT_CATEGORIAS
                modificado = True
            if "configuracion" not in datos:
                datos["configuracion"] = DEFAULT_CONFIG
                modificado = True
            if "historial" not in datos:
                datos["historial"] = []
                modificado = True
            
            # Migración de tareas antiguas
            for t in datos.get("tareas", []):
                if "frecuencia" not in t:
                    t["frecuencia"] = "unica"
                    modificado = True
                if "tipo_destino" not in t:
                    t["tipo_destino"] = "personal" if t.get("unidad") == "Ninguna (Tarea General)" else "unidad"
                    modificado = True
                if "dias_aviso" not in t:
                    t["dias_aviso"] = 5
                    modificado = True
                if "categoria" not in t:
                    t["categoria"] = "General"
                    modificado = True
                if "descripcion" not in t:
                    t["descripcion"] = ""
                    modificado = True
                if "hora_entrega" not in t:
                    t["hora_entrega"] = "09:00"
                    modificado = True
                if "recordatorios_por_dia" not in t:
                    t["recordatorios_por_dia"] = 1
                    modificado = True

            if modificado:
                self.guardar_datos(datos)

    def cargar_datos(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "unidades": DEFAULT_UNIDADES,
                "categorias": DEFAULT_CATEGORIAS,
                "configuracion": DEFAULT_CONFIG,
                "tareas": [],
                "historial": []
            }

    def guardar_datos(self, datos):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    # --- UNIDADES ---
    def obtener_unidades(self):
        return self.cargar_datos().get("unidades", DEFAULT_UNIDADES)

    def agregar_unidad(self, nombre):
        nombre = nombre.strip()
        if not nombre:
            return False, "El nombre de la unidad no puede estar vacío."
        datos = self.cargar_datos()
        if nombre in datos["unidades"]:
            return False, "La unidad ya existe."
        datos["unidades"].append(nombre)
        self.guardar_datos(datos)
        return True, "Unidad agregada correctamente."

    def eliminar_unidad(self, nombre):
        datos = self.cargar_datos()
        if nombre in datos["unidades"]:
            datos["unidades"].remove(nombre)
            self.guardar_datos(datos)
            return True, "Unidad eliminada."
        return False, "Unidad no encontrada."

    def editar_unidad(self, nombre_anterior, nuevo_nombre):
        nombre_anterior = nombre_anterior.strip()
        nuevo_nombre = nuevo_nombre.strip()
        if not nuevo_nombre:
            return False, "El nuevo nombre de la unidad no puede estar vacío."
        datos = self.cargar_datos()
        if nombre_anterior not in datos["unidades"]:
            return False, "Unidad original no encontrada."
        if nuevo_nombre != nombre_anterior and nuevo_nombre in datos["unidades"]:
            return False, "Ya existe una unidad con ese nombre."

        idx = datos["unidades"].index(nombre_anterior)
        datos["unidades"][idx] = nuevo_nombre

        # Actualizar tareas existentes asignadas a esta unidad
        for t in datos.get("tareas", []):
            if t.get("unidad") == nombre_anterior:
                t["unidad"] = nuevo_nombre

        # Actualizar historial
        for h in datos.get("historial", []):
            if h.get("unidad") == nombre_anterior:
                h["unidad"] = nuevo_nombre

        self.guardar_datos(datos)
        return True, f"Unidad renombrada a '{nuevo_nombre}'."

    # --- CATEGORÍAS ---
    def obtener_categorias(self):
        return self.cargar_datos().get("categorias", DEFAULT_CATEGORIAS)

    def agregar_categoria(self, nombre):
        nombre = nombre.strip()
        if not nombre:
            return False, "El nombre no puede estar vacío."
        datos = self.cargar_datos()
        if nombre in datos["categorias"]:
            return False, "La categoría ya existe."
        datos["categorias"].append(nombre)
        self.guardar_datos(datos)
        return True, "Categoría agregada."

    def eliminar_categoria(self, nombre):
        datos = self.cargar_datos()
        if nombre in datos["categorias"]:
            datos["categorias"].remove(nombre)
            self.guardar_datos(datos)
            return True, "Categoría eliminada."
        return False, "Categoría no encontrada."

    def editar_categoria(self, nombre_anterior, nuevo_nombre):
        nombre_anterior = nombre_anterior.strip()
        nuevo_nombre = nuevo_nombre.strip()
        if not nuevo_nombre:
            return False, "El nuevo nombre no puede estar vacío."
        datos = self.cargar_datos()
        if nombre_anterior not in datos["categorias"]:
            return False, "Categoría original no encontrada."
        if nuevo_nombre != nombre_anterior and nuevo_nombre in datos["categorias"]:
            return False, "Ya existe una categoría con ese nombre."

        idx = datos["categorias"].index(nombre_anterior)
        datos["categorias"][idx] = nuevo_nombre

        # Actualizar tareas existentes con esta categoría
        for t in datos.get("tareas", []):
            if t.get("categoria") == nombre_anterior:
                t["categoria"] = nuevo_nombre

        # Actualizar historial
        for h in datos.get("historial", []):
            if h.get("categoria") == nombre_anterior:
                h["categoria"] = nuevo_nombre

        self.guardar_datos(datos)
        return True, f"Categoría renombrada a '{nuevo_nombre}'."

    # --- CONFIGURACIÓN ---
    def obtener_configuracion(self):
        datos = self.cargar_datos()
        config = datos.get("configuracion", DEFAULT_CONFIG)
        if not config.get("pin_acceso"):
            config["pin_acceso"] = "2602"
        if not config.get("telegram_token"):
            config["telegram_token"] = os.getenv("TELEGRAM_TOKEN", "")
        if not config.get("telegram_chat_id"):
            config["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
        return config

    def validar_pin(self, pin_ingresado):
        config = self.obtener_configuracion()
        pin_correcto = str(config.get("pin_acceso", "2602")).strip()
        return str(pin_ingresado).strip() == pin_correcto

    def actualizar_configuracion(self, nueva_config):
        datos = self.cargar_datos()
        datos["configuracion"].update(nueva_config)
        self.guardar_datos(datos)
        return True, "Configuración actualizada."

    # --- TAREAS ---
    def obtener_tareas(self, filtro_estado=None, filtro_tipo=None, filtro_unidad=None, filtro_frecuencia=None):
        datos = self.cargar_datos()
        tareas = datos.get("tareas", [])
        resultado = []
        now = datetime.now()
        hoy = now.date()

        for t in tareas:
            # Calcular estado en tiempo real (pendiente, vencida, por_vencer, completada)
            if t.get("completada", False):
                t["estado_calculado"] = "completada"
            else:
                try:
                    fecha_ent = datetime.strptime(t["fecha_entrega"], "%Y-%m-%d").date()
                    fecha_ini = datetime.strptime(t["fecha_inicio"], "%Y-%m-%d").date()
                    if hoy > fecha_ent:
                        t["estado_calculado"] = "vencida"
                    elif hoy >= fecha_ini:
                        t["estado_calculado"] = "por_vencer"
                    else:
                        t["estado_calculado"] = "pendiente"
                except Exception:
                    t["estado_calculado"] = "pendiente"

            # Filtros
            if filtro_estado:
                if filtro_estado == "activas" and t["completada"]:
                    continue
                elif filtro_estado == "completadas" and not t["completada"]:
                    continue
                elif filtro_estado in ["vencida", "por_vencer", "pendiente"] and t["estado_calculado"] != filtro_estado:
                    continue

            if filtro_tipo and t.get("tipo_destino") != filtro_tipo:
                continue

            if filtro_unidad and filtro_unidad != "Todas" and t.get("unidad") != filtro_unidad:
                continue

            if filtro_frecuencia and filtro_frecuencia != "Todas" and t.get("frecuencia") != filtro_frecuencia:
                continue

            resultado.append(t)

        return resultado

    def crear_tarea_lote(self, titulo, descripcion, tipo_destino, unidades, categoria, frecuencia, fecha_entrega, hora_entrega, dias_aviso, recordatorios_por_dia, recordatorios):
        datos = self.cargar_datos()
        hoy = datetime.now().date()
        try:
            f_entrega = datetime.strptime(fecha_entrega, "%Y-%m-%d").date()
        except Exception:
            f_entrega = hoy + timedelta(days=7)
            fecha_entrega = str(f_entrega)

        hora_entrega = hora_entrega.strip() if hora_entrega else "09:00"
        dias_aviso = int(dias_aviso) if str(dias_aviso).isdigit() else 5
        recordatorios_por_dia = int(recordatorios_por_dia) if str(recordatorios_por_dia).isdigit() else 1
        f_inicio = f_entrega - timedelta(days=dias_aviso)

        if not unidades or tipo_destino == "personal":
            unidades = ["Personal / General"]

        tareas_creadas = []
        for u in unidades:
            tarea_id = str(uuid.uuid4())[:8]
            nueva = {
                "id": tarea_id,
                "tarea": titulo.strip(),
                "descripcion": descripcion.strip(),
                "tipo_destino": tipo_destino, # 'unidad' o 'personal'
                "unidad": u,
                "categoria": categoria,
                "frecuencia": frecuencia,
                "fecha_inicio": str(f_inicio),
                "fecha_entrega": str(fecha_entrega),
                "hora_entrega": hora_entrega,
                "dias_aviso": dias_aviso,
                "recordatorios_por_dia": recordatorios_por_dia,
                "recordatorios": recordatorios if recordatorios else ["Telegram", "Visual en App"],
                "completada": False,
                "creada_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            datos["tareas"].append(nueva)
            tareas_creadas.append(nueva)

        self.guardar_datos(datos)
        return tareas_creadas

    def completar_tarea(self, tarea_id, notas=""):
        datos = self.cargar_datos()
        tarea_encontrada = None
        index_encontrado = -1

        for i, t in enumerate(datos["tareas"]):
            if t["id"] == tarea_id:
                tarea_encontrada = t
                index_encontrado = i
                break

        if not tarea_encontrada:
            return False, "Tarea no encontrada."

        # Registrar en Historial
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        registro_historial = {
            "id": str(uuid.uuid4())[:8],
            "tarea_id": tarea_id,
            "tarea": tarea_encontrada["tarea"],
            "unidad": tarea_encontrada["unidad"],
            "categoria": tarea_encontrada["categoria"],
            "frecuencia": tarea_encontrada["frecuencia"],
            "fecha_entrega_original": f"{tarea_encontrada['fecha_entrega']} {tarea_encontrada.get('hora_entrega', '')}",
            "fecha_cumplimiento": fecha_actual,
            "notas": notas
        }
        datos["historial"].append(registro_historial)

        frecuencia = tarea_encontrada.get("frecuencia", "unica")

        if frecuencia == "unica":
            # Marcar completada permanentemente
            datos["tareas"][index_encontrado]["completada"] = True
            datos["tareas"][index_encontrado]["fecha_completada"] = fecha_actual
            mensaje = f"✅ Tarea '{tarea_encontrada['tarea']}' completada y archivada en el historial."
        else:
            # Recurrente: calcular la siguiente fecha limite y reiniciar estado
            fecha_entrega_actual = tarea_encontrada["fecha_entrega"]
            siguiente_fecha_entrega = calcular_siguiente_fecha(fecha_entrega_actual, frecuencia)
            
            dias_aviso = tarea_encontrada.get("dias_aviso", 5)
            siguiente_dt_entrega = datetime.strptime(siguiente_fecha_entrega, "%Y-%m-%d").date()
            siguiente_fecha_inicio = str(siguiente_dt_entrega - timedelta(days=dias_aviso))

            datos["tareas"][index_encontrado]["fecha_entrega"] = siguiente_fecha_entrega
            datos["tareas"][index_encontrado]["fecha_inicio"] = siguiente_fecha_inicio
            datos["tareas"][index_encontrado]["completada"] = False
            datos["tareas"][index_encontrado]["ultima_completada"] = fecha_actual

            freq_nombre = FRECUENCIAS.get(frecuencia, frecuencia)
            mensaje = f"✅ Tarea realizada. Como es recurrente ({freq_nombre}), se ha reprogramado automáticamente para el **{siguiente_fecha_entrega}** a las {tarea_encontrada.get('hora_entrega', '09:00')} hrs."

        self.guardar_datos(datos)
        return True, mensaje

    def finalizar_serie(self, tarea_id):
        """Finaliza permanentemente una tarea recurrente cancelando repeticiones futuras."""
        datos = self.cargar_datos()
        for t in datos["tareas"]:
            if t["id"] == tarea_id:
                t["completada"] = True
                t["frecuencia"] = "unica" # Convert to one-time to prevent future auto-renews
                t["fecha_completada"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                registro_historial = {
                    "id": str(uuid.uuid4())[:8],
                    "tarea_id": tarea_id,
                    "tarea": t["tarea"],
                    "unidad": t["unidad"],
                    "categoria": t["categoria"],
                    "frecuencia": "Serie Cancelada",
                    "fecha_entrega_original": f"{t['fecha_entrega']} {t.get('hora_entrega', '')}",
                    "fecha_cumplimiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "notas": "Serie recurrente finalizada y cancelada por el usuario"
                }
                datos["historial"].append(registro_historial)
                self.guardar_datos(datos)
                return True, f"🛑 Serie recurrente para '{t['tarea']}' finalizada. No se volverá a reprogramar."

        return False, "Tarea no encontrada."

    def postergar_tarea(self, tarea_id, dias=3):
        datos = self.cargar_datos()
        for t in datos["tareas"]:
            if t["id"] == tarea_id:
                try:
                    dt_entrega = datetime.strptime(t["fecha_entrega"], "%Y-%m-%d").date()
                except Exception:
                    dt_entrega = datetime.now().date()
                nueva_entrega = dt_entrega + timedelta(days=dias)
                dias_aviso = t.get("dias_aviso", 5)
                nueva_inicio = nueva_entrega - timedelta(days=dias_aviso)

                t["fecha_entrega"] = str(nueva_entrega)
                t["fecha_inicio"] = str(nueva_inicio)
                self.guardar_datos(datos)
                return True, f"Tarea postergada {dias} días (Nueva fecha: {nueva_entrega})."
        return False, "Tarea no encontrada."

    def editar_tarea(self, tarea_id, nuevos_datos):
        datos = self.cargar_datos()
        for t in datos["tareas"]:
            if t["id"] == tarea_id:
                if "tarea" in nuevos_datos:
                    t["tarea"] = nuevos_datos["tarea"].strip()
                if "descripcion" in nuevos_datos:
                    t["descripcion"] = nuevos_datos["descripcion"].strip()
                if "unidad" in nuevos_datos:
                    t["unidad"] = nuevos_datos["unidad"]
                if "categoria" in nuevos_datos:
                    t["categoria"] = nuevos_datos["categoria"]
                if "frecuencia" in nuevos_datos:
                    t["frecuencia"] = nuevos_datos["frecuencia"]
                if "fecha_entrega" in nuevos_datos:
                    t["fecha_entrega"] = nuevos_datos["fecha_entrega"]
                if "hora_entrega" in nuevos_datos:
                    t["hora_entrega"] = nuevos_datos["hora_entrega"]
                if "dias_aviso" in nuevos_datos:
                    t["dias_aviso"] = int(nuevos_datos["dias_aviso"])
                if "recordatorios_por_dia" in nuevos_datos:
                    t["recordatorios_por_dia"] = int(nuevos_datos["recordatorios_por_dia"])
                
                # Recalcular fecha de inicio
                try:
                    dt_e = datetime.strptime(t["fecha_entrega"], "%Y-%m-%d").date()
                    t["fecha_inicio"] = str(dt_e - timedelta(days=t["dias_aviso"]))
                except Exception:
                    pass

                self.guardar_datos(datos)
                return True, "Tarea actualizada correctamente."
        return False, "Tarea no encontrada."

    def eliminar_tarea(self, tarea_id):
        datos = self.cargar_datos()
        original_count = len(datos["tareas"])
        datos["tareas"] = [t for t in datos["tareas"] if t["id"] != tarea_id]
        if len(datos["tareas"]) < original_count:
            self.guardar_datos(datos)
            return True, "Tarea eliminada definitivamente."
        return False, "Tarea no encontrada."

    # --- HISTORIAL ---
    def obtener_historial(self):
        return self.cargar_datos().get("historial", [])

    def limpiar_historial(self):
        datos = self.cargar_datos()
        datos["historial"] = []
        datos["tareas"] = [t for t in datos["tareas"] if not t.get("completada", False)]
        self.guardar_datos(datos)
        return True, "Historial vaciado."

    # --- ESTADÍSTICAS DEL DASHBOARD ---
    def obtener_estadisticas(self):
        datos = self.cargar_datos()
        tareas = self.obtener_tareas()
        historial = datos.get("historial", [])
        
        total_activas = len([t for t in tareas if not t.get("completada", False)])
        vencidas = len([t for t in tareas if t.get("estado_calculado") == "vencida"])
        por_vencer = len([t for t in tareas if t.get("estado_calculado") == "por_vencer"])
        en_tiempo = len([t for t in tareas if t.get("estado_calculado") == "pendiente"])
        total_cumplidas = len(historial) + len([t for t in tareas if t.get("completada", False)])

        por_unidad = {}
        for u in datos.get("unidades", DEFAULT_UNIDADES) + ["Personal / General"]:
            por_unidad[u] = {"pendientes": 0, "completadas": 0}

        for t in tareas:
            u = t.get("unidad", "Personal / General")
            if u not in por_unidad:
                por_unidad[u] = {"pendientes": 0, "completadas": 0}
            if t.get("completada", False):
                por_unidad[u]["completadas"] += 1
            else:
                por_unidad[u]["pendientes"] += 1

        for h in historial:
            u = h.get("unidad", "Personal / General")
            if u not in por_unidad:
                por_unidad[u] = {"pendientes": 0, "completadas": 0}
            por_unidad[u]["completadas"] += 1

        return {
            "total_activas": total_activas,
            "vencidas": vencidas,
            "por_vencer": por_vencer,
            "en_tiempo": en_tiempo,
            "total_cumplidas": total_cumplidas,
            "por_unidad": por_unidad
        }
