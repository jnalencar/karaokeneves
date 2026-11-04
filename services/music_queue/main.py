import os

import requests
from flask import Flask, jsonify, request

from shared.db import DB


app = Flask(__name__)
db = DB()


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@app.post('/add')
def add_song():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Envie um objeto JSON com o campo song.'}), 400

    try:
        db.add_song(data.get('song'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({'message': 'Música adicionada!'}), 201


@app.get('/next')
def next_song():
    return jsonify({'song': db.get_next_song()})


@app.post('/pop')
def pop_song():
    song = db.pop_next_song()
    if song is None:
        return jsonify({'error': 'A fila está vazia.'}), 404
    return jsonify({'message': 'Música removida!', 'song': song})


@app.post('/finish')
def finish_song():
    db.clear_current_song()
    return jsonify({'message': 'Reprodução finalizada.'})


@app.get('/queue')
def get_queue():
    return jsonify({'queue': db.get_all_songs()})


@app.get('/current')
def current_song():
    return jsonify({'current_song': db.get_current_song()})


@app.post('/delete')
def delete_song():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Envie um objeto JSON com o campo pos.'}), 400

    pos = data.get('pos')
    if isinstance(pos, bool) or not isinstance(pos, int) or pos < 0:
        return jsonify({'error': 'A posição deve ser um inteiro não negativo.'}), 400
    if not db.delete_song(pos):
        return jsonify({'error': 'Não existe música nessa posição.'}), 404
    return jsonify({'message': 'Música removida!'})


@app.post('/skip')
def skip_song():
    try:
        response = requests.post(
            os.getenv(
                'KARAOKE_PLAYER_URL',
                f"http://127.0.0.1:{os.getenv('KARAOKE_PLAYER_PORT', '5002')}",
            ) + '/skip',
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({'error': 'Não foi possível comunicar com o player.'}), 502
    return jsonify({'message': 'Música pulada!', 'response': response.text})


if __name__ == '__main__':
    app.run(
        host=os.getenv('KARAOKE_INTERNAL_HOST', '127.0.0.1'),
        port=int(os.getenv('KARAOKE_QUEUE_PORT', '5001')),
    )
