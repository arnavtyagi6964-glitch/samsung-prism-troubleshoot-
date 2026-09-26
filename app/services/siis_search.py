import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass
class SiisResponseEntry:
    id: str
    original_query: str
    siis_title: str
    siis_content: str

    @property
    def search_text(self) -> str:
        return f"{self.original_query} {self.siis_title} {self.siis_content}"


class SiisResponseSearch:
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "siis_responses.json"
        self.data_path = Path(data_path)
        self.entries: List[SiisResponseEntry] = []
        self._load()

    def _load(self) -> None:
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("responses", []):
            siis_resp = item.get("siis_response", {})
            entry = SiisResponseEntry(
                id=item["id"],
                original_query=item.get("original_query", ""),
                siis_title=siis_resp.get("title", ""),
                siis_content=siis_resp.get("content", ""),
            )
            self.entries.append(entry)

    def find_best_match(
        self,
        query: str,
        score_cutoff: int = 60,
    ) -> Optional[tuple[SiisResponseEntry, int]]:
        if not self.entries:
            return None

        best_match = None
        best_score = 0

        for entry in self.entries:
            score = fuzz.token_set_ratio(query, entry.search_text)
            if score >= score_cutoff and score > best_score:
                best_score = score
                best_match = entry

        if best_match:
            return best_match, best_score
        return None

    def get_combined_text(self, entry: SiisResponseEntry) -> str:
        return f"{entry.siis_title}: {entry.siis_content}"


_siis_search_instance: Optional[SiisResponseSearch] = None


def get_siis_search() -> SiisResponseSearch:
    global _siis_search_instance
    if _siis_search_instance is None:
        _siis_search_instance = SiisResponseSearch()
    return _siis_search_instance