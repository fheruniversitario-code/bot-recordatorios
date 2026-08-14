import threading
import time
import os
import sys

from server import app as flask_app
from bot_service import iniciar_servicio_bot

def lanzar_bot():
    try:
        iniciar_servicio_bot()
    except Exception as e:
        print("[!] Advertencia: No se pudo iniciar el servicio del Bot de Telegram:", e)

def main():
    print("==================================================================")
    print("=== INICIANDO SISTEMA DE GESTION Y RECORDATORIOS (WEB + TELEGRAM) ===")
    print("==================================================================")
    print("Servidor Web disponible en: http://localhost:5000")
    print("Servicio de Bot de Telegram en proceso de vinculacion...")
    print("------------------------------------------------------------------")

    # Iniciar servicio Bot en un hilo separado
    hilo_bot = threading.Thread(target=lanzar_bot, daemon=True)
    hilo_bot.start()

    # Iniciar servidor Flask
    try:
        flask_app.run(host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nSistema detenido por el usuario.")

if __name__ == "__main__":
    main()