import io
import logging
import os
import signal
import socket
from threading import Thread

import qrcode
from flask import Flask, jsonify, render_template, send_file
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
ENTRY_PORT = int(os.getenv('KARAOKE_ENTRY_PORT', '5003'))


def get_local_ip():
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(('8.8.8.8', 80))
        return connection.getsockname()[0]
    except OSError:
        logger.exception('Não foi possível detectar o IP local.')
        return '127.0.0.1'
    finally:
        connection.close()


def get_control_url():
    host = os.getenv('KARAOKE_HOST') or get_local_ip()
    port = os.getenv('KARAOKE_CONTROL_PORT', '5000')
    return f'http://{host}:{port}'


@app.get('/')
def entry_screen():
    return render_template('entry.html')


@app.get('/qrcode.png')
def qr_code():
    image = qrcode.make(get_control_url())
    image_data = io.BytesIO()
    image.save(image_data, format='PNG')
    image_data.seek(0)
    return send_file(image_data, mimetype='image/png')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


def _handle_termination(_signum, _frame):
    raise KeyboardInterrupt


def main():
    server = make_server('0.0.0.0', ENTRY_PORT, app, threaded=True)
    server_thread = Thread(
        target=server.serve_forever,
        name='entry-web-server',
        daemon=True,
    )
    signal.signal(signal.SIGTERM, _handle_termination)
    server_thread.start()

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
                page = browser.new_page()
                page.goto(
                    f'http://127.0.0.1:{ENTRY_PORT}',
                    wait_until='domcontentloaded',
                    timeout=30000,
                )
                while not page.is_closed():
                    page.wait_for_timeout(500)
            finally:
                browser.close()
    except KeyboardInterrupt:
        logger.info('Encerrando tela inicial.')
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


if __name__ == '__main__':
    main()
