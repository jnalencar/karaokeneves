import unittest
from unittest.mock import patch

from services.entry_screen import main as entry_service
from services.video_player import main as player_service


class PlayerEndpointTests(unittest.TestCase):
    def setUp(self):
        player_service.shutdown_event.clear()
        player_service.set_playback_active(False)
        self.client = player_service.app.test_client()

    def tearDown(self):
        player_service.set_playback_active(False)

    def test_skip_is_rejected_when_nothing_is_playing(self):
        response = self.client.post('/skip')

        self.assertEqual(response.status_code, 409)

    def test_skip_finishes_the_active_playback(self):
        player_service.set_playback_active(True)

        response = self.client.post('/skip')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(player_service.playback_finished.is_set())

    def test_play_route_rejects_invalid_video_ids(self):
        response = self.client.get('/play/short')

        self.assertEqual(response.status_code, 400)

    def test_play_route_serves_the_player_page(self):
        response = self.client.get('/play/dQw4w9WgXcQ')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'dQw4w9WgXcQ', response.data)
        self.assertIn(b'/templates/scripts/video.js', response.data)
        response.close()
        script = self.client.get('/templates/scripts/video.js')
        self.assertEqual(script.status_code, 200)
        script.close()


class EntryScreenTests(unittest.TestCase):
    def setUp(self):
        self.client = entry_service.app.test_client()

    def test_qr_code_is_generated_for_the_control_url(self):
        with patch.object(
            entry_service,
            'get_control_url',
            return_value='http://192.168.1.10:5000',
        ):
            response = self.client.get('/qrcode.png')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/png')
        self.assertTrue(response.data.startswith(b'\x89PNG'))

    def test_entry_page_references_the_dynamic_qr_code(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/qrcode.png', response.data)


if __name__ == '__main__':
    unittest.main()
