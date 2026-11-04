import logging
import os
import re
import signal
from collections import OrderedDict
from threading import Event, Lock, Thread
from urllib.error import URLError
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, render_template, request
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from youtube_search import YoutubeSearch


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='templates', template_folder='templates')
shutdown_event = Event()
playback_finished = Event()
playback_lock = Lock()
search_cache_lock = Lock()
search_cache = OrderedDict()
search_in_progress = {}
playback_active = False
video_id_pattern = re.compile(r'^[A-Za-z0-9_-]{11}$')

QUEUE_URL = os.getenv(
    'KARAOKE_QUEUE_URL',
    f"http://127.0.0.1:{os.getenv('KARAOKE_QUEUE_PORT', '5001')}",
)
PLAYER_PORT = int(os.getenv('KARAOKE_PLAYER_PORT', '5002'))


def set_playback_active(active):
    global playback_active
    with playback_lock:
        playback_active = active
        if not active:
            playback_finished.clear()


@app.get('/health')
def health():
    with playback_lock:
        active = playback_active
    return jsonify({
        'status': 'stopping' if shutdown_event.is_set() else 'ok',
        'playing': active,
    })


@app.get('/play/<video_id>')
def play_video(video_id):
    if not isinstance(video_id, str) or not video_id_pattern.fullmatch(video_id):
        return jsonify({'error': 'ID de vídeo inválido.'}), 400
    return render_template(
        'video.html',
        video_id=video_id,
        song=request.args.get('song', ''),
    )


@app.get('/next-song')
def next_song():
    current_song = request.args.get('current_song')
    if not current_song:
        return jsonify({'error': 'A música atual é obrigatória.'}), 400

    try:
        current_response = requests.get(f'{QUEUE_URL}/current', timeout=5)
        current_response.raise_for_status()
        current_data = current_response.json()
        if not isinstance(current_data, dict):
            raise ValueError('Resposta inválida ao consultar a música atual.')
        if current_data.get('current_song') != current_song:
            return jsonify({'next_song': None})

        next_response = requests.get(f'{QUEUE_URL}/next', timeout=5)
        next_response.raise_for_status()
        next_data = next_response.json()
        if not isinstance(next_data, dict):
            raise ValueError('Resposta inválida ao consultar a próxima música.')
        song = next_data.get('song')
        if song is not None and not isinstance(song, str):
            raise ValueError('O nome da próxima música é inválido.')
    except (requests.RequestException, ValueError):
        logger.exception('Não foi possível consultar a próxima música.')
        return jsonify({
            'error': 'Não foi possível consultar a próxima música.',
        }), 502

    return jsonify({'next_song': song})


@app.post('/finished')
def finished():
    with playback_lock:
        if not playback_active:
            return jsonify({'error': 'Não há música em reprodução.'}), 409
        playback_finished.set()
    return jsonify({'status': 'finished'})


@app.post('/skip')
def skip():
    with playback_lock:
        if not playback_active:
            return jsonify({'error': 'Não há música em reprodução.'}), 409
        playback_finished.set()
    return jsonify({'status': 'skipped'})


def _search_youtube_video_id(song):
    results = YoutubeSearch(f'{song} karaoke', max_results=5).to_dict()
    if not isinstance(results, list):
        raise ValueError('Resposta inválida da busca do YouTube.')
    return next(
        (
            result.get('id')
            for result in results
            if isinstance(result, dict)
            and isinstance(result.get('id'), str)
            and video_id_pattern.fullmatch(result['id'])
        ),
        None,
    )


def _get_youtube_video_id(song):
    while True:
        with search_cache_lock:
            if song in search_cache:
                search_cache.move_to_end(song)
                return search_cache[song]

            pending_search = search_in_progress.get(song)
            if pending_search is None:
                pending_search = Event()
                search_in_progress[song] = pending_search
                should_search = True
            else:
                should_search = False

        if not should_search:
            pending_search.wait()
            continue

        search_succeeded = False
        try:
            video_id = _search_youtube_video_id(song)
            search_succeeded = True
        finally:
            with search_cache_lock:
                if search_succeeded:
                    search_cache[song] = video_id
                    search_cache.move_to_end(song)
                search_in_progress.pop(song, None)
                pending_search.set()
        return video_id


def _prefetch_queued_songs_once():
    response = requests.get(f'{QUEUE_URL}/queue', timeout=5)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get('queue'), list):
        raise ValueError('Resposta inválida ao consultar a fila.')

    queue = data['queue']
    if any(not isinstance(song, str) for song in queue):
        raise ValueError('O nome de uma música na fila é inválido.')
    queued_songs = set(queue)
    with search_cache_lock:
        for song in tuple(search_cache):
            if song not in queued_songs:
                del search_cache[song]

    for song in queue:
        _get_youtube_video_id(song)


def _prefetch_queued_songs():
    while not shutdown_event.is_set():
        try:
            _prefetch_queued_songs_once()
        except (requests.RequestException, URLError, ValueError):
            logger.exception('Falha ao pré-buscar músicas da fila.')
            shutdown_event.wait(5)
            continue
        shutdown_event.wait(2)


