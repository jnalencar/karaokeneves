# Karaoke Neves

Karaoke Neves is a web-based karaoke system that allows users to add songs to a queue, play them using a video player, and skip songs. The system is composed of four main services: `entry_screen`, `web_interface`, `music_queue`, and `video_player`.

## Requirements

To run this project, you need to have the following installed:

- Python 3.x
- pip (Python package installer)

You also need to install the required Python packages. You can do this by running:

```sh
pip install -r req.txt
```

## Project Structure

```sh
.env
.gitignore
.vscode/
    launch.json
app.py
req.txt
services/
    entry_screen/
        static/
            qrcode.png
        templates/
            entry.html
        main.py
    music_queue/
        main.py
    video_player/
        main.py
        templates/
            scripts/
                video.js
            styles/
                video.css
            video.html
    web_interface/
        main.py
        templates/
            assets/
            index.html
            scripts/
                index.js
            styles/
                index.css
shared/
    __pycache__/
    db.py
```

## Running the Project

To run all the services, execute the app.py script:

```sh
python app.py
```

This will start the `entry_screen`, `web_interface`, `music_queue`, and `video_player` services.

## Endpoints

### Entry Screen

#### GET /: Renders the QRCode to redirect the user to the web interface.

### Web Interface

#### GET /: Renders the main web interface.

### Music Queue

#### POST /add: Adds a song to the queue.
- Request body: `{ "song": "song_name" }`
- Response: `{ "message": "Musica adicionada!" }`

#### GET /next: Retrieves the next song in the queue.
- Response: `{ "song": "next_song_name" }`

#### POST /pop: Removes the next song from the queue.
- Response: `{ "message": "Musica removida!" }`

#### GET /queue: Retrieves the entire song queue.
- Response: `{ "queue": ["song1", "song2", ...] }`

#### GET /current: Retrieves the current song being played.
- Response: `{ "current_song": "current_song_name" }`

#### POST /delete: Deletes a song from the queue by position.
- Request body: `{ "pos": position }`
- Response: `{ "message": "Musica removida!" }`

#### POST /skip: Skips the current song.
- Response: `{ "message": "Musica pulada!", "response": "Skipped" }`

### Video Player

#### GET /play/<video_id>: Renders the video player for the given video ID.

#### POST /skip: Skips the current video being played.
- Response: `Skipped`

## Socket Events

### Web Interface

##### add_song: Adds a song to the queue.
- Data: `{ "song": "song_name" }`
- Emits: `song_added` with message `{ "message": "Musica adicionada!" }`

#### get_queue: Retrieves the entire song queue.
- Emits: `queue` with data `{ "queue": ["song1", "song2", ...] }`

#### get_current_song: Retrieves the current song being played.
- Emits: `current_song` with data `{ "current_song": "current_song_name" }`

#### delete_song: Deletes a song from the queue by position.
- Data: `{ "pos": position }`
- Emits: `song_deleted` with message `{ "message": "Musica removida!" }`

#### skip: Skips the current song.
- Emits: `song_skipped` with message `{ "message": "Musica pulada!" }`

### Music Queue

#### skip: Handles the skip event and calls the video player to skip the current song.
- Emits: `song_skipped` with message `{ "message": "Musica pulada!", "response": "Skipped" }`

## How It Works
1. Web Interface: The user interacts with the web interface to add songs to the queue, view the current song, and skip songs.
2. Music Queue: The `music_queue` service manages the song queue and handles requests to add, delete, and skip songs.
3. Video Player: The `video_player` service plays the songs from the queue using a YouTube video player. It handles requests to play and skip videos.
4. Entry Screen: The screen that the user see when the app is started, it has a QRCode to redirect the user to the web intercafe to interact with the system.

When the user start the app, the first screen to open is the `entry_screen`, it is a QRCode to simplify the user to access the `web_interface` with a direct link to its IP and Port.

When the user adds a song, the `web_interface` emits an add_song event, which is handled by the `music_queue` service. The song is added to the queue, and the `song_added` event is emitted back to the `web_interface`.

When the user clicks the skip button, the `web_interface` emits a skip event, which is handled by the `music_queue` service. The `music_queue` service then calls the `video_player` service to skip the current video. The `video_player` service stops the current video and starts playing the next song in the queue.