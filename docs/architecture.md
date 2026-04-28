# System Architecture

## Overview

The Smart Parking Slot Booker is structured as a layered, agent-based system.
Each layer has a single responsibility and communicates only with the layer directly below it.

```
┌──────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                      │
│  React 19 + Vite 8  (frontend/src/)                       │
│  Components: LocationSelector, SlotGrid, BookingPanel,    │
│              ActiveBookings, NLPInput, Timer              │
│  State:      useParking.js (custom hook)                  │
│  Slot UI:    Pure-CSS animated parking lot grid           │
│              (no map images — occupancy bars + animations)│
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP REST  (/api/*)
                           │ Vite proxy → :5000
                           ▼
┌──────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                      │
│  Flask 3.1  (backend/app.py)                              │
│  • create_app() factory pattern                           │
│  • CORS enabled                                           │
│  • Request trace ID generation                            │
│  • HTTP status code mapping                               │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  AGENT ORCHESTRATION LAYER                │
│  agents/nlp_agent.py  (AgentOrchestrator)                 │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  NLPAgent   │  │ BookingAgent │  │   SlotAgent    │  │
│  │             │  │              │  │                │  │
│  │ Guardrails  │  │ Guardrails   │  │ Guardrails     │  │
│  │ IntentEngine│  │ IntentEngine │  │ IntentEngine   │  │
│  │ RAGModule   │  │ Validator    │  │ Validator      │  │
│  │ Validator   │  │              │  │                │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                     MCP LAYER                             │
│  mcp/intent_engine.py  — parsing + confidence scoring     │
│  mcp/validator.py      — intent parameter validation      │
│  mcp/guardrails.py     — safety + rate limiting           │
│  mcp/rag_module.py     — knowledge retrieval (RAG)        │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                           │
│  services/slot_service.py    — JSON file I/O              │
│  services/booking_service.py — in-memory state + timers   │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  PERSISTENCE LAYER                        │
│  parking_data.json        — slot status (persisted)       │
│  parking_knowledge.json   — RAG knowledge base            │
│  (bookings are in-memory only, reset on restart)          │
└──────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Flask (`app.py`)
- Application factory `create_app(data_file, knowledge_file)` — enables dependency injection for testing
- Route registration via closure over injected service/agent instances
- HTTP error code mapping (400 / 404 / 409 / 429 / 201)
- Trace ID generation per request

### Agents
- **NLPAgent**: Runs the full NLP pipeline (Guardrails → IntentEngine → RAG → Validator)
- **BookingAgent**: Validates + executes booking/release operations
- **SlotAgent**: Validates + queries location/slot data
- **AgentOrchestrator**: Combines rate limiting, NLPAgent parsing, and agent routing

### MCP Layer
- **IntentEngine**: Regex-based NLP parsing, location resolution, duration extraction, confidence scoring
- **IntentValidator**: Per-intent-type parameter requirement enforcement
- **Guardrails**: Text sanitisation, duration bounds, location ID format, sliding-window rate limiter
- **RAGModule**: Keyword-overlap retrieval from structured knowledge base

### Services
- **SlotService**: All reads/writes to `parking_data.json`; thread-safe writes via Lock
- **BookingService**: Creates/releases bookings; schedules `threading.Timer` for auto-expiry

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `create_app()` factory | Enables test isolation (inject temp data file) |
| Agent → Service separation | Services are pure data logic; agents add MCP + validation |
| In-memory bookings | Simplicity; slot occupancy is still persisted |
| Trace IDs on every request | Full request-scoped log correlation across all layers |
| Simulated RAG (keyword) | No ML dependencies required; upgradeable to vector search |
| Sliding-window rate limiter | Fair rate limiting without Redis dependency |