def _queue_has_next_song():
    response = requests.get(f'{QUEUE_URL}/next', timeout=5)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Resposta inválida ao consultar a próxima música.')
    song = data.get('song')
    if song is not None and not isinstance(song, str):
        raise ValueError('O nome da próxima música é inválido.')
    return bool(song)


def _forget_unsuccessful_search(song):
    with search_cache_lock:
        if search_cache.get(song) is None:
            search_cache.pop(song, None)


def _play_song(page, song):
    video_id = _get_youtube_video_id(song)
    if not video_id:
        _forget_unsuccessful_search(song)
        logger.warning('Nenhum resultado encontrado para: %s', song)
        return False

    song_started = False
    try:
        set_playback_active(True)
        page.goto(
            f'http://127.0.0.1:{PLAYER_PORT}/play/{video_id}?'
            f'{urlencode({"song": song})}',
            wait_until='domcontentloaded',
            timeout=30000,
        )
        page.wait_for_function(
            'window.karaokePlayerReady === true',
            timeout=30000,
        )
        page.locator('#unmute-overlay').click(timeout=10000)

        response = requests.post(f'{QUEUE_URL}/pop', timeout=5)
        response.raise_for_status()
        song_started = True
        logger.info('Reproduzindo: %s', song)

        while not shutdown_event.is_set():
            if playback_finished.wait(0.5):
                break
            if page.is_closed():
                break
        return True
    finally:
        set_playback_active(False)
        if song_started:
            try:
                response = requests.post(f'{QUEUE_URL}/finish', timeout=5)
                response.raise_for_status()
            except requests.RequestException:
                logger.exception('Não foi possível atualizar a música atual.')
        return_to_entry = True
        if song_started:
            try:
                return_to_entry = not _queue_has_next_song()
            except (requests.RequestException, ValueError):
                logger.exception('Não foi possível verificar a fila seguinte.')
        if (
            return_to_entry
            and not shutdown_event.is_set()
            and not page.is_closed()
        ):
            try:
                page.goto(
                    f"http://127.0.0.1:{os.getenv('KARAOKE_ENTRY_PORT', '5003')}",
                    wait_until='domcontentloaded',
                    timeout=10000,
                )
            except PlaywrightError:
                logger.exception('Não foi possível voltar à tela do QR Code.')


def _play_queue(page):
    while not shutdown_event.is_set():
        try:
            response = requests.get(f'{QUEUE_URL}/next', timeout=5)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError('Resposta inválida do serviço da fila.')
            song = data.get('song')
            if song is not None and not isinstance(song, str):
                raise ValueError('O nome da música na fila é inválido.')
        except (requests.RequestException, ValueError):
            logger.exception('Falha ao consultar a fila.')
            shutdown_event.wait(5)
            continue

        if not song:
            shutdown_event.wait(2)
            continue

        try:
            if not _play_song(page, song):
                shutdown_event.wait(5)
        except (requests.RequestException, URLError, ValueError):
            logger.exception('Falha ao reproduzir: %s', song)
            shutdown_event.wait(5)
        except PlaywrightError:
            logger.exception('Falha no Chromium ao reproduzir: %s', song)
            raise


def _launch_display(playwright):
    launch_options = {
        'headless': False,
        'args': [
            '--kiosk',
            '--start-fullscreen',
            '--no-first-run',
            '--disable-infobars',
            '--disable-dev-shm-usage',
        ],
    }
    executable_path = os.getenv('KARAOKE_BROWSER_EXECUTABLE')
    if executable_path:
        launch_options['executable_path'] = executable_path

    browser = playwright.chromium.launch(**launch_options)
    page = browser.new_page(no_viewport=True)
    page.goto(
        f"http://127.0.0.1:{os.getenv('KARAOKE_ENTRY_PORT', '5003')}",
        wait_until='domcontentloaded',
        timeout=30000,
    )
    return browser, page


def search_and_play_song():
    while not shutdown_event.is_set():
        try:
            with sync_playwright() as playwright:
                browser, page = _launch_display(playwright)
                try:
                    logger.info('Tela única em modo quiosque pronta.')
                    _play_queue(page)
                finally:
                    browser.close()
        except PlaywrightError:
            logger.exception('Não foi possível iniciar o Chromium do player.')
            shutdown_event.wait(10)


def _handle_termination(_signum, _frame):
    raise KeyboardInterrupt


def main():
    server = make_server(
        os.getenv('KARAOKE_INTERNAL_HOST', '127.0.0.1'),
        PLAYER_PORT,
        app,
        threaded=True,
    )
    worker = Thread(target=search_and_play_song, name='video-player', daemon=True)
    prefetch_worker = Thread(
        target=_prefetch_queued_songs,
        name='queue-prefetch',
        daemon=True,
    )
    worker.start()
    prefetch_worker.start()
    signal.signal(signal.SIGTERM, _handle_termination)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Encerrando player de vídeo.')
    finally:
        shutdown_event.set()
        playback_finished.set()
        server.server_close()
        worker.join(timeout=5)
        prefetch_worker.join(timeout=5)


if __name__ == '__main__':
    main()
