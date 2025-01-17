from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return '<form action="/add" method="post"> <input name="song"> <button type="submit">Add Song</button> </form>'

@app.route('/add', methods=['POST'])
def add_song():
    song = request.form.get('song')
    requests.post('http://localhost:5001/add', json={'song': song})
    return 'Song added!'

app.run(host='0.0.0.0', port=5000)