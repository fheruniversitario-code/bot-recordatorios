import os
import io
from flask import Flask, render_template, jsonify, request, send_file
from database import DatabaseManager, FRECUENCIAS

app = Flask(__name__, template_folder="templates", static_folder="static")
db = DatabaseManager()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    pin = data.get("pin", "")
    if db.validar_pin(pin):
        return jsonify({
            "status": "success",
            "message": "Acceso concedido",
            "token": "valid_session_token_saludremind_2602"
        })
    return jsonify({"status": "error", "message": "PIN de acceso incorrecto."}), 401


@app.route("/api/auth/verify", methods=["POST"])
def auth_verify():
    data = request.json or {}
    token = data.get("token", "")
    pin = data.get("pin", "")
    if token == "valid_session_token_saludremind_2602" or db.validar_pin(pin):
        return jsonify({"status": "success", "message": "Sesión válida."})
    return jsonify({"status": "error", "message": "Sesión vencida o requerida."}), 401


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    return jsonify({"status": "success", "data": db.obtener_estadisticas()})


@app.route("/api/tareas", methods=["GET"])
def get_tareas():
    filtro_estado = request.args.get("estado")
    filtro_tipo = request.args.get("tipo")
    filtro_unidad = request.args.get("unidad")
    filtro_frecuencia = request.args.get("frecuencia")
    busqueda = request.args.get("busqueda", "").strip().lower()

    tareas = db.obtener_tareas(
        filtro_estado=filtro_estado,
        filtro_tipo=filtro_tipo,
        filtro_unidad=filtro_unidad,
        filtro_frecuencia=filtro_frecuencia
    )

    if busqueda:
        tareas = [
            t for t in tareas 
            if busqueda in t.get("tarea", "").lower() or busqueda in t.get("descripcion", "").lower() or busqueda in t.get("unidad", "").lower()
        ]

    return jsonify({"status": "success", "data": tareas, "count": len(tareas)})


@app.route("/api/tareas", methods=["POST"])
def crear_tarea():
    data = request.json or {}
    titulo = data.get("tarea", "").strip()
    descripcion = data.get("descripcion", "").strip()
    tipo_destino = data.get("tipo_destino", "unidad")
    unidades = data.get("unidades", [])
    categoria = data.get("categoria", "General")
    frecuencia = data.get("frecuencia", "unica")
    fecha_entrega = data.get("fecha_entrega")
    hora_entrega = data.get("hora_entrega", "09:00")
    dias_aviso = data.get("dias_aviso", 5)
    recordatorios_por_dia = data.get("recordatorios_por_dia", 1)
    recordatorios = data.get("recordatorios", ["Telegram", "Visual en App"])

    if not titulo:
        return jsonify({"status": "error", "message": "El título de la tarea es requerido."}), 400

    if tipo_destino == "unidad" and not unidades:
        return jsonify({"status": "error", "message": "Debes seleccionar al menos una unidad de salud."}), 400

    creadas = db.crear_tarea_lote(
        titulo=titulo,
        descripcion=descripcion,
        tipo_destino=tipo_destino,
        unidades=unidades,
        categoria=categoria,
        frecuencia=frecuencia,
        fecha_entrega=fecha_entrega,
        hora_entrega=hora_entrega,
        dias_aviso=dias_aviso,
        recordatorios_por_dia=recordatorios_por_dia,
        recordatorios=recordatorios
    )

    return jsonify({
        "status": "success",
        "message": f"Se ha(n) creado {len(creadas)} tarea(s) correctamente.",
        "data": creadas
    })


@app.route("/api/tareas/<tarea_id>/completar", methods=["POST"])
def completar_tarea(tarea_id):
    data = request.json or {}
    notas = data.get("notas", "")
    ok, mensaje = db.completar_tarea(tarea_id, notas=notas)
    if ok:
        return jsonify({"status": "success", "message": mensaje})
    return jsonify({"status": "error", "message": mensaje}), 400


@app.route("/api/tareas/<tarea_id>/finalizar_serie", methods=["POST"])
def finalizar_serie(tarea_id):
    ok, mensaje = db.finalizar_serie(tarea_id)
    if ok:
        return jsonify({"status": "success", "message": mensaje})
    return jsonify({"status": "error", "message": mensaje}), 400


@app.route("/api/tareas/<tarea_id>/postergar", methods=["POST"])
def postergar_tarea(tarea_id):
    data = request.json or {}
    dias = data.get("dias", 3)
    ok, mensaje = db.postergar_tarea(tarea_id, dias=int(dias))
    if ok:
        return jsonify({"status": "success", "message": mensaje})
    return jsonify({"status": "error", "message": mensaje}), 400


@app.route("/api/tareas/<tarea_id>", methods=["PUT"])
def editar_tarea(tarea_id):
    data = request.json or {}
    ok, mensaje = db.editar_tarea(tarea_id, data)
    if ok:
        return jsonify({"status": "success", "message": mensaje})
    return jsonify({"status": "error", "message": mensaje}), 400


@app.route("/api/tareas/<tarea_id>", methods=["DELETE"])
def eliminar_tarea(tarea_id):
    ok, mensaje = db.eliminar_tarea(tarea_id)
    if ok:
        return jsonify({"status": "success", "message": mensaje})
    return jsonify({"status": "error", "message": mensaje}), 400


