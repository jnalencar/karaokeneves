import sys
import os

# Add the parent directory of 'shared' to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.db import DB
from flask import Flask, request, jsonify

app = Flask(__name__)
db = DB()

@app.route('/add', methods=['POST'])
def add_song():
    song = request.json.get('song')
    db.add_song(song)
    return jsonify({'message': 'Musica adicionada!'})

@app.route('/next', methods=['GET'])
def next_song():
    song = db.get_next_song()
    return jsonify({'song': song})

@app.route('/pop', methods=['POST'])
def pop_song():
    db.pop_next_song()
    return jsonify({'message': 'Musica removida!'})

@app.route('/queue', methods=['GET'])
def get_queue():
    queue = db.get_all_songs()
    return jsonify({'queue': queue})

@app.route('/current', methods=['GET'])
def current_song():
    song = db.get_current_song()
    return jsonify({'current_song': song})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)