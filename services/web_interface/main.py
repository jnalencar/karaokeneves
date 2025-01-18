from flask import Flask, request, render_template
import requests
from flask_socketio import SocketIO, emit

app = Flask(__name__)
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

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)