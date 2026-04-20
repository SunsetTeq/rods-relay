import sqlite3
from datetime import datetime, timezone
import json
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relay_camera_states (
                    source_id TEXT PRIMARY KEY,
                    active_camera_id TEXT,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relay_camera_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    command_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error_text TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_delivered_at TEXT,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relay_vision_states (
                    source_id TEXT PRIMARY KEY,
                    frame_id INTEGER NOT NULL,
                    frame_timestamp TEXT,
                    detections_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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
            self._ensure_column(connection, "relay_camera_states", "active_camera_id", "TEXT")
            self._ensure_column(connection, "relay_camera_states", "state_json", "TEXT")
            self._ensure_column(connection, "relay_camera_states", "updated_at", "TEXT")
            self._ensure_column(connection, "relay_camera_commands", "attempts", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "relay_camera_commands", "error_text", "TEXT")
            self._ensure_column(connection, "relay_camera_commands", "result_json", "TEXT")
            self._ensure_column(connection, "relay_camera_commands", "last_delivered_at", "TEXT")
            self._ensure_column(connection, "relay_camera_commands", "completed_at", "TEXT")
            self._ensure_column(connection, "relay_vision_states", "frame_id", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "relay_vision_states", "frame_timestamp", "TEXT")
            self._ensure_column(
                connection,
                "relay_vision_states",
                "detections_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(connection, "relay_vision_states", "payload_json", "TEXT")
            self._ensure_column(connection, "relay_vision_states", "updated_at", "TEXT")
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

    def upsert_camera_state(
        self,
        source_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        updated_at = datetime.now(timezone.utc).isoformat()
        serialized_state = json.dumps(state)
        active_camera_id = state.get("active_camera_id")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO relay_camera_states (
                    source_id,
                    active_camera_id,
                    state_json,
                    updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    active_camera_id = excluded.active_camera_id,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    active_camera_id,
                    serialized_state,
                    updated_at,
                ),
            )
            connection.commit()

        return self.get_camera_state(source_id) or {
            **state,
            "source_id": source_id,
            "updated_at": updated_at,
        }

    def get_camera_state(self, source_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT source_id, active_camera_id, state_json, updated_at
                FROM relay_camera_states
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()

        if row is None:
            return None

        payload = json.loads(row["state_json"])
        return {
            **payload,
            "source_id": row["source_id"],
            "active_camera_id": row["active_camera_id"],
            "updated_at": row["updated_at"],
        }

    def upsert_detection_frame(
        self,
        source_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        updated_at = datetime.now(timezone.utc).isoformat()
        serialized_payload = json.dumps(payload)
        frame_id = int(payload["frame_id"])
        frame_timestamp = payload.get("frame_timestamp")
        detections_count = int(payload["detections_count"])

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO relay_vision_states (
                    source_id,
                    frame_id,
                    frame_timestamp,
                    detections_count,
                    payload_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    frame_id = excluded.frame_id,
                    frame_timestamp = excluded.frame_timestamp,
                    detections_count = excluded.detections_count,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    frame_id,
                    frame_timestamp,
                    detections_count,
                    serialized_payload,
                    updated_at,
                ),
            )
            connection.commit()

        stored_payload = self.get_detection_frame(source_id)
        if stored_payload is not None:
            return stored_payload

        return {
            **payload,
            "source_id": source_id,
            "updated_at": updated_at,
        }

    def get_detection_frame(self, source_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    source_id,
                    frame_id,
                    frame_timestamp,
                    detections_count,
                    payload_json,
                    updated_at
                FROM relay_vision_states
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()

        if row is None:
            return None

        payload = json.loads(row["payload_json"])
        return {
            **payload,
            "source_id": row["source_id"],
            "frame_id": int(row["frame_id"]),
            "frame_timestamp": row["frame_timestamp"],
            "detections_count": int(row["detections_count"]),
            "updated_at": row["updated_at"],
        }

    def get_current_objects(self, source_id: str) -> dict[str, Any] | None:
        payload = self.get_detection_frame(source_id)
        if payload is None:
            return None

        detections = payload.get("detections", [])
        objects: list[dict[str, Any]] = []
        for index, item in enumerate(detections):
            track_id = item.get("track_id")
            objects.append(
                {
                    "id": str(track_id) if track_id is not None else f"det-{index + 1}",
                    "track_id": track_id,
                    "class_id": int(item["class_id"]),
                    "class_name": str(item["class_name"]),
                    "confidence": float(item["confidence"]),
                }
            )

        return {
            "source_id": source_id,
            "frame_id": int(payload["frame_id"]),
            "frame_timestamp": payload.get("frame_timestamp"),
            "objects_count": len(objects),
            "objects": objects,
            "updated_at": payload.get("updated_at"),
        }

    def create_camera_command(
        self,
        source_id: str,
        command_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload)

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO relay_camera_commands (
                    source_id,
                    command_type,
                    payload_json,
                    status,
                    attempts,
                    error_text,
                    result_json,
                    created_at,
                    updated_at,
                    last_delivered_at,
                    completed_at
                ) VALUES (?, ?, ?, 'pending', 0, NULL, NULL, ?, ?, NULL, NULL)
                """,
                (
                    source_id,
                    command_type,
                    payload_json,
                    now,
                    now,
                ),
            )
            connection.commit()
            command_id = int(cursor.lastrowid)

        return self.get_camera_command(command_id) or {
            "id": command_id,
            "source_id": source_id,
            "command_type": command_type,
            "payload": payload,
            "status": "pending",
            "attempts": 0,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "error": None,
            "result": None,
        }

    def claim_next_camera_command(
        self,
        source_id: str,
        retry_after_seconds: int,
    ) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        retry_before = datetime.fromtimestamp(
            now.timestamp() - retry_after_seconds,
            tz=timezone.utc,
        ).isoformat()

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM relay_camera_commands
                WHERE source_id = ?
                  AND (
                    status = 'pending'
                    OR (
                        status = 'sent'
                        AND (
                            last_delivered_at IS NULL
                            OR last_delivered_at <= ?
                        )
                    )
                  )
                ORDER BY id ASC
                LIMIT 1
                """,
                (
                    source_id,
                    retry_before,
                ),
            ).fetchall()
            row = rows[0] if rows else None
            if row is None:
                return None

            updated_at = now.isoformat()
            connection.execute(
                """
                UPDATE relay_camera_commands
                SET
                    status = 'sent',
                    attempts = attempts + 1,
                    updated_at = ?,
                    last_delivered_at = ?
                WHERE id = ?
                """,
                (
                    updated_at,
                    updated_at,
                    int(row["id"]),
                ),
            )
            connection.commit()

        return self.get_camera_command(int(row["id"]))

    def complete_camera_command(
        self,
        command_id: int,
        ok: bool,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        updated_at = datetime.now(timezone.utc).isoformat()
        status = "completed" if ok else "failed"
        result_json = json.dumps(result) if result is not None else None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE relay_camera_commands
                SET
                    status = ?,
                    error_text = ?,
                    result_json = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    error,
                    result_json,
                    updated_at,
                    updated_at,
                    command_id,
                ),
            )
            connection.commit()

        return self.get_camera_command(command_id)

    def get_camera_command(self, command_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM relay_camera_commands
                WHERE id = ?
                """,
                (command_id,),
            ).fetchone()

        if row is None:
            return None

        payload = json.loads(row["payload_json"])
        result = json.loads(row["result_json"]) if row["result_json"] else None
        return {
            "id": int(row["id"]),
            "source_id": row["source_id"],
            "command_type": row["command_type"],
            "payload": payload,
            "status": row["status"],
            "attempts": int(row["attempts"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "error": row["error_text"],
            "result": result,
        }

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
