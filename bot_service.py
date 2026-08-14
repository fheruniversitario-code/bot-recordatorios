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


# --- SCHEDULER DE RECORDATORIO DIARIO Y MULTI-SLOT ---
def enviar_resumen_diario(bot, min_recordatorios_requeridos=1):
    if not bot:
        return

    config = db.obtener_configuracion()
    chat_id = config.get("telegram_chat_id")
    if not chat_id:
        return

    tareas = db.obtener_tareas(filtro_estado="activas")
    # Filtrar tareas activas en periodo de aviso
    activas_aviso = [
        t for t in tareas 
        if t.get("estado_calculado") in ["vencida", "por_vencer"] 
        and t.get("recordatorios_por_dia", 1) >= min_recordatorios_requeridos
    ]

    if not activas_aviso:
        return

    slot_label = "08:00 AM" if min_recordatorios_requeridos == 1 else ("13:00 PM" if min_recordatorios_requeridos == 2 else "19:00 PM")
    header = f"🚨 *AVISO DIARIO DE PENDIENTES ({slot_label})* 🚨\n({datetime.date.today().strftime('%d/%m/%Y')})\n\nTienes {len(activas_aviso)} tarea(s) pendientes:"
    bot.send_message(chat_id, header)

    for t in activas_aviso:
        freq_lbl = FRECUENCIAS.get(t.get("frecuencia"), t.get("frecuencia"))
        msg = (
            f"🏥 *{t['unidad']}*\n"
            f"📝 *{t['tarea']}*\n"
            f"🔁 Frecuencia: `{freq_lbl}`\n"
            f"📅 Fecha Límite: *{t['fecha_entrega']}* ⏰ `{t.get('hora_entrega', '09:00')} hrs`"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Marcar Realizada", callback_data=f"done_{t['id']}"),
            InlineKeyboardButton("📅 Postergar +3 días", callback_data=f"postpone_{t['id']}")
        )
        try:
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print("Error enviando mensaje telegram:", e)


def loop_programador(bot):
    print("[*] Programador diario de Telegram iniciado con soporte de múltiples recordatorios al día...")
    config = db.obtener_configuracion()
    hora_defecto = config.get("hora_notificacion_diaria", "08:00")

    # Slot 1 (Mañana / Principal)
    schedule.every().day.at(hora_defecto).do(enviar_resumen_diario, bot=bot, min_recordatorios_requeridos=1)
    
    # Slot 2 (Mediodía / Tarde - para tareas con >= 2 recordatorios por dia)
    schedule.every().day.at("13:00").do(enviar_resumen_diario, bot=bot, min_recordatorios_requeridos=2)
    
    # Slot 3 (Noche - para tareas con 3 recordatorios por dia)
    schedule.every().day.at("19:00").do(enviar_resumen_diario, bot=bot, min_recordatorios_requeridos=3)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print("Error en loop scheduler:", e)
        time.sleep(15)


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