# 🅿️ Smart Parking Slot Booker — MCP + RAG + Agentic AI

> A full-stack intelligent parking management system built with **Flask** (Python) and **React** (Vite).  
> Implements **Model Context Protocol (MCP)**, **Retrieval-Augmented Generation (RAG)**, a **multi-agent architecture**, and production-grade **guardrails + observability**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev)
[![Tests](https://img.shields.io/badge/Tests-pytest-yellow)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](#)

---

## Table of Contents

1. [Project Description](#project-description)
2. [Architecture Diagram](#architecture-diagram)
3. [MCP — Model Context Protocol](#mcp--model-context-protocol)
4. [RAG — Retrieval-Augmented Generation](#rag--retrieval-augmented-generation)
5. [Agentic System](#agentic-system)
6. [Multi-Agent Workflow](#multi-agent-workflow)
7. [Guardrails](#guardrails)
8. [Observability](#observability)
9. [Project Structure](#project-structure)
10. [API Documentation](#api-documentation)
11. [Setup & Run](#setup--run)
12. [Running Tests](#running-tests)
13. [Screenshots](#screenshots)
14. [Future Improvements](#future-improvements)

---

## Project Description

**Smart Parking Slot Booker** is a real-time parking reservation system for Chennai, India.  
Users can browse parking locations, view live slot availability on a satellite map, and book or release slots — all through a modern React UI or via a **natural-language assistant**.

### What makes this system "smart"?

| Feature | Implementation |
|---|---|
| Natural Language Input | "Book parking near mall for 2 hours" |
| Intent Understanding | MCP Intent Engine with confidence scoring |
| Factual Grounding | RAG knowledge base retrieval |
| Autonomous Routing | Multi-agent orchestrator |
| Input Safety | Guardrails (injection, rate limiting, bounds) |
| Full Observability | Trace-ID logging across all layers |
| Auto-Expiry | Per-booking countdown timers (backend + frontend) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND  (:3000)                       │
│                                                                       │
│  NLPInput ─── LocationSelector ─── SlotGrid ─── BookingPanel        │
│                     ↕ useParking.js (central state hook)             │
└──────────────────────────────┬──────────────────────────────────────┘
                                │  HTTP + Vite proxy /api → :5000
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FLASK BACKEND  (:5000)                         │
│                                                                       │
│   app.py  (create_app factory)                                        │
│     │                                                                 │
│     ├── /api/locations  ──►  SlotAgent.get_locations()               │
│     ├── /api/slots      ──►  SlotAgent.get_slots()                   │
│     ├── /api/book       ──►  BookingAgent.book()                     │
│     ├── /api/release    ──►  BookingAgent.release()                  │
│     ├── /api/bookings   ──►  BookingService.get_active_bookings()    │
│     └── /api/nlp        ──►  AgentOrchestrator.process_nlp_request() │
│                                         │                             │
│                    ┌────────────────────┤                             │
│                    ▼                    ▼                             │
│            ┌──────────────┐    ┌──────────────────┐                  │
│            │  NLPAgent    │    │ AgentOrchestrator │                  │
│            │  ─────────── │    │  routes intent to │                  │
│            │  Guardrails  │    │  SlotAgent or     │                  │
│            │  IntentEngine│    │  BookingAgent     │                  │
│            │  RAGModule   │    └──────────────────┘                  │
│            │  Validator   │                                           │
│            └──────────────┘                                           │
│                                                                       │
│   ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│   │ SlotService │  │ BookingService  │  │  MCP Layer               │ │
│   │ (JSON I/O)  │  │ (in-memory +    │  │  intent_engine.py        │ │
│   │             │  │  auto-release   │  │  validator.py            │ │
│   └──────┬──────┘  │  timers)        │  │  guardrails.py           │ │
│          │         └────────────────-┘  │  rag_module.py           │ │
│          ▼                               └─────────────────────────┘ │
│   parking_data.json  ←→  parking_knowledge.json                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## MCP — Model Context Protocol

**MCP (Model Context Protocol)** is a design pattern used in this project to create a unified, validated pipeline through which every user action — whether from a structured API call or natural language — must pass before being executed.

### Core Concept

Instead of each endpoint implementing its own ad-hoc validation, all actions are converted into a **structured intent object**:

```json
{
  "intent":     "BOOK_SLOT",
  "params": {
    "location": "mall-parking",
    "duration": 2,
    "slot_id":  null
  },
  "confidence": 1.0,
  "rag_context": [...]
}
```

This intent is then validated by `IntentValidator` before any booking logic runs.

### Intent Types

| Constant | Value | Description |
|---|---|---|
| `INTENT_VIEW_SLOTS` | `"VIEW_SLOTS"` | Query slot availability at a location |
| `INTENT_BOOK_SLOT` | `"BOOK_SLOT"` | Book a parking slot |
| `INTENT_RELEASE_SLOT` | `"RELEASE_SLOT"` | Release / cancel a booking |
| `INTENT_UNKNOWN` | `"UNKNOWN"` | Fallback when intent cannot be determined |

### MCP Pipeline (two paths)

**Structured API call:**
```
Request → Guardrails → create_structured_intent() → validate_intent() → Service
```

**Natural Language call:**
```
Text → Guardrails → IntentEngine.parse() → RAGModule.enrich_intent() → validate_intent() → Orchestrator routing
```

### Confidence Scoring

NLP-parsed intents receive a 0–1 confidence score:

| Factor Detected | Points Added |
|---|---|
| Recognised intent keyword | +0.4 |
| Location resolved | +0.3 |
| Duration extracted | +0.3 |
| **Maximum** | **1.0** |

Intents with confidence < 0.4 are **not executed** — the user receives a clarification message.

---

## RAG — Retrieval-Augmented Generation

**RAG (Retrieval-Augmented Generation)** grounds the system's NLP responses in a factual knowledge base rather than relying on pure pattern matching.

### How it works

1. `parking_knowledge.json` contains **13 structured knowledge entries** across four categories: `pricing`, `location`, `policy`, `tips`.
2. When a user submits a natural-language query, `RAGModule.retrieve_context()` scores every knowledge entry by counting keyword overlaps with the query tokens.
3. The top-3 most relevant entries are attached to the MCP intent dict as `rag_context` and `rag_context_text`.
4. The NLP endpoint returns this context to the frontend, which can display it as grounded information.

### Example

**Query:** `"how much does parking cost at mall for 3 hours"`

**Retrieved context:**
```
[PRICING] Standard parking rate is ₹20 per hour for all locations.
[PRICING] Minimum booking duration is 1 hour; maximum is 24 hours. Cost = duration × ₹20.
[LOCATION] Mall Parking (Express Avenue): Dedicated lot for Express Avenue mall visitors.
```

### Knowledge Base Structure

```json
{
  "id":       "pricing-standard",
  "category": "pricing",
  "keywords": ["price", "cost", "rate", "charge", "fee"],
  "content":  "Standard parking rate is ₹20 per hour..."
}
```

> **Note:** This is a simulated RAG using keyword scoring rather than vector embeddings. A production upgrade would use sentence-transformers + a vector store (FAISS / ChromaDB / Pinecone).

---

## Agentic System

The backend is organised as a **multi-agent system** where each agent has a single responsibility and operates through the MCP pipeline.

### Agents

| Agent | File | Responsibility |
|---|---|---|
| **NLPAgent** | `agents/nlp_agent.py` | Parse text → intent via Guardrails + IntentEngine + RAG |
| **BookingAgent** | `agents/booking_agent.py` | Book and release slots via BookingService |
| **SlotAgent** | `agents/slot_agent.py` | Query locations and slot availability via SlotService |
| **AgentOrchestrator** | `agents/nlp_agent.py` | Route NLP requests to the correct agent |

### Agent Interface Contract

Every agent method returns a plain `dict`:
- **Success:** contains the response payload (e.g., `{"booking": {...}}`)
- **Failure:** contains `{"error": "descriptive message"}`

Flask routes simply check `if "error" in result` to determine HTTP status codes.

---

## Multi-Agent Workflow

### NLP Request Flow

```
POST /api/nlp  {"text": "Book parking near mall for 2 hours"}
        │
        ▼
  AgentOrchestrator.process_nlp_request()
        │
        ├─1─▶  Guardrails.check_rate_limit()         [reject if exceeded]
        │
        ├─2─▶  NLPAgent.process()
        │           ├─ Guardrails.validate_text_input()
        │           ├─ IntentEngine.parse()           → intent=BOOK_SLOT, conf=1.0
        │           ├─ RAGModule.enrich_intent()      → attach RAG context
        │           └─ IntentValidator.validate()
        │
        ├─3─▶  Route by intent:
        │           BOOK_SLOT  → return prefill for UI confirmation
        │           VIEW_SLOTS → SlotAgent.get_slots() → return live data
        │           RELEASE    → return prefill for UI confirmation
        │
        └─4─▶  Return enriched response dict (with trace_id + context)
```

### Direct API Request Flow (e.g. POST /api/book)

```
POST /api/book  {"location": "anna-nagar", "duration": 2}
        │
        ├─1─▶  Guardrails.check_rate_limit()
        ├─2─▶  BookingAgent.book()
        │           ├─ Guardrails.validate_duration()
        │           ├─ Guardrails.sanitize_location_id()
        │           ├─ IntentEngine.create_structured_intent()
        │           ├─ IntentValidator.validate()
        │           └─ BookingService.create_booking()
        │                   ├─ SlotService.find_first_available_slot()
        │                   ├─ SlotService.mark_slot_occupied()  [persisted]
        │                   └─ schedule auto-release timer
        └─▶  201 response with booking object
```

---

## Guardrails

Guardrails are enforced **before** any agent or service logic runs.

### Implemented Guards

| Guard | Rule | Error Returned |
|---|---|---|
| Empty input | Text must not be blank | 400 Bad Request |
| Input length | Max 500 characters | 400 Bad Request |
| Injection patterns | No HTML, SQL, JS, path traversal | 400 Bad Request |
| Duration bounds | Must be integer 1–24 | 400 / 409 |
| Location ID format | Only `[a-zA-Z0-9-]` max 50 chars | 400 Bad Request |
| Rate limiting | Max 30 requests per 60 seconds per IP | 429 Too Many Requests |
| Slot conflict | Cannot book an already-occupied slot | 409 Conflict |
| Low NLP confidence | Intent not clear enough to execute | Fallback message |

### Rate Limiter Algorithm

Uses a **sliding-window** counter (per client IP, in-memory):

```python
window_start = now - WINDOW_SECONDS
timestamps = [ts for ts in store[ip] if ts > window_start]
if len(timestamps) >= MAX_REQUESTS:
    return False, "Rate limit exceeded"
store[ip].append(now)
```

---

## Observability

Every HTTP request is assigned a **trace ID** — an 8-character uppercase hex string (e.g. `A3F9BC12`).  
This trace ID is stamped on every log line generated during that request, across all modules.

### Log Format

```
2026-04-27 10:00:00 [agents.booking_agent] [INFO] [trace=A3F9BC12] BookingAgent.book(location=anna-nagar, duration=2h, slot=None)
2026-04-27 10:00:00 [services.booking_service] [INFO] [trace=A3F9BC12] BookingService: created booking F1E2D3C4 | slot=AN-001 | location=anna-nagar | duration=2h | cost=₹40
```

### Log Coverage

| Layer | What is logged |
|---|---|
| Flask routes | Method + path + trace_id |
| BookingAgent | Operation + params |
| SlotAgent | Operation + location |
| NLPAgent | Input text (truncated) + intent + confidence |
| IntentEngine | Each parsing step (intent, location, duration, confidence) |
| Guardrails | Rejections with reason |
| RAGModule | Number of entries loaded / retrieved |
| BookingService | Booking created / released (with cost) |
| SlotService | Data load/save operations, slot state changes |

---

## Project Structure

```
project-root/
│
├── README.md                          ← This file
│
├── backend/
│   ├── app.py                         ← Flask entry point + create_app() factory
│   ├── mcp_logic.py                   ← Legacy MCP module (preserved for reference)
│   ├── parking_data.json              ← Slot/location persistence (JSON)
│   ├── parking_knowledge.json         ← RAG knowledge base (13 entries)
│   ├── download_maps.py               ← Utility: capture Google Maps screenshots
│   ├── requirements.txt               ← Python dependencies
│   │
│   ├── mcp/                           ← Model Context Protocol layer
│   │   ├── __init__.py
│   │   ├── intent_engine.py           ← NLP parsing, location resolution, confidence
│   │   ├── validator.py               ← Intent parameter validation
│   │   ├── guardrails.py              ← Input safety + rate limiting
│   │   └── rag_module.py              ← Knowledge retrieval (simulated RAG)
│   │
│   ├── agents/                        ← Multi-agent system
│   │   ├── __init__.py
│   │   ├── nlp_agent.py               ← NLPAgent + AgentOrchestrator
│   │   ├── booking_agent.py           ← BookingAgent
│   │   └── slot_agent.py              ← SlotAgent
│   │
│   ├── services/                      ← Business logic / data access
│   │   ├── __init__.py
│   │   ├── slot_service.py            ← JSON file I/O for slots/locations
│   │   └── booking_service.py        ← In-memory bookings + auto-release timers
│   │
│   ├── utils/                         ← Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py                  ← All configuration constants
│   │   └── logger.py                  ← Trace-ID logging setup
│   │
│   ├── tests/                         ← Pytest test suite
│   │   ├── __init__.py
│   │   ├── conftest.py                ← Shared fixtures (temp data, flask client)
│   │   ├── test_booking.py            ← BookingService + BookingAgent unit tests
│   │   ├── test_mcp.py                ← IntentEngine, Validator, Guardrails, RAG tests
│   │   └── test_api.py                ← Flask endpoint integration tests
│   │
│   └── conftest.py                    ← sys.path setup for pytest
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js                 ← /api proxy → :5000
│   └── src/
│       ├── App.jsx
│       ├── hooks/useParking.js        ← Central state + all fetch calls
│       └── components/
│           ├── LocationSelector.jsx
│           ├── SlotGrid.jsx
│           ├── BookingPanel.jsx
│           ├── ActiveBookings.jsx
│           ├── Timer.jsx
│           └── NLPInput.jsx
│
└── docs/
    ├── architecture.md
    ├── mcp_design.md
    └── api_docs.md
```

---

## API Documentation

All endpoints served at `http://localhost:5000`. Frontend dev server proxies `/api/*` automatically.

### `GET /api/locations`

Returns all parking locations with real-time available-slot counts.

**Response `200`:**
```json
{
  "locations": [
    {
      "id": "anna-nagar",
      "name": "Anna Nagar",
      "address": "2nd Avenue, Anna Nagar, Chennai - 600040",
      "totalSlots": 8,
      "availableSlots": 7,
      "ratePerHour": 20
    }
  ]
}
```

---

### `GET /api/slots?location=<id>`

Slot-level detail for one location.

**Response `200`:**
```json
{
  "location": "Anna Nagar",
  "location_id": "anna-nagar",
  "ratePerHour": 20,
  "totalSlots": 8,
  "availableSlots": 7,
  "mapImageUrl": "/anna_nagar_map.png",
  "slots": [
    { "id": "AN-001", "status": "free" },
    { "id": "AN-002", "status": "occupied", "booking_id": "A1B2C3D4" }
  ]
}
```

**Error `400`** — missing `location` param  
**Error `404`** — unknown location ID

---

### `POST /api/book`

Book a parking slot.

**Request:**
```json
{
  "location": "anna-nagar",
  "duration": 2,
  "slot_id": "AN-003"
}
```
`slot_id` is optional. Omit to auto-assign the first free slot.

**Response `201`:**
```json
{
  "message": "Slot AN-003 booked successfully!",
  "booking": {
    "booking_id": "A1B2C3D4",
    "location_id": "anna-nagar",
    "location_name": "Anna Nagar",
    "slot_id": "AN-003",
    "duration": 2,
    "cost": 40,
    "currency": "₹",
    "booked_at": "2026-04-27T10:00:00",
    "expires_at": "2026-04-27T12:00:00",
    "status": "active"
  },
  "mcp_intent": { "intent": "BOOK_SLOT", "confidence": 1.0 },
  "trace_id": "A3F9BC12"
}
```

**Error `400`** — missing/invalid fields  
**Error `409`** — slot occupied or no slots available  
**Error `429`** — rate limit exceeded

---

### `POST /api/release`

Release an active booking.

**Request** (one of):
```json
{ "booking_id": "A1B2C3D4" }
{ "slot_id": "AN-003" }
```

**Response `200`:**
```json
{
  "message": "Slot AN-003 released successfully!",
  "booking_id": "A1B2C3D4",
  "mcp_intent": { "intent": "RELEASE_SLOT", "confidence": 1.0 },
  "trace_id": "B4E5F6G7"
}
```

**Error `400`** — neither `booking_id` nor `slot_id` provided  
**Error `404`** — booking not found or already released

---

### `GET /api/bookings`

All currently active bookings.

**Response `200`:**
```json
{ "bookings": [ { "booking_id": "...", "status": "active", ... } ] }
```

---

### `GET /api/booking/<booking_id>`

Single booking by ID.

**Response `200`:** `{ "booking": { ... } }`  
**Error `404`:** booking not found

---

### `POST /api/nlp`

Natural-language interface. Routes through the full MCP + RAG + agent pipeline.

**Request:**
```json
{ "text": "Book parking near mall for 2 hours" }
```

**Response `200`:**
```json
{
  "parsed": {
    "intent": "BOOK_SLOT",
    "params": { "location": "mall-parking", "duration": 2 },
    "confidence": 1.0,
    "rag_context": [ { "id": "pricing-standard", ... } ]
  },
  "action": "book",
  "prefill": { "location": "mall-parking", "duration": 2 },
  "message": "Ready to book at Mall Parking for 2 hour(s). Cost: ₹40. Confirm to proceed.",
  "context": "[PRICING] Standard parking rate is ₹20 per hour...",
  "trace_id": "C5D6E7F8"
}
```

**Error `400`** — empty text  
**Error `429`** — rate limit exceeded

---

## Setup & Run

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
# → http://localhost:5000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
# → http://localhost:3000  (proxies /api → :5000)
```

### Map Screenshots *(optional, one-time)*

```bash
pip install playwright
playwright install chromium
cd backend
python download_maps.py
# → saves PNG files to frontend/public/
```

---

## Running Tests

```bash
cd backend

# Install test dependencies (if not done already)
pip install pytest pytest-flask

# Run full test suite
pytest tests/ -v

# Run specific test file
pytest tests/test_mcp.py -v
pytest tests/test_booking.py -v
pytest tests/test_api.py -v

# Run with coverage (requires pytest-cov)
pip install pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

**Test count overview:**

| File | Tests | Scope |
|---|---|---|
| `test_mcp.py` | ~45 | IntentEngine, Validator, Guardrails, RAGModule |
| `test_booking.py` | ~20 | BookingService, BookingAgent |
| `test_api.py` | ~30 | All 7 Flask endpoints |

---

## Screenshots

> *(Replace with actual screenshots once UI is running)*

| Feature | Screenshot |
|---|---|
| Dashboard & Location Selector | `docs/screenshots/dashboard.png` |
| Slot Grid (satellite map view) | `docs/screenshots/slot_grid.png` |
| Booking Panel | `docs/screenshots/booking_panel.png` |
| Active Bookings with Timer | `docs/screenshots/active_bookings.png` |
| NLP Smart Assistant | `docs/screenshots/nlp_input.png` |

---

## Future Improvements

### Backend

- [ ] **Vector RAG**: Replace keyword scoring with `sentence-transformers` + FAISS for semantic similarity
- [ ] **Persistent bookings**: Store booking records in SQLite / PostgreSQL instead of in-memory
- [ ] **Authentication**: JWT-based user authentication and per-user booking history
- [ ] **WebSocket support**: Real-time slot updates pushed to all connected clients
- [ ] **Payment integration**: UPI / Razorpay API for actual payment processing
- [ ] **LLM integration**: Plug in an OpenAI / Ollama model for true natural language generation
- [ ] **Redis rate limiter**: Replace in-memory rate-store with Redis for multi-process support
- [ ] **Async Flask**: Migrate to async handlers or FastAPI for higher throughput

### Frontend

- [ ] **User accounts**: Login / signup with booking history view
- [ ] **Mobile responsiveness**: PWA with push notifications for booking reminders
- [ ] **Dark mode**: CSS variable–based theme switching
- [ ] **Slot reservation heatmap**: Time-based availability visualisation

### Infrastructure

- [ ] **Docker Compose**: Containerise backend + frontend for one-command startup
- [ ] **CI/CD**: GitHub Actions pipeline running pytest on every push
- [ ] **Structured logging**: JSON log format + ELK Stack / Grafana Loki integration
- [ ] **OpenTelemetry**: Distributed tracing with Jaeger for production observability

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest backend/tests/ -v`
4. Commit and push
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
