import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path


class DB:
    def __init__(self, database_path=None):
        default_path = Path(__file__).resolve().parents[1] / 'data' / 'karaoke.sqlite3'
        self.database_path = Path(
            database_path or os.getenv('KARAOKE_DB_PATH') or default_path
        ).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                'CREATE TABLE IF NOT EXISTS queue ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'song TEXT NOT NULL)'
            )
            connection.execute(
                'CREATE TABLE IF NOT EXISTS playback_state ('
                'key TEXT PRIMARY KEY, value TEXT)'
            )

    def add_song(self, song):
        if not isinstance(song, str) or not song.strip():
            raise ValueError('O nome da música não pode ficar vazio.')
        song = song.strip()
        if len(song) > 200:
            raise ValueError('O nome da música deve ter no máximo 200 caracteres.')

        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute('INSERT INTO queue (song) VALUES (?)', (song,))

    def get_next_song(self):
        with self._lock, closing(self._connect()) as connection, connection:
            row = connection.execute(
                'SELECT song FROM queue ORDER BY id LIMIT 1'
            ).fetchone()
            return row['song'] if row else None

    def pop_next_song(self):
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute(
                'SELECT id, song FROM queue ORDER BY id LIMIT 1'
            ).fetchone()
            if row is None:
                return None

            connection.execute('DELETE FROM queue WHERE id = ?', (row['id'],))
            connection.execute(
                'INSERT INTO playback_state (key, value) VALUES (?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                ('current_song', row['song']),
            )
            return row['song']

    def get_all_songs(self):
        with self._lock, closing(self._connect()) as connection, connection:
            rows = connection.execute(
                'SELECT song FROM queue ORDER BY id'
            ).fetchall()
            return [row['song'] for row in rows]

    def get_current_song(self):
        with self._lock, closing(self._connect()) as connection, connection:
            row = connection.execute(
                'SELECT value FROM playback_state WHERE key = ?',
                ('current_song',),
            ).fetchone()
            return row['value'] if row else None

    def clear_current_song(self):
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                'DELETE FROM playback_state WHERE key = ?',
                ('current_song',),
            )

    def delete_song(self, pos):
        if isinstance(pos, bool) or not isinstance(pos, int) or pos < 0:
            return False

        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute(
                'SELECT id FROM queue ORDER BY id LIMIT 1 OFFSET ?', (pos,)
            ).fetchone()
            if row is None:
                return False
            connection.execute('DELETE FROM queue WHERE id = ?', (row['id'],))
            return True
