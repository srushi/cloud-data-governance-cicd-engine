"""Warehouse connector interface.

A connector exposes the tables of one warehouse (or fixture directory) as
lists of row dicts whose values are strings or ``None`` — the same shape the
validation checks consume regardless of the backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class WarehouseConnector(ABC):
    name = "base"

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Return the names of the tables available from this source."""

    @abstractmethod
    def fetch_table(self, table: str) -> list[dict]:
        """Return all rows of ``table`` as dicts of column -> string/None."""

    @abstractmethod
    def table_columns(self, table: str) -> list[str]:
        """Return the column names of ``table`` in order."""

    def close(self) -> None:  # pragma: no cover - default no-op
        pass
