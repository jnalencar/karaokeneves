import os

import requests
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit


app = Flask(__name__, static_folder='templates', template_folder='templates')
socketio = SocketIO(app)
QUEUE_URL = os.getenv(
    'KARAOKE_QUEUE_URL',
    f"http://127.0.0.1:{os.getenv('KARAOKE_QUEUE_PORT', '5001')}",
)


def queue_request(method, path, **kwargs):
    response = requests.request(
        method,
        f'{QUEUE_URL}/{path}',
        timeout=5,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def emit_service_error():
    emit('service_error', {
        'message': 'Não foi possível comunicar com o serviço da fila.',
    })


@app.get('/')
def home():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@socketio.on('add_song')
def handle_add_song(data):
    if not isinstance(data, dict) or not isinstance(data.get('song'), str):
        emit('song_error', {'message': 'Informe o nome da música.'})
        return
    try:
        queue_request('POST', 'add', json={'song': data['song']})
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('song_added', {'message': 'Música adicionada!'})


@socketio.on('get_queue')
def handle_get_queue():
    try:
        data = queue_request('GET', 'queue')
        if not isinstance(data, dict):
            raise ValueError('Resposta inválida do serviço da fila.')
        queue = data.get('queue')
        if not isinstance(queue, list):
            raise ValueError('Resposta inválida do serviço da fila.')
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('queue', {'queue': queue})


@socketio.on('get_current_song')
def handle_get_current_song():
    try:
        data = queue_request('GET', 'current')
        if not isinstance(data, dict):
            raise ValueError('Resposta inválida do serviço da fila.')
        current_song = data.get('current_song')
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('current_song', {
        'current_song': current_song or 'Nenhuma música tocando',
    })


@socketio.on('delete_song')
def handle_delete_song(data):
    pos = data.get('pos') if isinstance(data, dict) else None
    if isinstance(pos, bool) or not isinstance(pos, int) or pos < 0:
        emit('song_error', {'message': 'Posição inválida na fila.'})
        return
    try:
        queue_request('POST', 'delete', json={'pos': pos})
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('song_deleted', {'message': 'Música removida!'})


@socketio.on('move_song')
def handle_move_song(data):
    source = data.get('source') if isinstance(data, dict) else None
    target = data.get('target') if isinstance(data, dict) else None
    positions = (source, target)
    if any(
        isinstance(position, bool)
        or not isinstance(position, int)
        or position < 0
        for position in positions
    ):
        emit('song_error', {'message': 'Posição inválida na fila.'})
        return
    try:
        queue_request(
            'POST',
            'move',
            json={'source': source, 'target': target},
        )
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('song_moved', {'message': 'Ordem da fila atualizada!'})


@socketio.on('skip')
def handle_skip():
    try:
        queue_request('POST', 'skip')
    except (requests.RequestException, ValueError):
        emit_service_error()
        return
    emit('song_skipped', {'message': 'Música pulada!'})


if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('KARAOKE_CONTROL_PORT', '5000')),
    )
