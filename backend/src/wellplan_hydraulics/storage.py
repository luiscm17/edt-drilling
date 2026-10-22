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
            # Additive migration: never rewrite input/result bytes or assign an
            # origin to old rows. Repeated startup leaves the schema unchanged.
            columns = {row[1] for row in connection.execute('PRAGMA table_info(cases)')}
            if 'provenance_json' not in columns:
                connection.execute('ALTER TABLE cases ADD COLUMN provenance_json TEXT')

    @staticmethod
    def _record(row):
        return {'id': row[0], 'input': json.loads(row[1]), 'result': json.loads(row[2]),
                'provenance': json.loads(row[3]) if row[3] is not None else None}

    def save(self, inputs, result, provenance=None):
        # Serialize before opening the transaction; never store NaN/Infinity.
        input_json = json.dumps(inputs, allow_nan=False)
        result_json = json.dumps(result, allow_nan=False)
        provenance_json = (json.dumps(provenance, allow_nan=False)
                           if provenance is not None else None)
        with _connection(self.path) as connection:
            cursor = connection.execute(
                'INSERT INTO cases (input_json, result_json, provenance_json) VALUES (?, ?, ?)',
                (input_json, result_json, provenance_json))
            record = self._record((cursor.lastrowid, input_json, result_json, provenance_json))
        return record

    def list(self):
        with _connection(self.path) as connection:
            rows = connection.execute(
                'SELECT id, input_json, result_json, provenance_json FROM cases ORDER BY id').fetchall()
        return [self._record(row) for row in rows]

    def get(self, case_id):
        with _connection(self.path) as connection:
            row = connection.execute(
                'SELECT id, input_json, result_json, provenance_json FROM cases WHERE id = ?',
                (case_id,)).fetchone()
        return self._record(row) if row else None
