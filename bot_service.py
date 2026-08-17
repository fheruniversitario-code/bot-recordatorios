import os
import time
import datetime
import threading
import schedule
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import DatabaseManager, FRECUENCIAS

db = DatabaseManager()
USER_STATES = {}


def obtener_bot():
    config = db.obtener_configuracion()
    token = config.get("telegram_token") or os.getenv("TELEGRAM_TOKEN", "")
    if not token or token == "PON_TU_TOKEN_AQUI_SI_PRUEBAS_LOCAL":
        print("[!] Bot de Telegram: TOKEN no configurado. El servidor seguira funcionando sin bot Telegram.")
        return None
    try:
        bot = telebot.TeleBot(token, parse_mode="Markdown")
        return bot
    except Exception as e:
        print("[!] Error iniciando TeleBot:", e)
        return None


# --- BOT HANDLERS ---
def registrar_handlers(bot):
    if not bot:
        return

    @bot.message_handler(commands=['start', 'menu', 'help'])
    def cmd_start(message):
        texto = (
            "🏥 *SISTEMA DE GESTIÓN CAISES & REMINDERS*\n\n"
            "¡Hola! Soy tu asistente de recordatorios para Unidades de Salud y Pendientes Personales.\n\n"
            "Selecciona una opción del menú interactivo o usa los comandos:"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📋 Ver Todos los Pendientes", callback_data="btn_pendientes"),
            InlineKeyboardButton("⚡ Ver Próximos / Vencidos", callback_data="btn_urgentes"),
            InlineKeyboardButton("🏥 Por Unidades de Salud", callback_data="btn_unidades"),
            InlineKeyboardButton("👤 Pendientes Personales", callback_data="btn_personales"),
            InlineKeyboardButton("➕ Crear Nueva Tarea", callback_data="btn_asistente_nueva")
        )
        bot.reply_to(message, texto, reply_markup=markup)

    @bot.message_handler(commands=['pendientes'])
    def cmd_pendientes(message):
        enviar_lista_pendientes(bot, message.chat.id)

    @bot.message_handler(commands=['unidades'])
    def cmd_unidades(message):
        unidades = db.obtener_unidades()
        markup = InlineKeyboardMarkup(row_width=2)
        for u in unidades:
            markup.add(InlineKeyboardButton(f"🏥 {u}", callback_data=f"filter_unit_{u}"))
        bot.send_message(message.chat.id, "Selecciona una Unidad de Salud para consultar sus pendientes:", reply_markup=markup)

    @bot.message_handler(commands=['personales'])
    def cmd_personales(message):
        tareas = db.obtener_tareas(filtro_estado="activas", filtro_tipo="personal")
        enviar_formato_tareas(bot, message.chat.id, tareas, "👤 *PENDIENTES PERSONALES / GENERALES*")

    @bot.message_handler(commands=['nueva'])
    def cmd_nueva(message):
        texto_cmd = message.text.replace('/nueva', '').strip()
        if '|' in texto_cmd:
            try:
                partes = [p.strip() for p in texto_cmd.split('|')]
                tarea = partes[0]
                unidad = partes[1] if len(partes) > 1 else "CAISES Guanajuato"
                frecuencia = partes[2].lower() if len(partes) > 2 else "mensual"
                fecha_entrega = partes[3] if len(partes) > 3 else str(datetime.date.today() + datetime.timedelta(days=7))
                dias_aviso = int(partes[4]) if len(partes) > 4 else 5

                tipo_destino = "personal" if unidad.lower() == "personal" else "unidad"

                creadas = db.crear_tarea_lote(
                    titulo=tarea,
                    descripcion="Creada desde Telegram",
                    tipo_destino=tipo_destino,
                    unidades=[unidad],
                    categoria="General",
                    frecuencia=frecuencia,
                    fecha_entrega=fecha_entrega,
                    hora_entrega="09:00",
                    dias_aviso=dias_aviso,
                    recordatorios_por_dia=1,
                    recordatorios=["Telegram", "Visual en App"]
                )
                bot.reply_to(message, f"✅ *Tarea Guardada*: `{tarea}` ({unidad})\n📅 Límite: `{fecha_entrega}` 09:00 hrs | 🔁 Frecuencia: `{FRECUENCIAS.get(frecuencia, frecuencia)}`")
            except Exception as e:
                bot.reply_to(message, f"❌ Error de formato. Usa:\n`/nueva Mi Tarea | CAISES Guanajuato | mensual | 2026-09-15 | 5`")
        else:
            iniciar_asistente_nueva_tarea(bot, message.chat.id)

    # --- CALLBACK QUERY HANDLER ---
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        data = call.data
        chat_id = call.message.chat.id

        if data == "btn_pendientes":
            enviar_lista_pendientes(bot, chat_id)
        elif data == "btn_urgentes":
            tareas = db.obtener_tareas(filtro_estado="activas")
            urgentes = [t for t in tareas if t.get("estado_calculado") in ["vencida", "por_vencer"]]
            enviar_formato_tareas(bot, chat_id, urgentes, "🚨 *PENDIENTES VENCIDOS Y PRÓXIMOS*")
        elif data == "btn_unidades":
            unidades = db.obtener_unidades()
            markup = InlineKeyboardMarkup(row_width=2)
            for u in unidades:
                markup.add(InlineKeyboardButton(f"🏥 {u}", callback_data=f"filter_unit_{u}"))
            bot.send_message(chat_id, "Selecciona una Unidad de Salud:", reply_markup=markup)
        elif data == "btn_personales":
            tareas = db.obtener_tareas(filtro_estado="activas", filtro_tipo="personal")
            enviar_formato_tareas(bot, chat_id, tareas, "👤 *PENDIENTES PERSONALES*")
        elif data.startswith("filter_unit_"):
            unidad_nom = data.replace("filter_unit_", "")
            tareas = db.obtener_tareas(filtro_estado="activas", filtro_unidad=unidad_nom)
            enviar_formato_tareas(bot, chat_id, tareas, f"🏥 *PENDIENTES - {unidad_nom.upper()}*")
        elif data == "btn_asistente_nueva":
            iniciar_asistente_nueva_tarea(bot, chat_id)
        elif data.startswith("done_"):
            tarea_id = data.split('_')[1]
            ok, msg = db.completar_tarea(tarea_id, notas="Cumplida vía Bot de Telegram")
            if ok:
                bot.answer_callback_query(call.id, "✅ ¡Tarea realizada!")
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=call.message.text + f"\n\n{msg}"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Error al completar.")
        elif data.startswith("postpone_"):
            tarea_id = data.split('_')[1]
            ok, msg = db.postergar_tarea(tarea_id, 3)
            if ok:
                bot.answer_callback_query(call.id, "📅 Postergada +3 días")
                bot.send_message(chat_id, f"📅 {msg}")
            else:
                bot.answer_callback_query(call.id, "❌ Error al postergar.")
        elif data.startswith("stop_series_"):
            tarea_id = data.split('_')[2]
            ok, msg = db.finalizar_serie(tarea_id)
            if ok:
                bot.answer_callback_query(call.id, "🛑 Serie finalizada")
                bot.send_message(chat_id, f"🛑 {msg}")

    # Conversational text steps
    @bot.message_handler(func=lambda msg: msg.chat.id in USER_STATES)
    def handle_wizard_steps(message):
        chat_id = message.chat.id
        state = USER_STATES.get(chat_id)

        if state and state.get("step") == "WAIT_TITLE":
            state["titulo"] = message.text.strip()
            state["step"] = "WAIT_UNIT"
            bot.send_message(chat_id, "Excelente. ¿Para qué **Unidad de Salud** o ámbito es esta tarea?\nResponde escribiendo el nombre o 'Personal':")
        
        elif state and state.get("step") == "WAIT_UNIT":
            input_u = message.text.strip()
            state["unidad"] = input_u
            state["tipo_destino"] = "personal" if input_u.lower() in ["personal", "general"] else "unidad"
            state["step"] = "WAIT_FREQ"
            bot.send_message(chat_id, "Indica la **Frecuencia / Recurrencia**:\n(Opciones: unica, diaria, semanal, quincenal, mensual, bimensual, trimestral, cuatrimestral, semestral, anual)")

        elif state and state.get("step") == "WAIT_FREQ":
            freq = message.text.strip().lower()
            state["frecuencia"] = freq if freq in FRECUENCIAS else "mensual"
            state["step"] = "WAIT_DATE"
            bot.send_message(chat_id, "Indica la **Fecha Límite de Entrega** (Formato AAAA-MM-DD, ej. 2026-10-15):")

        elif state and state.get("step") == "WAIT_DATE":
            fecha_str = message.text.strip()
            state["fecha_entrega"] = fecha_str

            creadas = db.crear_tarea_lote(
                titulo=state["titulo"],
                descripcion="Creada vía asistente Telegram",
                tipo_destino=state["tipo_destino"],
                unidades=[state["unidad"]],
                categoria="General",
                frecuencia=state["frecuencia"],
                fecha_entrega=state["fecha_entrega"],
                hora_entrega="09:00",
                dias_aviso=5,
                recordatorios_por_dia=1,
                recordatorios=["Telegram", "Visual en App"]
            )
            del USER_STATES[chat_id]
            bot.send_message(chat_id, f"🎉 *¡Tarea creada con éxito!*\n`{state['titulo']}` ({state['unidad']})\nFecha límite: {fecha_str} 09:00 hrs")


