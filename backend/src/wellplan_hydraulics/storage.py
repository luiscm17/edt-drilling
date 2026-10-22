"""Small append-only SQLite store; callers validate and calculate before saving."""
from contextlib import contextmanager
import json
import sqlite3


@contextmanager
def _connection(path):
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class CaseStore:
    def __init__(self, path):
        self.path = str(path)

    def initialize(self):
        with _connection(self.path) as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )''')

    @staticmethod
    def _record(row):
        return {'id': row[0], 'input': json.loads(row[1]), 'result': json.loads(row[2])}

    def save(self, inputs, result):
        # Serialize before opening the transaction; never store NaN/Infinity.
        input_json = json.dumps(inputs, allow_nan=False)
        result_json = json.dumps(result, allow_nan=False)
        with _connection(self.path) as connection:
            cursor = connection.execute(
                'INSERT INTO cases (input_json, result_json) VALUES (?, ?)',
                (input_json, result_json))
            record = self._record((cursor.lastrowid, input_json, result_json))
        return record

    def list(self):
        with _connection(self.path) as connection:
            rows = connection.execute(
                'SELECT id, input_json, result_json FROM cases ORDER BY id').fetchall()
        return [self._record(row) for row in rows]

    def get(self, case_id):
        with _connection(self.path) as connection:
            row = connection.execute(
                'SELECT id, input_json, result_json FROM cases WHERE id = ?',
                (case_id,)).fetchone()
        return self._record(row) if row else None
