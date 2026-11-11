# -*- coding: utf-8 -*-
"""Pruebas de la transcripción del dictado en el servidor.

El audio se transcribe con un modelo local (faster-whisper). Para que las
pruebas no dependan de la descarga del modelo, aquí se sustituye
`transcribir_audio` por un doble; lo que se fija es el contrato del endpoint:
permisos, tamaño, disponibilidad y errores.
"""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from . import transcripcion
from .tests_captura_voz import BaseCapturaVozTest


class TranscripcionDisponibleTest(BaseCapturaVozTest):
    @override_settings(TRANSCRIPCION_BACKEND='browser')
    def test_backend_browser_la_desactiva(self):
        self.assertFalse(transcripcion.disponible())

    @override_settings(TRANSCRIPCION_BACKEND='auto')
    def test_auto_depende_de_la_libreria_instalada(self):
        with patch.dict('sys.modules', {'faster_whisper': object()}):
            self.assertTrue(transcripcion.disponible())

    @override_settings(TRANSCRIPCION_BACKEND='local')
    def test_local_sin_libreria_no_esta_disponible(self):
        import sys
        with patch.dict(sys.modules, {'faster_whisper': None}):
            self.assertFalse(transcripcion.disponible())


class EndpointTranscribirTest(BaseCapturaVozTest):
    def _url(self):
        return reverse('captura_voz_transcribir', args=[self.exp.pk])

    def _audio(self, contenido=b'\x1aE\xdf\xa3audio-de-prueba', nombre='dictado.webm'):
        return SimpleUploadedFile(nombre, contenido, content_type='audio/webm')

    @override_settings(TRANSCRIPCION_BACKEND='browser')
    def test_sin_backend_responde_503(self):
        respuesta = self.client.post(self._url(), {'audio': self._audio()})
        self.assertEqual(respuesta.status_code, 503)
        self.assertIn('no está disponible', respuesta.json()['error'])

    @patch('expedientes.transcripcion.disponible', return_value=True)
    @patch('expedientes.transcripcion.transcribir_audio',
           return_value='  cuatro mil quinientos  ')
    def test_transcribe_y_devuelve_texto(self, _transcribir, _disponible):
        respuesta = self.client.post(self._url(), {'audio': self._audio()})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['texto'], 'cuatro mil quinientos')
        self.assertEqual(respuesta.json()['error'], '')

    @patch('expedientes.transcripcion.disponible', return_value=True)
    @patch('expedientes.transcripcion.transcribir_audio', return_value='')
    def test_audio_sin_texto_avisa(self, _transcribir, _disponible):
        respuesta = self.client.post(self._url(), {'audio': self._audio()})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['texto'], '')
        self.assertIn('No se entendió', respuesta.json()['error'])

    @patch('expedientes.transcripcion.disponible', return_value=True)
    def test_sin_archivo_responde_400(self, _disponible):
        respuesta = self.client.post(self._url(), {})
        self.assertEqual(respuesta.status_code, 400)

    @patch('expedientes.transcripcion.disponible', return_value=True)
    @override_settings(MAX_AUDIO_DICTADO_BYTES=10)
    def test_audio_demasiado_largo_responde_400(self, _disponible):
        respuesta = self.client.post(self._url(), {
            'audio': self._audio(b'x' * 50),
        })
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('demasiado largo', respuesta.json()['error'])

    @patch('expedientes.transcripcion.disponible', return_value=True)
    @patch('expedientes.transcripcion.transcribir_audio',
           side_effect=RuntimeError('modelo roto'))
    def test_error_del_modelo_no_filtra_detalle(self, _transcribir, _disponible):
        respuesta = self.client.post(self._url(), {'audio': self._audio()})

        self.assertEqual(respuesta.status_code, 500)
        self.assertNotIn('modelo roto', respuesta.json()['error'])

    def test_exige_permiso(self):
        self.client.force_login(self.sin_permiso)
        respuesta = self.client.post(self._url(), {'audio': self._audio()})
        self.assertEqual(respuesta.status_code, 403)


class PantallaConServidorTest(BaseCapturaVozTest):
    @patch('expedientes.transcripcion.disponible', return_value=True)
    def test_la_pantalla_activa_el_modo_servidor(self, _disponible):
        cuerpo = self.client.get(reverse('captura_voz', args=[self.exp.pk])
                                 ).content.decode('utf-8')
        self.assertIn('"servidor": true', cuerpo)
        self.assertIn('captura-voz/transcribir/', cuerpo)

    @override_settings(TRANSCRIPCION_BACKEND='browser')
    def test_la_pantalla_cae_al_navegador_si_no_hay_modelo(self):
        cuerpo = self.client.get(reverse('captura_voz', args=[self.exp.pk])
                                 ).content.decode('utf-8')
        self.assertIn('"servidor": false', cuerpo)
