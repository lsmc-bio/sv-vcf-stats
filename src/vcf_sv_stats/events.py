"""Bounded disk-backed record relationship graph."""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict


class EventSummary(TypedDict):
    duplicate_ids: tuple[tuple[str, int], ...]
    unresolved_mate_references: int
    bnd_total: int
    bnd_without_mate: int
    reciprocal_pairs: int
    resolved_events: int


class EventStore:
    """Record identifiers and relationship edges without unbounded Python state."""

    def __init__(self, temp_dir: str | Path | None = None) -> None:
        with tempfile.NamedTemporaryFile(
            prefix="vcf-sv-stats.events.", suffix=".sqlite3", dir=temp_dir, delete=False
        ) as handle:
            self.path = Path(handle.name)
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE records (
                ordinal INTEGER PRIMARY KEY,
                record_id TEXT,
                event_id TEXT,
                is_bnd INTEGER NOT NULL
            );
            CREATE TABLE mates (
                ordinal INTEGER NOT NULL,
                mate_id TEXT NOT NULL
            );
            """
        )

    def _create_indexes(self) -> None:
        """Create query indexes after the streaming ingestion phase completes."""
        self.connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS records_id ON records(record_id);
            CREATE INDEX IF NOT EXISTS records_event ON records(event_id);
            CREATE INDEX IF NOT EXISTS mates_ordinal ON mates(ordinal);
            CREATE INDEX IF NOT EXISTS mates_id ON mates(mate_id);
            """
        )

    def add(
        self,
        ordinal: int,
        record_id: str | None,
        event_id: str | None,
        mate_ids: Iterable[str],
        *,
        is_bnd: bool,
    ) -> None:
        real_record_id = record_id if record_id and record_id != "." else None
        real_event_id = event_id if event_id and event_id != "." else None
        real_mate_ids = tuple(mate_id for mate_id in mate_ids if mate_id and mate_id != ".")
        if not (real_record_id or real_event_id or real_mate_ids or is_bnd):
            return
        self.connection.execute(
            "INSERT INTO records(ordinal, record_id, event_id, is_bnd) VALUES (?, ?, ?, ?)",
            (ordinal, real_record_id, real_event_id, int(is_bnd)),
        )
        self.connection.executemany(
            "INSERT INTO mates(ordinal, mate_id) VALUES (?, ?)",
            ((ordinal, mate_id) for mate_id in real_mate_ids),
        )

    def summarize(self) -> EventSummary:
        self.connection.commit()
        self._create_indexes()
        duplicate_rows = self.connection.execute(
            """
            SELECT record_id, COUNT(*) AS count
            FROM records
            WHERE record_id IS NOT NULL AND record_id != '.'
            GROUP BY record_id HAVING COUNT(*) > 1
            ORDER BY record_id
            """
        ).fetchall()
        unresolved = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM mates m
            LEFT JOIN records r ON r.record_id = m.mate_id
            WHERE r.ordinal IS NULL
            """
        ).fetchone()[0]
        bnd_total = self.connection.execute(
            "SELECT COUNT(*) FROM records WHERE is_bnd = 1"
        ).fetchone()[0]
        bnd_without_mate = self.connection.execute(
            """
            SELECT COUNT(*) FROM records r
            WHERE r.is_bnd = 1 AND NOT EXISTS (
                SELECT 1 FROM mates m WHERE m.ordinal = r.ordinal
            )
            """
        ).fetchone()[0]
        reciprocal_pairs = self.connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT
                    CASE WHEN a.ordinal < b.ordinal THEN a.ordinal ELSE b.ordinal END AS left_id,
                    CASE WHEN a.ordinal < b.ordinal THEN b.ordinal ELSE a.ordinal END AS right_id
                FROM records a
                JOIN mates am ON am.ordinal = a.ordinal
                JOIN records b ON b.record_id = am.mate_id
                JOIN mates bm ON bm.ordinal = b.ordinal AND bm.mate_id = a.record_id
                WHERE a.is_bnd = 1 AND b.is_bnd = 1
            )
            """
        ).fetchone()[0]
        reciprocal_pairs_with_event = self.connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT
                    CASE WHEN a.ordinal < b.ordinal THEN a.ordinal ELSE b.ordinal END AS left_id,
                    CASE WHEN a.ordinal < b.ordinal THEN b.ordinal ELSE a.ordinal END AS right_id
                FROM records a
                JOIN mates am ON am.ordinal = a.ordinal
                JOIN records b ON b.record_id = am.mate_id
                JOIN mates bm ON bm.ordinal = b.ordinal AND bm.mate_id = a.record_id
                WHERE a.is_bnd = 1 AND b.is_bnd = 1
                  AND a.event_id IS NOT NULL AND a.event_id != '.'
                  AND a.event_id = b.event_id
            )
            """
        ).fetchone()[0]
        explicit_events = self.connection.execute(
            """
            SELECT COUNT(DISTINCT event_id)
            FROM records
            WHERE event_id IS NOT NULL AND event_id != '.'
            """
        ).fetchone()[0]
        return {
            "duplicate_ids": tuple((str(row[0]), int(row[1])) for row in duplicate_rows),
            "unresolved_mate_references": int(unresolved),
            "bnd_total": int(bnd_total),
            "bnd_without_mate": int(bnd_without_mate),
            "reciprocal_pairs": int(reciprocal_pairs),
            "resolved_events": int(
                reciprocal_pairs + explicit_events - reciprocal_pairs_with_event
            ),
        }

    def close(self) -> None:
        self.connection.close()
        self.path.unlink(missing_ok=True)

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
