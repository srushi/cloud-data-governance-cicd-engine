"""Local offline connector backed by CSV fixtures (or a SQLite database).

This is what makes the full demo runnable with no cloud credentials: point
the connector at a directory of ``<table>.csv`` files (see ``fixtures/``) and
it behaves exactly like a warehouse connector. If the directory instead
contains a ``warehouse.db`` SQLite file, tables are read from it.
"""

from __future__ import annotations

import csv
import os
import sqlite3

from .base import WarehouseConnector


class LocalConnector(WarehouseConnector):
    name = "local"

    def __init__(self, fixtures_dir: str):
        self.fixtures_dir = fixtures_dir
        self.db_path = os.path.join(fixtures_dir, "warehouse.db")
        self.use_sqlite = os.path.exists(self.db_path)
        self._cache: dict[str, list[dict]] = {}

    def list_tables(self) -> list[str]:
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
                return [r[0] for r in rows]
            finally:
                conn.close()
        if not os.path.isdir(self.fixtures_dir):
            return []
        return sorted(f[:-4] for f in os.listdir(self.fixtures_dir)
                      if f.endswith(".csv"))

    def fetch_table(self, table: str) -> list[dict]:
        if table in self._cache:
            return self._cache[table]
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = [{k: (None if row[k] is None else str(row[k]))
                         for k in row.keys()}
                        for row in conn.execute(f'SELECT * FROM "{table}"')]
            finally:
                conn.close()
        else:
            path = os.path.join(self.fixtures_dir, f"{table}.csv")
            with open(path, newline="", encoding="utf-8") as fh:
                rows = [{k: (None if v == "" else v) for k, v in row.items()}
                        for row in csv.DictReader(fh)]
        self._cache[table] = rows
        return rows

    def table_columns(self, table: str) -> list[str]:
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            try:
                return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
            finally:
                conn.close()
        path = os.path.join(self.fixtures_dir, f"{table}.csv")
        with open(path, newline="", encoding="utf-8") as fh:
            return next(csv.reader(fh))
