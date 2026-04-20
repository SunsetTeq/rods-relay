from typing import Any


def serialize_event_row(row: dict[str, Any]) -> dict[str, Any]:
    event_id = int(row["id"])
    annotated_path = row.get("screenshot_annotated_path")

    return {
        "id": event_id,
        "source_id": row["source_id"],
        "source_event_id": int(row["source_event_id"]),
        "event_type": row["event_type"],
        "class_name": row["class_name"],
        "class_id": row.get("class_id"),
        "track_id": row.get("track_id"),
        "confidence": float(row["confidence"]),
        "state_key": row["state_key"],
        "first_seen_frame_id": int(row["first_seen_frame_id"]),
        "confirmed_frame_id": int(row["confirmed_frame_id"]),
        "last_seen_frame_id": int(row["last_seen_frame_id"]),
        "stable_frames_required": int(row["stable_frames_required"]),
        "absent_frames_required": int(row["absent_frames_required"]),
        "cooldown_seconds": int(row["cooldown_seconds"]),
        "source_frame_width": row.get("source_frame_width"),
        "source_frame_height": row.get("source_frame_height"),
        "frame_timestamp": row["frame_timestamp"],
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at"),
        "received_at": row["received_at"],
        "screenshot_annotated_url": (
            f"/api/v1/events/{event_id}/screenshots/annotated" if annotated_path else None
        ),
    }
