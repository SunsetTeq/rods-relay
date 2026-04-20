from datetime import datetime
from pathlib import Path


class RelayScreenshotService:
    def __init__(self, base_dir: str) -> None:
        self.project_root = Path(__file__).resolve().parents[3]
        raw_base_dir = Path(base_dir)
        self.base_dir = (
            raw_base_dir.resolve()
            if raw_base_dir.is_absolute()
            else (self.project_root / raw_base_dir).resolve()
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_event_bytes(
        self,
        event_id: int,
        variant: str,
        content: bytes,
        frame_timestamp: str | None,
        content_type: str | None,
    ) -> str | None:
        if not content:
            return None

        timestamp = self._parse_timestamp(frame_timestamp)
        day_dir = self.base_dir / timestamp.strftime("%Y") / timestamp.strftime("%m") / timestamp.strftime("%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        suffix = ".png" if (content_type or "").lower().endswith("png") else ".jpg"
        target_path = day_dir / f"event_{event_id}_{variant}{suffix}"
        target_path.write_bytes(content)
        return self._to_posix_relative(target_path)

    def get_absolute_path(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.base_dir / candidate).resolve()
            if not resolved.exists():
                legacy_resolved = (self.project_root / candidate).resolve()
                if legacy_resolved.exists():
                    resolved = legacy_resolved

        if self.base_dir not in resolved.parents and resolved != self.base_dir:
            raise ValueError("Requested screenshot path is outside of the storage directory")
        return resolved

    def _parse_timestamp(self, frame_timestamp: str | None) -> datetime:
        if not frame_timestamp:
            return datetime.utcnow()

        normalized = frame_timestamp.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.utcnow()

    def _to_posix_relative(self, path: Path | None) -> str | None:
        if path is None:
            return None

        try:
            relative_path = path.resolve().relative_to(self.base_dir)
        except ValueError:
            return path.resolve().as_posix()

        return relative_path.as_posix()
