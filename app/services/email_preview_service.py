from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailPreview:
    dealer_id: int
    dealer_name: str | None
    to: str
    subject: str
    body: str
