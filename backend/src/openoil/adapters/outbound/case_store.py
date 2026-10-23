"""SQLAlchemy-backed SQLite adapter for atomic case snapshots."""

import json

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import URL


class CaseStore:
    def __init__(self, path):
        self.path = str(path)
        self.engine = create_engine(
            URL.create("sqlite", database=self.path),
            connect_args={"check_same_thread": False},
        )
        self.metadata = MetaData()
        self.cases = Table(
            "cases",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("input_json", Text, nullable=False),
            Column("result_json", Text, nullable=False),
            Column("provenance_json", Text, nullable=True),
        )

    def initialize(self):
        self.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            columns = {
                column["name"] for column in inspect(connection).get_columns("cases")
            }
            if "provenance_json" not in columns:
                # Additive migration: leave old input/result bytes and IDs untouched.
                connection.execute(
                    text("ALTER TABLE cases ADD COLUMN provenance_json TEXT")
                )

    @staticmethod
    def _record(row):
        return {
            "id": row["id"],
            "input": json.loads(row["input_json"]),
            "result": json.loads(row["result_json"]),
            "provenance": (
                json.loads(row["provenance_json"])
                if row["provenance_json"] is not None
                else None
            ),
        }

    def save(self, inputs, result, provenance=None):
        # Serialize before opening the transaction; never store NaN/Infinity.
        input_json = json.dumps(inputs, allow_nan=False)
        result_json = json.dumps(result, allow_nan=False)
        provenance_json = (
            json.dumps(provenance, allow_nan=False) if provenance is not None else None
        )
        with self.engine.begin() as connection:
            inserted = connection.execute(
                self.cases.insert().values(
                    input_json=input_json,
                    result_json=result_json,
                    provenance_json=provenance_json,
                )
            )
            case_id = inserted.inserted_primary_key[0]
        return self._record(
            {
                "id": case_id,
                "input_json": input_json,
                "result_json": result_json,
                "provenance_json": provenance_json,
            }
        )

    def list(self):
        statement = select(self.cases).order_by(self.cases.c.id)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [self._record(row) for row in rows]

    def get(self, case_id):
        statement = select(self.cases).where(self.cases.c.id == case_id)
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return self._record(row) if row is not None else None

    def close(self):
        self.engine.dispose()
