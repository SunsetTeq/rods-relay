import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RelayEventRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def initialize(self) -> None:
        try:
            self._initialize_schema()
        except sqlite3.Error:
            self._recover_broken_database()
            self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relay_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_event_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    class_id INTEGER,
                    track_id INTEGER,
                    confidence REAL NOT NULL,
                    state_key TEXT NOT NULL,
                    first_seen_frame_id INTEGER NOT NULL,
                    confirmed_frame_id INTEGER NOT NULL,
                    last_seen_frame_id INTEGER NOT NULL,
                    stable_frames_required INTEGER NOT NULL,
                    absent_frames_required INTEGER NOT NULL,
                    cooldown_seconds INTEGER NOT NULL,
                    source_frame_width INTEGER,
                    source_frame_height INTEGER,
                    frame_timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    received_at TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    screenshot_annotated_path TEXT,
                    UNIQUE(source_id, source_event_id)
                )
                """
            )
            self._ensure_column(connection, "relay_events", "track_id", "INTEGER")
            self._ensure_column(connection, "relay_events", "updated_at", "TEXT")
            self._ensure_column(
                connection,
                "relay_events",
                "source_frame_width",
                "INTEGER",
            )
            self._ensure_column(
                connection,
                "relay_events",
                "source_frame_height",
                "INTEGER",
            )
            self._ensure_column(
                connection,
                "relay_events",
                "screenshot_annotated_path",
                "TEXT",
            )
            connection.commit()

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in existing_columns:
            return

        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )

    def _recover_broken_database(self) -> None:
        journal_path = self.database_path.with_name(f"{self.database_path.name}-journal")
        if journal_path.exists():
            try:
                journal_path.unlink(missing_ok=True)
            except PermissionError:
                pass

        if self.database_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_path = self.database_path.with_name(
                f"{self.database_path.stem}.corrupt-{timestamp}{self.database_path.suffix}"
            )
            try:
                self.database_path.replace(backup_path)
            except PermissionError:
                pass

    def upsert_event(
        self,
        source_id: str,
        source_event: dict[str, Any],
    ) -> tuple[int, bool]:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id, received_at, screenshot_annotated_path
                FROM relay_events
                WHERE source_id = ? AND source_event_id = ?
                """,
                (source_id, int(source_event["id"])),
            ).fetchone()

            ingested_at = datetime.now(timezone.utc).isoformat()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO relay_events (
                        source_id,
                        source_event_id,
                        event_type,
                        class_name,
                        class_id,
                        track_id,
                        confidence,
                        state_key,
                        first_seen_frame_id,
                        confirmed_frame_id,
                        last_seen_frame_id,
                        stable_frames_required,
                        absent_frames_required,
                        cooldown_seconds,
                        source_frame_width,
                        source_frame_height,
                        frame_timestamp,
                        created_at,
                        updated_at,
                        received_at,
                        ingested_at,
                        screenshot_annotated_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        int(source_event["id"]),
                        source_event["event_type"],
                        source_event["class_name"],
                        source_event.get("class_id"),
                        source_event.get("track_id"),
                        float(source_event["confidence"]),
                        source_event["state_key"],
                        int(source_event["first_seen_frame_id"]),
                        int(source_event["confirmed_frame_id"]),
                        int(source_event["last_seen_frame_id"]),
                        int(source_event["stable_frames_required"]),
                        int(source_event["absent_frames_required"]),
                        int(source_event["cooldown_seconds"]),
                        source_event.get("source_frame_width"),
                        source_event.get("source_frame_height"),
                        source_event["frame_timestamp"],
                        source_event["created_at"],
                        source_event.get("updated_at"),
                        ingested_at,
                        ingested_at,
                        None,
                    ),
                )
                connection.commit()
                return int(cursor.lastrowid), True

            event_id = int(existing["id"])
            connection.execute(
                """
                UPDATE relay_events
                SET
                    event_type = ?,
                    class_name = ?,
                    class_id = ?,
                    track_id = ?,
                    confidence = ?,
                    state_key = ?,
                    first_seen_frame_id = ?,
                    confirmed_frame_id = ?,
                    last_seen_frame_id = ?,
                    stable_frames_required = ?,
                    absent_frames_required = ?,
                    cooldown_seconds = ?,
                    source_frame_width = ?,
                    source_frame_height = ?,
                    frame_timestamp = ?,
                    created_at = ?,
                    updated_at = ?,
                    ingested_at = ?
                WHERE id = ?
                """,
                (
                    source_event["event_type"],
                    source_event["class_name"],
                    source_event.get("class_id"),
                    source_event.get("track_id"),
                    float(source_event["confidence"]),
                    source_event["state_key"],
                    int(source_event["first_seen_frame_id"]),
                    int(source_event["confirmed_frame_id"]),
                    int(source_event["last_seen_frame_id"]),
                    int(source_event["stable_frames_required"]),
                    int(source_event["absent_frames_required"]),
                    int(source_event["cooldown_seconds"]),
                    source_event.get("source_frame_width"),
                    source_event.get("source_frame_height"),
                    source_event["frame_timestamp"],
                    source_event["created_at"],
                    source_event.get("updated_at"),
                    ingested_at,
                    event_id,
                ),
            )
            connection.commit()
            return event_id, False

    def update_event_screenshots(
        self,
        event_id: int,
        screenshot_annotated_path: str | None,
    ) -> None:
        with self._connect() as connection:
            current = connection.execute(
                """
                SELECT screenshot_annotated_path
                FROM relay_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
            if current is None:
                return

            connection.execute(
                """
                UPDATE relay_events
                SET
                    screenshot_annotated_path = ?,
                    ingested_at = ?
                WHERE id = ?
                """,
                (
                    screenshot_annotated_path or current["screenshot_annotated_path"],
                    datetime.now(timezone.utc).isoformat(),
                    event_id,
                ),
            )
            connection.commit()

    def count_events(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM relay_events"
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    def get_event_by_id(self, event_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                {self._base_event_select_sql()}
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_recent_events(self, limit: int) -> list[dict[str, Any]]:
        rows, _ = self.list_events_page(limit=limit)
        return rows

    def list_events_page(
        self,
        limit: int,
        before_id: int | None = None,
        after_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        if before_id is not None and after_id is not None:
            raise ValueError("before_id and after_id cannot be used together")

        params: list[Any] = []
        where_clause = ""
        order = "DESC"

        if before_id is not None:
            where_clause = "WHERE id < ?"
            params.append(before_id)
        elif after_id is not None:
            where_clause = "WHERE id > ?"
            params.append(after_id)
            order = "ASC"

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                {self._base_event_select_sql()}
                {where_clause}
                ORDER BY id {order}
                LIMIT ?
                """,
                (*params, limit + 1),
            ).fetchall()

        has_more = len(rows) > limit
        page_rows = rows[:limit]
        return [dict(row) for row in page_rows], has_more

    def _base_event_select_sql(self) -> str:
        return """
            SELECT
                id,
                source_id,
                source_event_id,
                event_type,
                class_name,
                class_id,
                track_id,
                confidence,
                state_key,
                first_seen_frame_id,
                confirmed_frame_id,
                last_seen_frame_id,
                stable_frames_required,
                absent_frames_required,
                cooldown_seconds,
                source_frame_width,
                source_frame_height,
                frame_timestamp,
                created_at,
                updated_at,
                received_at,
                ingested_at,
                screenshot_annotated_path
            FROM relay_events
        """
