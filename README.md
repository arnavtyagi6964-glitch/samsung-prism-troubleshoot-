# Troubleshooting Engine API

A FastAPI service that converts raw user complaints and official SIIS troubleshooting responses into structured, validated Goal objects with deeplink integration for Samsung/TechCorp device settings.

## What It Does

Given a user complaint (e.g., "My phone screen is blank after installing an app") and an official SIIS troubleshooting response, the API:
1. Extracts structured actions and steps from the SIIS text
2. Validates output against strict schema rules (Title Case action names, "It will..." descriptions, sentence-case titles)
3. Enriches each step with matching deeplinks from a 578-entry catalog
4. Caches results using semantic similarity (85%+ threshold) to avoid repeated LLM calls
5. Returns a `ContextDeeplinkResponse` with Goals, Actions, StepGroups, and actionable/validation deeplinks

## 5-Stage Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Input      │     │  LLM Extraction  │     │  Schema         │     │  Deeplink       │     │  Response   │
│  Validation │ ──▶ │  (Gemini 3.8)    │ ──▶ │  Validation     │ ──▶ │  Search         │ ──▶ │  Assembly   │
│             │     │                  │     │  (Pydantic)     │     │  (RapidFuzz)    │     │             │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────────┘     └─────────────┘
       ▲                                                                                      │
       │                              ┌──────────────────┐                                    │
       └─────────────────────────────▶│  Cache Layer     │◀───────────────────────────────────┘
                                      │  (In-Memory,     │
                                      │   85% similarity)│
                                      └──────────────────┘
```

1. **Schema Validation** (`app/schemas/`) — Pydantic models + custom validators for Title Case, word counts, "It will" prefix
2. **Deeplink Search** (`app/services/deeplink_search.py`) — RapidFuzz token-set-ratio search across 578 deeplinks (description, message, qna_description)
3. **LLM Extraction** (`app/services/llm_extraction.py`) — Gemini 3.8-flash with structured prompt, retry-with-backoff on 503
4. **Caching** (`app/services/cache.py`) — In-memory dict with semantic similarity matching (≥85%)
5. **API** (`app/main.py`) — FastAPI endpoints with latency tracking and cache metadata

## Setup

```bash
# Clone / navigate to project
cd troubleshooting-engine

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

**`.env` contents:**
```env
GEMINI_API_KEY=your-gemini-api-key-here
LLM_MODEL=gemini-3.8-flash
```

## Run the Server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Server starts at `http://localhost:8000`

- **Interactive docs (Swagger UI):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

### POST /v1/troubleshoot
Extract structured troubleshooting goal from complaint + SIIS response.

**Request:**
```json
{
  "query": "My TechCorp A15G tablet screen flashes and then goes completely blank whenever I tap to open an email in Gmail",
  "siis_response": "Smartphone,Others Mobile... Email server not responding... Step 1: Check Email Access on a PC..."
}
```

**Response (success):**
```json
{
  "success": true,
  "data": {
    "contexts": [{
      "goal": "Follow these steps to perform this Email Connection Troubleshooting",
      "title": "Email connection fix",
      "score": 0.85,
      "actions": [
        {
          "actionName": "Check Email Access on PC",
          "description": "It will verify your account status",
          "stepGroups": [{
            "steps": ["Try accessing your email on a personal computer..."],
            "actionableDeeplink": {"deeplink": "voiceassist://masked/act/...", ...},
            "validationDeeplink": {"deeplink": "voiceassist://masked/val/...", "key": "..."}
          }],
          "category": "manual"
        }
      ]
    }]
  },
  "cached": false,
  "cache_score": null,
  "cache_matched_query": null,
  "latency_ms": 1234.56
}
```

**Response (cache hit):**
```json
{
  "success": true,
  "data": {...},
  "cached": true,
  "cache_score": 93.33,
  "cache_matched_query": "My TechCorp A15G tablet screen flashes...",
  "latency_ms": 0.45
}
```

**Response (error):**
```json
{
  "success": false,
  "data": null,
  "error": "description must start with 'It will'",
  "cached": false,
  "latency_ms": 12.34
}
```

## Example curl Commands

```bash
# Health check
curl http://localhost:8000/health

# Troubleshoot - first request (cache miss, calls Gemini)
curl -X POST http://localhost:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My phone screen is blank after installing an app",
    "siis_response": "Step 1: Force restart by holding Power + Volume Down for 20 seconds. Step 2: Charge for 1 hour. Step 3: Check for physical damage."
  }'

# Troubleshoot - repeated request (cache hit, instant)
curl -X POST http://localhost:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My phone screen is blank after installing an app",
    "siis_response": "Step 1: Force restart by holding Power + Volume Down for 20 seconds. Step 2: Charge for 1 hour. Step 3: Check for physical damage."
  }'

# Troubleshoot - similar query (cache hit via 85%+ similarity)
curl -X POST http://localhost:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My phone screen went blank after I installed an application",
    "siis_response": "Step 1: Force restart by holding Power + Volume Down for 20 seconds. Step 2: Charge for 1 hour. Step 3: Check for physical damage."
  }'
```

## Project Structure

```
troubleshooting-engine/
├── app/
│   ├── main.py                 # FastAPI app + endpoints
│   ├── schemas/
│   │   ├── models.py           # Pydantic models (Goal, Action, StepGroup, Deeplink, etc.)
│   │   └── validation.py       # Custom validators (Title Case, word count, "It will")
│   └── services/
│       ├── deeplink_search.py  # RapidFuzz search over 578 deeplinks
│       ├── llm_extraction.py   # Gemini 3.8-flash extraction + retry logic
│       └── cache.py            # In-memory semantic cache (85% threshold)
├── data/
│   ├── deeplinks.json          # 578 deeplink entries
│   ├── siis_responses.json     # 20 official SIIS responses
│   ├── input.txt               # 20 raw user complaints
│   └── sample_output.json      # Formatting reference for LLM
├── requirements.txt
├── .env.example
└── README.md
```

## Running Tests

```bash
# Validation test (schema validators)
python3 test_validation_manual.py

# LLM extraction test (requires GEMINI_API_KEY)
python3 test_llm_extraction.py
```