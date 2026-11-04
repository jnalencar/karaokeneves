from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from shared.db import DB


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / 'karaoke.sqlite3'
        self.db = DB(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_queue_survives_database_recreation(self):
        self.db.add_song('  Minha música  ')

        reopened_db = DB(self.database_path)

        self.assertEqual(reopened_db.get_all_songs(), ['Minha música'])

    def test_pop_moves_song_to_current_and_preserves_order(self):
        self.db.add_song('Primeira')
        self.db.add_song('Segunda')

        self.assertEqual(self.db.pop_next_song(), 'Primeira')
        self.assertEqual(self.db.get_current_song(), 'Primeira')
        self.assertEqual(self.db.get_all_songs(), ['Segunda'])
        self.db.clear_current_song()
        self.assertIsNone(self.db.get_current_song())
        empty_db = DB(Path(self.temp_dir.name) / 'empty.sqlite3')
        self.assertIsNone(empty_db.pop_next_song())

    def test_delete_uses_zero_based_queue_position(self):
        for song in ('Primeira', 'Segunda', 'Terceira'):
            self.db.add_song(song)

        self.assertTrue(self.db.delete_song(1))
        self.assertEqual(self.db.get_all_songs(), ['Primeira', 'Terceira'])
        self.assertFalse(self.db.delete_song(5))
        self.assertFalse(self.db.delete_song(-1))
        self.assertFalse(self.db.delete_song(True))

    def test_move_song_reorders_queue_and_delete_compacts_positions(self):
        for song in ('Primeira', 'Segunda', 'Terceira'):
            self.db.add_song(song)

        self.assertTrue(self.db.move_song(2, 0))
        self.assertEqual(self.db.get_all_songs(), [
            'Terceira',
            'Primeira',
            'Segunda',
        ])
        self.assertFalse(self.db.move_song(3, 0))
        self.assertFalse(self.db.move_song(0, -1))
        self.assertFalse(self.db.move_song(True, 0))

        self.assertTrue(self.db.delete_song(1))
        self.db.add_song('Quarta')
        self.assertEqual(self.db.get_all_songs(), [
            'Terceira',
            'Segunda',
            'Quarta',
        ])

    def test_legacy_queue_is_migrated_without_changing_its_order(self):
        legacy_path = Path(self.temp_dir.name) / 'legacy.sqlite3'
        with closing(sqlite3.connect(legacy_path)) as connection, connection:
            connection.execute(
                'CREATE TABLE queue ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, song TEXT NOT NULL)'
            )
            connection.executemany(
                'INSERT INTO queue (song) VALUES (?)',
                [('Primeira',), ('Segunda',)],
            )

        migrated_db = DB(legacy_path)
        migrated_db.add_song('Terceira')

        self.assertEqual(migrated_db.get_all_songs(), [
            'Primeira',
            'Segunda',
            'Terceira',
        ])

    def test_add_song_rejects_empty_or_overlong_names(self):
        for song in ('  ', 'a' * 201, None):
            with self.subTest(song=song):
                with self.assertRaises(ValueError):
                    self.db.add_song(song)

        self.assertEqual(self.db.get_all_songs(), [])

if __name__ == '__main__':
    unittest.main()