@app.route("/api/unidades", methods=["GET", "POST", "PUT", "DELETE"])
def gestionar_unidades():
    if request.method == "GET":
        return jsonify({"status": "success", "data": db.obtener_unidades()})
    elif request.method == "POST":
        data = request.json or {}
        nombre = data.get("nombre", "")
        ok, msg = db.agregar_unidad(nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_unidades()})
        return jsonify({"status": "error", "message": msg}), 400
    elif request.method == "PUT":
        data = request.json or {}
        nombre_anterior = data.get("nombre_anterior", "")
        nuevo_nombre = data.get("nuevo_nombre", "")
        ok, msg = db.editar_unidad(nombre_anterior, nuevo_nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_unidades()})
        return jsonify({"status": "error", "message": msg}), 400
    elif request.method == "DELETE":
        data = request.json or {}
        nombre = data.get("nombre", "")
        ok, msg = db.eliminar_unidad(nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_unidades()})
        return jsonify({"status": "error", "message": msg}), 400


@app.route("/api/categorias", methods=["GET", "POST", "PUT", "DELETE"])
def gestionar_categorias():
    if request.method == "GET":
        return jsonify({"status": "success", "data": db.obtener_categorias()})
    elif request.method == "POST":
        data = request.json or {}
        nombre = data.get("nombre", "")
        ok, msg = db.agregar_categoria(nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_categorias()})
        return jsonify({"status": "error", "message": msg}), 400
    elif request.method == "PUT":
        data = request.json or {}
        nombre_anterior = data.get("nombre_anterior", "")
        nuevo_nombre = data.get("nuevo_nombre", "")
        ok, msg = db.editar_categoria(nombre_anterior, nuevo_nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_categorias()})
        return jsonify({"status": "error", "message": msg}), 400
    elif request.method == "DELETE":
        data = request.json or {}
        nombre = data.get("nombre", "")
        ok, msg = db.eliminar_categoria(nombre)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_categorias()})
        return jsonify({"status": "error", "message": msg}), 400


@app.route("/api/configuracion", methods=["GET", "POST"])
def gestionar_configuracion():
    if request.method == "GET":
        return jsonify({"status": "success", "data": db.obtener_configuracion()})
    elif request.method == "POST":
        data = request.json or {}
        ok, msg = db.actualizar_configuracion(data)
        if ok:
            return jsonify({"status": "success", "message": msg, "data": db.obtener_configuracion()})
        return jsonify({"status": "error", "message": msg}), 400


@app.route("/api/historial", methods=["GET", "DELETE"])
def gestionar_historial():
    if request.method == "GET":
        return jsonify({"status": "success", "data": db.obtener_historial()})
    elif request.method == "DELETE":
        ok, msg = db.limpiar_historial()
        return jsonify({"status": "success", "message": msg})


@app.route("/api/respaldo/json", methods=["GET"])
def descargar_respaldo_json():
    try:
        path = db.file_path
        return send_file(path, as_attachment=True, download_name="memoria_caises_respaldo.json", mimetype="application/json")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/frecuencias", methods=["GET"])
def get_frecuencias():
    return jsonify({"status": "success", "data": FRECUENCIAS})


@app.route("/api/reporte/pdf", methods=["GET"])
def generar_reporte_pdf():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=1
        )
        story.append(Paragraph("<b>REPORTE DE CUMPLIMIENTO DE PENDIENTES - UNIDADES DE SALUD</b>", title_style))
        story.append(Spacer(1, 15))

        stats = db.obtener_estadisticas()
        tareas = db.obtener_tareas()
        historial = db.obtener_historial()

        resumen_text = f"<b>Total Activas:</b> {stats['total_activas']} | <b>Vencidas:</b> {stats['vencidas']} | <b>Por Vencer:</b> {stats['por_vencer']} | <b>Completadas en Historial:</b> {stats['total_cumplidas']}"
        story.append(Paragraph(resumen_text, styles['Normal']))
        story.append(Spacer(1, 15))

        story.append(Paragraph("<b>TAREAS PENDIENTES / ACTIVAS</b>", styles['Heading2']))
        data_table = [["Unidad / Ámbito", "Tarea", "Categoría", "Frecuencia", "Fecha y Hora Límite", "Estado"]]
        
        for t in tareas:
            if not t.get("completada", False):
                freq_lbl = FRECUENCIAS.get(t.get("frecuencia"), t.get("frecuencia"))
                fecha_hora = f"{t.get('fecha_entrega', '')} {t.get('hora_entrega', '')}"
                data_table.append([
                    t.get("unidad", ""),
                    t.get("tarea", ""),
                    t.get("categoria", ""),
                    freq_lbl,
                    fecha_hora,
                    t.get("estado_calculado", "").upper()
                ])

        if len(data_table) > 1:
            t = Table(data_table, colWidths=[100, 140, 90, 80, 85, 55])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No hay tareas pendientes en este momento.", styles['Italic']))

        story.append(Spacer(1, 20))

        story.append(Paragraph("<b>HISTORIAL DE CUMPLIMIENTO CERRADO</b>", styles['Heading2']))
        hist_table = [["Unidad", "Tarea", "Categoría", "Fecha Límite Original", "Cumplida El"]]
        for h in historial[-25:]:
            hist_table.append([
                h.get("unidad", ""),
                h.get("tarea", ""),
                h.get("categoria", ""),
                h.get("fecha_entrega_original", ""),
                h.get("fecha_cumplimiento", "")
            ])

        if len(hist_table) > 1:
            th = Table(hist_table, colWidths=[110, 150, 90, 90, 110])
            th.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(th)
        else:
            story.append(Paragraph("No hay registros en el historial.", styles['Italic']))

        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="Reporte_Pendientes_Unidades_Salud.pdf", mimetype="application/pdf")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error generando PDF: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
