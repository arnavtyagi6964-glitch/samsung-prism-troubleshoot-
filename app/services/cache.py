from typing import Optional, Dict, Tuple

from rapidfuzz import fuzz

from app.schemas.models import ContextDeeplinkResponse


_cache: Dict[str, ContextDeeplinkResponse] = {}
_SIMILARITY_THRESHOLD = 85


def get_cached_response(query: str) -> Optional[Tuple[ContextDeeplinkResponse, int, str]]:
    if not _cache:
        return None

    best_match = None
    best_score = 0

    for cached_query in _cache:
        score = fuzz.token_set_ratio(query, cached_query)
        if score >= _SIMILARITY_THRESHOLD and score > best_score:
            best_score = score
            best_match = cached_query

    if best_match:
        return _cache[best_match], best_score, best_match

    return None


def set_cached_response(query: str, response: ContextDeeplinkResponse) -> None:
    _cache[query] = response


def clear_cache() -> None:
    _cache.clear()


def get_cache_stats() -> Dict:
    return {
        "size": len(_cache),
        "queries": list(_cache.keys()),
    }