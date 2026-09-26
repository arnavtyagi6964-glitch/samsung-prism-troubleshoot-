from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import time

from app.services import (
    extract_context_response,
    get_cached_response,
    set_cached_response,
    get_siis_search,
)
from app.schemas.models import ContextDeeplinkResponse


app = FastAPI(title="Troubleshooting Engine API", version="1.0.0")


class TroubleshootRequest(BaseModel):
    query: str
    siis_response: Optional[str] = None


class TroubleshootResponse(BaseModel):
    success: bool
    data: Optional[ContextDeeplinkResponse] = None
    error: Optional[str] = None
    cached: Optional[bool] = None
    cache_score: Optional[float] = None
    cache_matched_query: Optional[str] = None
    latency_ms: float


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok")


@app.post("/v1/troubleshoot", response_model=TroubleshootResponse)
async def troubleshoot(request: TroubleshootRequest):
    start_time = time.perf_counter()

    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    # Determine SIIS response text to use
    if request.siis_response and request.siis_response.strip():
        siis_text = request.siis_response.strip()
    else:
        # Auto-lookup best matching SIIS response from dataset
        siis_search = get_siis_search()
        match = siis_search.find_best_match(request.query, score_cutoff=50)
        if not match:
            raise HTTPException(
                status_code=404,
                detail="No matching SIIS response found for query. Provide siis_response explicitly or check query spelling.",
            )
        matched_entry, match_score = match
        siis_text = siis_search.get_combined_text(matched_entry)
        print(f"=== AUTO SIIS LOOKUP ===")
        print(f"Query: '{request.query}'")
        print(f"Matched: '{matched_entry.original_query}' (score: {match_score})")
        print(f"Using SIIS title: '{matched_entry.siis_title}'")
        print(f"=== END AUTO SIIS LOOKUP ===")

    try:
        cached = get_cached_response(request.query)

        if cached:
            response, score, matched_query = cached
            cached_flag = True
            cache_score = score
            cache_matched = matched_query
        else:
            response = extract_context_response(request.query, siis_text)
            cached_flag = False
            cache_score = None
            cache_matched = None

        latency_ms = (time.perf_counter() - start_time) * 1000

        return TroubleshootResponse(
            success=True,
            data=response,
            cached=cached_flag,
            cache_score=cache_score,
            cache_matched_query=cache_matched,
            latency_ms=round(latency_ms, 2),
        )
    except ValueError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return TroubleshootResponse(
            success=False,
            error=str(e),
            latency_ms=round(latency_ms, 2),
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return TroubleshootResponse(
            success=False,
            error=f"Internal error: {str(e)}",
            latency_ms=round(latency_ms, 2),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)