from flask import Flask, request, render_template
import requests
from flask_socketio import SocketIO, emit
import os
import subprocess

app = Flask(__name__, static_folder='templates')
socketio = SocketIO(app)

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('add_song')
def handle_add_song(data):
    song = data.get('song')
    if song:
        requests.post('http://localhost:5001/add', json={'song': song})
        emit('song_added', {'message': 'Musica adicionada!'})

@socketio.on('get_queue')
def handle_get_queue():
    response = requests.get('http://localhost:5001/queue')
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    try:
        queue = response.json().get('queue', [])
        emit('queue', {'queue': queue})
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")

@socketio.on('get_current_song')
def handle_get_current_song():
    response = requests.get('http://localhost:5001/current')
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    try:
        current_song = response.json().get('current_song', 'Nenhuma música tocando')
        emit('current_song', {'current_song': current_song})
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")

@socketio.on('delete_song')
def handle_delete_song(data):
    pos = data.get('pos')
    if pos is not None:
        response = requests.post('http://localhost:5001/delete', json={'pos': pos})
        emit('song_deleted', {'message': 'Musica removida!'})

@socketio.on('skip')
def handle_skip():
    print('Skipping song...')
    requests.post('http://localhost:5001/skip')
    emit('song_skipped', {'message': 'Musica pulada!'})

@socketio.on('shutdown')
def handle_shutdown():
    emit('shutdown_ack', {'message': 'Shutting down...'})
    # Run the shutdown command
    subprocess.call(['sudo', 'shutdown', 'now'])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)