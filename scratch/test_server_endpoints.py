import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from server import app

class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_api(self):
        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')

    def test_tareas_api(self):
        # Crear tarea en lote
        payload = {
            "tarea": "Reporte Trimestral de Epidemiología",
            "descripcion": "Verificar vacunas e inventario",
            "tipo_destino": "unidad",
            "unidades": ["CAISES Guanajuato", "UMAPS Puentecillas"],
            "categoria": "Informes y Reportes",
            "frecuencia": "trimestral",
            "fecha_entrega": "2026-11-30",
            "dias_aviso": 7
        }
        res = self.client.post('/api/tareas', json=payload)
        self.assertEqual(res.status_code, 200)
        j = res.get_json()
        self.assertEqual(j['status'], 'success')
        self.assertEqual(len(j['data']), 2)

        # GET tareas
        res_get = self.client.get('/api/tareas')
        self.assertEqual(res_get.status_code, 200)
        data = res_get.get_json()['data']
        self.assertGreaterEqual(len(data), 2)

    def test_pdf_report(self):
        response = self.client.get('/api/reporte/pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')

if __name__ == "__main__":
    unittest.main()