def iniciar_asistente_nueva_tarea(bot, chat_id):
    USER_STATES[chat_id] = {"step": "WAIT_TITLE"}
    bot.send_message(chat_id, "📝 *ASISTENTE NUEVA TAREA*\n\nPor favor escribe el **Título / Descripción** de la actividad pendiente:")


def enviar_lista_pendientes(bot, chat_id):
    tareas = db.obtener_tareas(filtro_estado="activas")
    enviar_formato_tareas(bot, chat_id, tareas, "📋 *TODOS TUS PENDIENTES ACTIVOS*")


def enviar_formato_tareas(bot, chat_id, tareas, titulo_seccion):
    if not tareas:
        bot.send_message(chat_id, f"{titulo_seccion}\n\n🎉 ¡Excelente! No hay tareas pendientes en esta categoría.")
        return

    msg = f"{titulo_seccion} ({len(tareas)} en total):\n\n"
    for t in tareas[:15]:
        estado = t.get("estado_calculado", "pendiente")
        icon_est = "🚨" if estado == "vencida" else ("⚡" if estado == "por_vencer" else "🌱")
        freq_lbl = FRECUENCIAS.get(t.get("frecuencia"), t.get("frecuencia"))

        msg += f"{icon_est} *{t['tarea']}*\n"
        msg += f"🏥 `{t['unidad']}` | 🏷️ `{t['categoria']}`\n"
        msg += f"🔁 Frecuencia: `{freq_lbl}`\n"
        msg += f"📅 Fecha Límite: *{t['fecha_entrega']}* ⏰ `{t.get('hora_entrega', '09:00')} hrs`\n"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Ya lo hice", callback_data=f"done_{t['id']}"),
            InlineKeyboardButton("📅 Postergar +3d", callback_data=f"postpone_{t['id']}")
        )
        if t.get("frecuencia") != "unica" and not t.get("completada"):
            markup.add(InlineKeyboardButton("🛑 Finalizar Serie", callback_data=f"stop_series_{t['id']}"))

        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=markup)
        msg = ""


