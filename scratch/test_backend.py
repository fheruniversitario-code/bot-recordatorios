import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from datetime import datetime, timedelta
from database import DatabaseManager, FRECUENCIAS, calcular_siguiente_fecha

TEST_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_memoria.json")

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)
        self.db = DatabaseManager(file_path=TEST_DB_FILE)

    def tearDown(self):
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)

    def test_calcular_siguiente_fecha(self):
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "diaria"), "2026-08-16")
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "semanal"), "2026-08-22")
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "quincenal"), "2026-08-30")
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "mensual"), "2026-09-15")
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "bimensual"), "2026-10-15")
        self.assertEqual(calcular_siguiente_fecha("2026-08-15", "trimestral"), "2026-11-15")

    def test_crear_tarea_lote_con_hora_y_recordatorios(self):
        unidades = ["CAISES Guanajuato", "UMAPS Puentecillas"]
        creadas = self.db.crear_tarea_lote(
            titulo="Reporte de Vacunación",
            descripcion="Entregar informe mensual",
            tipo_destino="unidad",
            unidades=unidades,
            categoria="Vacunación",
            frecuencia="mensual",
            fecha_entrega="2026-09-01",
            hora_entrega="14:30",
            dias_aviso=5,
            recordatorios_por_dia=2,
            recordatorios=["Telegram"]
        )
        self.assertEqual(len(creadas), 2)
        self.assertEqual(creadas[0]["hora_entrega"], "14:30")
        self.assertEqual(creadas[0]["recordatorios_por_dia"], 2)

        # Probar completar tarea recurrente
        tarea_id = creadas[0]["id"]
        ok, msg = self.db.completar_tarea(tarea_id, notas="Todo en orden")
        self.assertTrue(ok)

        # Probar finalizar serie del segundo item
        t2_id = creadas[1]["id"]
        ok_fin, msg_fin = self.db.finalizar_serie(t2_id)
        self.assertTrue(ok_fin)

        tareas = self.db.obtener_tareas()
        t2 = [t for t in tareas if t["id"] == t2_id][0]
        self.assertTrue(t2["completada"])
        self.assertEqual(t2["frecuencia"], "unica")

if __name__ == "__main__":
    unittest.main()
