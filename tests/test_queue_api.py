import atexit
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


_test_storage = tempfile.TemporaryDirectory()
atexit.register(_test_storage.cleanup)
_previous_database_path = os.environ.get('KARAOKE_DB_PATH')
os.environ['KARAOKE_DB_PATH'] = str(
    Path(_test_storage.name) / 'imported.sqlite3'
)

from services.music_queue import main as queue_service

if _previous_database_path is None:
    os.environ.pop('KARAOKE_DB_PATH', None)
else:
    os.environ['KARAOKE_DB_PATH'] = _previous_database_path


class QueueApiTests(unittest.TestCase):
    def setUp(self):
        self.client = queue_service.app.test_client()
        queue_service.db = queue_service.DB(
            Path(_test_storage.name) / f'{self.id()}.sqlite3'
        )

    def test_add_and_read_queue(self):
        response = self.client.post('/add', json={'song': 'Minha música'})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get('/queue').json, {
            'queue': ['Minha música'],
        })

    def test_invalid_song_payload_returns_bad_request(self):
        for payload in ({'song': '  '}, {'song': 'a' * 201}, [], None):
            with self.subTest(payload=payload):
                response = self.client.post('/add', json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)

    def test_delete_reports_invalid_positions(self):
        self.client.post('/add', json={'song': 'Minha música'})

        self.assertEqual(
            self.client.post('/delete', json={'pos': -1}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post('/delete', json={'pos': True}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post('/delete', json={'pos': 3}).status_code,
            404,
        )

    def test_finish_clears_the_current_song(self):
        self.client.post('/add', json={'song': 'Minha música'})
        self.client.post('/pop')

        response = self.client.post('/finish')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.get('/current').json['current_song'])

    def test_skip_reports_player_unavailable(self):
        with patch.object(
            queue_service.requests,
            'post',
            side_effect=queue_service.requests.Timeout,
        ):
            response = self.client.post('/skip')

        self.assertEqual(response.status_code, 502)
        self.assertIn('error', response.json)


if __name__ == '__main__':
    unittest.main()
