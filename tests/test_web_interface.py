import unittest
from unittest.mock import Mock, patch

import requests

from services.web_interface import main as web_service


class WebInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.client = web_service.socketio.test_client(web_service.app)
        self.addCleanup(self.client.disconnect)

    def test_control_page_and_assets_are_available(self):
        with web_service.app.test_client() as http_client:
            response = http_client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'/templates/scripts/index.js', response.data)

            script = http_client.get('/templates/scripts/index.js')
            self.assertEqual(script.status_code, 200)
            script.close()
            response.close()

    @patch.object(web_service.requests, 'request')
    def test_add_song_emits_success_after_queue_accepts_request(self, request):
        response = Mock()
        response.json.return_value = {'message': 'ok'}
        request.return_value = response

        self.client.emit('add_song', {'song': 'Minha música'})

        events = self.client.get_received()
        self.assertIn('song_added', [event['name'] for event in events])
        request.assert_called_once_with(
            'POST',
            f'{web_service.QUEUE_URL}/add',
            timeout=5,
            json={'song': 'Minha música'},
        )

    @patch.object(web_service.requests, 'request')
    def test_move_song_sends_positions_to_queue_service(self, request):
        response = Mock()
        response.json.return_value = {'message': 'ok'}
        request.return_value = response

        self.client.emit('move_song', {'source': 2, 'target': 0})

        events = self.client.get_received()
        self.assertIn('song_moved', [event['name'] for event in events])
        request.assert_called_once_with(
            'POST',
            f'{web_service.QUEUE_URL}/move',
            timeout=5,
            json={'source': 2, 'target': 0},
        )

    @patch.object(
        web_service.requests,
        'request',
        side_effect=requests.ConnectionError,
    )
    def test_queue_outage_is_reported_to_control_client(self, _request):
        self.client.emit('get_queue')

        events = self.client.get_received()
        errors = [event for event in events if event['name'] == 'service_error']
        self.assertEqual(len(errors), 1)
        self.assertIn('message', errors[0]['args'][0])


if __name__ == '__main__':
    unittest.main()
