import logging
import os
import re
import signal
from threading import Event, Lock, Thread
from urllib.error import URLError

import requests
from flask import Flask, jsonify, render_template
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
    return render_template('video.html', video_id=video_id)


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


def _play_song(browser, song):
    results = YoutubeSearch(f'{song} karaoke', max_results=5).to_dict()
    if not results:
        logger.warning('Nenhum resultado encontrado para: %s', song)
        return False

    video_id = next(
        (
            result.get('id')
            for result in results
            if isinstance(result, dict)
            and isinstance(result.get('id'), str)
            and video_id_pattern.fullmatch(result['id'])
        ),
        None,
    )
    if video_id is None:
        logger.warning('Resultado com ID de vídeo inválido para: %s', song)
        return False

    page = browser.new_page()
    song_started = False
    try:
        set_playback_active(True)
        page.goto(
            f'http://127.0.0.1:{PLAYER_PORT}/play/{video_id}',
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
        if not page.is_closed():
            page.close()


def _play_queue(browser):
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
            if not _play_song(browser, song):
                shutdown_event.wait(5)
        except (requests.RequestException, URLError, ValueError):
            logger.exception('Falha ao reproduzir: %s', song)
            shutdown_event.wait(5)
        except PlaywrightError:
            logger.exception('Falha no Chromium ao reproduzir: %s', song)
            raise


def search_and_play_song():
    while not shutdown_event.is_set():
        try:
            with sync_playwright() as playwright:
                launch_options = {
                    'headless': False,
                    'args': [
                        '--kiosk',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ],
                }
                executable_path = os.getenv('KARAOKE_BROWSER_EXECUTABLE')
                if executable_path:
                    launch_options['executable_path'] = executable_path
                browser = playwright.chromium.launch(**launch_options)
                try:
                    _play_queue(browser)
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
    worker.start()
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


if __name__ == '__main__':
    main()
