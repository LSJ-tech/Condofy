from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase

from .indicadores import IndicadorNoDisponibleError, obtener_uf, obtener_utm


class ValidarPeriodoTests(TestCase):
    def test_formato_invalido_lanza_error(self):
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026/10")

    def test_mes_fuera_de_rango_lanza_error(self):
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026-13")

    def test_input_malicioso_no_pasa_la_validacion(self):
        """periodo llega desde POST (LiquidacionGenerarView) -- confirma que
        un valor armado a mano no llega a construir la URL de mindicador.cl
        (ver python:S7044 en SonarCloud)."""
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026-10/../../etc/passwd")


class ObtenerUtmTests(TestCase):
    @patch("personal.indicadores.requests.get")
    def test_utm_publicada_devuelve_el_valor(self, mock_get):
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "serie": [{"fecha": "2026-10-01T00:00:00.000Z", "valor": 68785}]
        }
        self.assertEqual(obtener_utm("2026-10"), Decimal("68785"))
        mock_get.assert_called_once_with("https://mindicador.cl/api/utm/2026", timeout=8)

    @patch("personal.indicadores.requests.get")
    def test_utm_no_publicada_lanza_error(self, mock_get):
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {"serie": []}
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026-12")

    @patch("personal.indicadores.requests.get")
    def test_fallo_de_red_lanza_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("timeout")
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026-10")

    @patch("personal.indicadores.requests.get")
    def test_json_invalido_lanza_error(self, mock_get):
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.side_effect = ValueError("not json")
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_utm("2026-10")


class ObtenerUfTests(TestCase):
    @patch("personal.indicadores.requests.get")
    def test_uf_del_ultimo_dia_disponible(self, mock_get):
        valor = 39500.12
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {"serie": [{"fecha": "2026-10-31", "valor": valor}]}
        self.assertEqual(obtener_uf("2026-10"), Decimal(str(valor)))

    @patch("personal.indicadores.requests.get")
    def test_uf_cae_al_valor_mas_reciente_si_la_fecha_no_esta_publicada(self, mock_get):
        respuesta_vacia = MagicMock()
        respuesta_vacia.raise_for_status.return_value = None
        respuesta_vacia.json.return_value = {"serie": []}
        respuesta_reciente = MagicMock()
        respuesta_reciente.raise_for_status.return_value = None
        respuesta_reciente.json.return_value = {"serie": [{"fecha": "2026-10-05", "valor": 39400.0}]}
        mock_get.side_effect = [respuesta_vacia, respuesta_reciente]
        self.assertEqual(obtener_uf("2026-12"), Decimal(str(39400.0)))

    @patch("personal.indicadores.requests.get")
    def test_sin_ningun_valor_reciente_lanza_error(self, mock_get):
        vacio = MagicMock()
        vacio.raise_for_status.return_value = None
        vacio.json.return_value = {"serie": []}
        mock_get.side_effect = [vacio, vacio]
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_uf("2026-12")

    @patch("personal.indicadores.requests.get")
    def test_fallo_de_red_lanza_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("timeout")
        with self.assertRaises(IndicadorNoDisponibleError):
            obtener_uf("2026-10")
