"""Append-only audit helpers for HMIS workflows."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import HmisActionType, HmisSyncEvent


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class HmisAuditStore:
    path: Path | None = None
    _events: list[HmisSyncEvent] = field(default_factory=list)
    _loaded: bool = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.path is None or not self.path.exists():
            return
        events: list[HmisSyncEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            events.append(HmisSyncEvent(**payload))
        self._events = events

    def emit(self, event: HmisSyncEvent) -> HmisSyncEvent:
        self._ensure_loaded()
        self._events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event

    def record(
        self,
        *,
        action_type: HmisActionType,
        actor_id: str,
        local_ref: str | None = None,
        external_ref: str | None = None,
        adapter_name: str | None = None,
        status: str = "pending",
        response_summary: str | None = None,
        retry_count: int = 0,
        metadata: Mapping[str, Any] | None = None,
    ) -> HmisSyncEvent:
        return self.emit(
            HmisSyncEvent(
                event_id=str(uuid4()),
                action_type=action_type,
                actor_id=actor_id,
                local_ref=local_ref,
                external_ref=external_ref,
                adapter_name=adapter_name,
                status=status,  # type: ignore[arg-type]
                response_summary=response_summary,
                occurred_at=_utc_now(),
                retry_count=retry_count,
                metadata=dict(metadata or {}),
            )
        )

    def list_events(
        self,
        *,
        action_type: HmisActionType | None = None,
        local_ref: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[HmisSyncEvent]:
        self._ensure_loaded()
        items = list(self._events)
        if action_type is not None:
            items = [item for item in items if item.action_type == action_type]
        if local_ref is not None:
            items = [item for item in items if item.local_ref == local_ref]
        if status is not None:
            items = [item for item in items if item.status == status]
        items.sort(key=lambda item: (item.occurred_at or "", item.event_id))
        if limit is not None:
            return items[-max(0, limit) :]
        return items

    def latest_for_local_ref(self, local_ref: str) -> HmisSyncEvent | None:
        events = self.list_events(local_ref=local_ref)
        return events[-1] if events else None


__all__ = ["HmisAuditStore"]
