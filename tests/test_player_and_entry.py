import unittest
from unittest.mock import Mock, call, patch
from types import SimpleNamespace

from services.entry_screen import main as entry_service
from services.video_player import main as player_service


class PlayerEndpointTests(unittest.TestCase):
    def setUp(self):
        player_service.shutdown_event.clear()
        player_service.set_playback_active(False)
        with player_service.search_cache_lock:
            player_service.search_cache.clear()
            player_service.search_in_progress.clear()
        self.client = player_service.app.test_client()

    def tearDown(self):
        player_service.set_playback_active(False)

    def _make_page_that_finishes_playback(self):
        page = Mock()
        page.is_closed.return_value = False

        def finish_from_audio_activation(**_kwargs):
            player_service.playback_finished.set()

        page.locator.return_value.click.side_effect = finish_from_audio_activation
        return page

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
        self.assertIn(b'data-current-song=""', response.data)
        self.assertIn(b'id="next-song"', response.data)
        self.assertIn(b'id="next-song-requester"', response.data)
        self.assertIn(b'PEDIDO POR', response.data)
        self.assertIn(b'/templates/scripts/video.js', response.data)
        response.close()
        script = self.client.get('/templates/scripts/video.js')
        self.assertEqual(script.status_code, 200)
        script.close()
        stylesheet = self.client.get('/templates/styles/video.css')
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(b'.next-song', stylesheet.data)
        stylesheet.close()

    def test_next_song_endpoint_returns_queue_head_for_active_song(self):
        current_response = Mock()
        current_response.json.return_value = {
            'current_song': 'Música atual',
        }
        next_response = Mock()
        next_response.json.return_value = {'song': 'Próxima música'}

        with patch.object(
            player_service.requests,
            'get',
            side_effect=[current_response, next_response],
        ):
            response = self.client.get(
                '/next-song',
                query_string={'current_song': 'Música atual'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'next_song': 'Próxima música'})

    @patch.object(player_service, '_search_youtube_video_id')
    @patch.object(player_service.requests, 'get')
    def test_prefetch_starts_a_search_for_every_queued_song(
        self,
        get,
        search_results,
    ):
        queue_response = Mock()
        queue_response.json.return_value = {
            'queue': ['Primeira', 'Segunda', 'Terceira'],
        }
        get.return_value = queue_response
        search_results.return_value = 'dQw4w9WgXcQ'

        player_service._prefetch_queued_songs_once()

        self.assertEqual(
            search_results.call_args_list,
            [call('Primeira'), call('Segunda'), call('Terceira')],
        )

    @patch.object(player_service, '_search_youtube_video_id', return_value=None)
    def test_unsuccessful_search_can_be_retried(self, search_video):
        self.assertFalse(player_service._play_song(Mock(), 'Sem resultado'))
        self.assertFalse(player_service._play_song(Mock(), 'Sem resultado'))

        self.assertEqual(search_video.call_count, 2)

    @patch.object(player_service, '_queue_has_next_song', return_value=False)
    @patch.object(player_service.requests, 'post')
    @patch.object(player_service.requests, 'get')
    @patch.object(player_service, '_search_youtube_video_id')
    def test_playback_reuses_prefetched_youtube_results(
        self,
        search_results,
        get,
        _post,
        _queue_has_next,
    ):
        queue_response = Mock()
        queue_response.json.return_value = {'queue': ['Minha música']}
        get.return_value = queue_response
        search_results.return_value = 'dQw4w9WgXcQ'
        player_service._prefetch_queued_songs_once()

        page = self._make_page_that_finishes_playback()

        self.assertTrue(player_service._play_song(page, 'Minha música'))
        search_results.assert_called_once_with('Minha música')
        self.assertEqual(
            page.goto.call_args_list[0].args[0],
            'http://127.0.0.1:5002/play/dQw4w9WgXcQ?song=Minha+m%C3%BAsica',
        )

    @patch.object(player_service.requests, 'post')
    @patch.object(player_service, 'YoutubeSearch')
    def test_playback_reuses_display_page_and_returns_to_qr(
        self,
        youtube_search,
        post,
    ):
        youtube_search.return_value.to_dict.return_value = [
            {'id': 'dQw4w9WgXcQ'},
        ]
        post.return_value = Mock()
        page = self._make_page_that_finishes_playback()
        with patch.object(
            player_service,
            '_queue_has_next_song',
            return_value=False,
        ):
            result = player_service._play_song(page, 'Minha música')

        self.assertTrue(result)
        self.assertEqual(page.goto.call_count, 2)
        self.assertIn('/play/dQw4w9WgXcQ?', page.goto.call_args_list[0].args[0])
        self.assertTrue(page.goto.call_args_list[1].args[0].endswith(':5003'))
        self.assertFalse(page.close.called)
        self.assertEqual(post.call_count, 2)

    @patch.object(player_service, '_queue_has_next_song', return_value=True)
    @patch.object(player_service.requests, 'post')
    @patch.object(player_service, 'YoutubeSearch')
    def test_playback_keeps_video_screen_when_another_song_is_queued(
        self,
        youtube_search,
        post,
        _queue_has_next,
    ):
        youtube_search.return_value.to_dict.return_value = [
            {'id': 'dQw4w9WgXcQ'},
        ]
        post.return_value = Mock()
        page = self._make_page_that_finishes_playback()

        self.assertTrue(player_service._play_song(page, 'Minha música'))

        self.assertEqual(page.goto.call_count, 1)

    def test_display_launches_single_browser_in_fullscreen_kiosk(self):
        page = Mock()
        browser = Mock()
        browser.new_page.return_value = page
        playwright = SimpleNamespace(
            chromium=SimpleNamespace(launch=Mock(return_value=browser))
        )

        launched_browser, display_page = player_service._launch_display(playwright)

        self.assertIs(launched_browser, browser)
        self.assertIs(display_page, page)
        options = playwright.chromium.launch.call_args.kwargs
        self.assertFalse(options['headless'])
        self.assertIn('--kiosk', options['args'])
        self.assertIn('--start-fullscreen', options['args'])
        browser.new_page.assert_called_once_with(no_viewport=True)
        page.goto.assert_called_once()


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
        with patch.object(
            entry_service,
            'get_control_url',
            return_value='http://192.168.1.10:5000',
        ):
            response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/qrcode.png', response.data)
        self.assertIn(b'http://192.168.1.10:5000', response.data)
        self.assertIn(b'O palco', response.data)

    def test_entry_screen_styles_are_served(self):
        response = self.client.get('/static/styles/entry.css')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'100dvh', response.data)
        self.assertIn(b'--blue', response.data)
        self.assertNotIn(b'--purple', response.data)
        response.close()


if __name__ == '__main__':
    unittest.main()