# --- SCHEDULER DE RECORDATORIO DIARIO, POR HORA E INTERVALOS DINÁMICOS ---
def obtener_ahora_mexico():
    """Obtiene fecha y hora actual con la zona horaria de México (America/Mexico_City)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Mexico_City"))
    except Exception:
        tz_mex = datetime.timezone(datetime.timedelta(hours=-6))
        return datetime.datetime.now(tz_mex)


def enviar_notificacion_individual(bot, chat_id, tarea):
    freq_lbl = FRECUENCIAS.get(tarea.get("frecuencia"), tarea.get("frecuencia"))
    estado = tarea.get("estado_calculado", "pendiente")
    icon_est = "🚨" if estado == "vencida" else "⚡"
    
    msg = (
        f"{icon_est} *RECORDATORIO DE PENDIENTES*\n\n"
        f"🏥 *{tarea['unidad']}*\n"
        f"📝 *{tarea['tarea']}*\n"
        f"🏷️ Categoría: `{tarea.get('categoria', 'General')}`\n"
        f"🔁 Frecuencia: `{freq_lbl}`\n"
        f"📅 Fecha Límite: *{tarea['fecha_entrega']}* ⏰ `{tarea.get('hora_entrega', '08:00')} hrs`"
    )
    if tarea.get("descripcion"):
        msg += f"\nℹ️ _{tarea['descripcion']}_"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Marcar Realizada", callback_data=f"done_{tarea['id']}"),
        InlineKeyboardButton("📅 Postergar +3 días", callback_data=f"postpone_{tarea['id']}")
    )
    if tarea.get("frecuencia") != "unica" and not tarea.get("completada"):
        markup.add(InlineKeyboardButton("🛑 Finalizar Serie", callback_data=f"stop_series_{tarea['id']}"))

    try:
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=markup)
        print(f"[+] Notificación enviada a Telegram: '{tarea['tarea']}' ({tarea['unidad']})")
    except Exception as e:
        print("Error enviando notificación telegram:", e)


def procesar_recordatorios_telegram(bot):
    if not bot:
        return

    config = db.obtener_configuracion()
    chat_id = config.get("telegram_chat_id")
    if not chat_id:
        return

    now_mex = obtener_ahora_mexico()
    hora_actual_str = now_mex.strftime("%H:%M")

    tareas = db.obtener_tareas(filtro_estado="activas")
    
    # Filtrar tareas por vencer o vencidas con aviso por Telegram activo
    activas_aviso = [
        t for t in tareas 
        if t.get("estado_calculado") in ["vencida", "por_vencer"] 
        and "Telegram" in t.get("recordatorios", ["Telegram", "Visual en App"])
    ]

    for t in activas_aviso:
        hora_tarea = t.get("hora_entrega", "08:00")
        frec_param = str(t.get("recordatorios_por_dia", "1"))
        last_sent_str = t.get("ultima_notificacion_telegram", "")

        minutos_desde_ultimo = 999999
        if last_sent_str:
            try:
                last_dt = datetime.datetime.strptime(last_sent_str, "%Y-%m-%d %H:%M:%S")
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=now_mex.tzinfo)
                minutos_desde_ultimo = (now_mex - last_dt).total_seconds() / 60.0
            except Exception:
                pass

        debe_notificar = False

        if frec_param.startswith("int_"):
            # Intervalos dinámicos en horas (int_2, int_3, int_4, int_6, int_8, int_12)
            try:
                num_horas = int(frec_param.replace("int_", ""))
            except ValueError:
                num_horas = 4
            intervalo_minutos = num_horas * 60
            if minutos_desde_ultimo >= (intervalo_minutos - 2):
                debe_notificar = True
        elif frec_param == "3":
            # 3 veces al día: hora_tarea, 13:00, 19:00
            slots = [hora_tarea, "13:00", "19:00"]
            if hora_actual_str in slots and minutos_desde_ultimo >= 45:
                debe_notificar = True
        elif frec_param == "2":
            # 2 veces al día: hora_tarea, 14:00
            slots = [hora_tarea, "14:00"]
            if hora_actual_str in slots and minutos_desde_ultimo >= 45:
                debe_notificar = True
        else:
            # 1 vez al día: a la hora personalizada fijada en la tarea o a la global
            hora_global = config.get("hora_notificacion_diaria", "08:00")
            slots = [hora_tarea, hora_global]
            if hora_actual_str in slots and minutos_desde_ultimo >= 1100: # ~18 horas
                debe_notificar = True

        if debe_notificar:
            enviar_notificacion_individual(bot, chat_id, t)
            db.registrar_notificacion_telegram_enviada(t["id"], now_mex.strftime("%Y-%m-%d %H:%M:%S"))


def loop_programador(bot):
    print("[*] Programador de Telegram iniciado (Zona Horaria México: America/Mexico_City)...")
    print("[*] Monitoreando horas fijadas e intervalos personalizados por tarea...")

    while True:
        try:
            procesar_recordatorios_telegram(bot)
        except Exception as e:
            print("Error en loop programador telegram:", e)
        time.sleep(30)


def iniciar_servicio_bot():
    bot = obtener_bot()
    if bot:
        registrar_handlers(bot)
        
        hilo_scheduler = threading.Thread(target=loop_programador, args=(bot,), daemon=True)
        hilo_scheduler.start()

        print("[*] Bot de Telegram escuchando mensajes...")
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print("Error en polling bot:", e)


if __name__ == "__main__":
    iniciar_servicio_bot()