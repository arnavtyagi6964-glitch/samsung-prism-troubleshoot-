from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import extract_context_response
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


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok")


@app.post("/v1/troubleshoot", response_model=TroubleshootResponse)
async def troubleshoot(request: TroubleshootRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    if not request.siis_response or not request.siis_response.strip():
        raise HTTPException(status_code=400, detail="siis_response is required")

    try:
        result = extract_context_response(request.query, request.siis_response)

        return TroubleshootResponse(
            success=True,
            data=result,
        )
    except ValueError as e:
        return TroubleshootResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        return TroubleshootResponse(
            success=False,
            error=f"Internal error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)