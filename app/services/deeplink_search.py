import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.schemas.models import Deeplink, ValidationDeepLink


@dataclass
class DeeplinkEntry:
    id: str
    deeplink: str
    description: str
    message: str
    originalType: str
    control_type: Optional[str]
    qna_description: str
    validation_deeplink: Optional[str]
    validation_key: Optional[str]

    @property
    def search_text(self) -> str:
        parts = [self.description, self.message, self.qna_description]
        return " ".join(p for p in parts if p)


class DeeplinkSearch:
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "deeplinks.json"
        self.data_path = Path(data_path)
        self.entries: List[DeeplinkEntry] = []
        self._load()

    def _load(self) -> None:
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("deeplinks", []):
            validation = item.get("validation") or {}
            entry = DeeplinkEntry(
                id=item["id"],
                deeplink=item["deeplink"],
                description=item.get("description", ""),
                message=item.get("message", ""),
                originalType=item.get("originalType", ""),
                control_type=item.get("control_type"),
                qna_description=item.get("qna_description", ""),
                validation_deeplink=validation.get("deeplink"),
                validation_key=validation.get("key"),
            )
            self.entries.append(entry)

    def search(
        self,
        query: str,
        limit: int = 10,
        score_cutoff: int = 60,
    ) -> List[Deeplink]:
        if not query.strip():
            return []

        scored = []
        for entry in self.entries:
            score = fuzz.token_set_ratio(query, entry.search_text)
            if score >= score_cutoff:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        results = []
        for score, entry in top:
            deeplink = Deeplink(
                deeplink=entry.deeplink,
                description=entry.description,
                message=entry.message,
                classes={"originalType": entry.originalType} if entry.originalType else None,
                originalType=entry.originalType,
            )
            results.append(deeplink)

        return results

    def search_with_scores(
        self,
        query: str,
        limit: int = 10,
        score_cutoff: int = 60,
    ) -> List[tuple[Deeplink, int]]:
        if not query.strip():
            return []

        scored = []
        for entry in self.entries:
            score = fuzz.token_set_ratio(query, entry.search_text)
            if score >= score_cutoff:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        results = []
        for score, entry in top:
            deeplink = Deeplink(
                deeplink=entry.deeplink,
                description=entry.description,
                message=entry.message,
                classes={"originalType": entry.originalType} if entry.originalType else None,
                originalType=entry.originalType,
            )
            results.append((deeplink, score))

        return results

    def get_by_id(self, deeplink_id: str) -> Optional[DeeplinkEntry]:
        for entry in self.entries:
            if entry.id == deeplink_id:
                return entry
        return None

    def get_validation_deeplink(self, deeplink_id: str) -> Optional[ValidationDeepLink]:
        entry = self.get_by_id(deeplink_id)
        if entry and entry.validation_deeplink and entry.validation_key:
            return ValidationDeepLink(
                deeplink=entry.validation_deeplink,
                key=entry.validation_key,
            )
        return None


_deeplink_search_instance: Optional[DeeplinkSearch] = None


def get_deeplink_search() -> DeeplinkSearch:
    global _deeplink_search_instance
    if _deeplink_search_instance is None:
        _deeplink_search_instance = DeeplinkSearch()
    return _deeplink_search_instance