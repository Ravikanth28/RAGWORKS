# MCP Design Document

## What is MCP?

**Model Context Protocol (MCP)** is an intent-based middleware pattern that:

1. Normalises *all* user actions — whether from typed API parameters or natural language — into a single, validated **intent object**.
2. Ensures every action is **validated** before any data mutation occurs.
3. Makes the system's decision-making **auditable** (every response includes the `mcp_intent` that was executed).

## Intent Object Schema

```json
{
  "intent":     "BOOK_SLOT",
  "params": {
    "location": "anna-nagar",
    "duration": 2,
    "slot_id":  null
  },
  "confidence": 1.0,
  "raw_input":  "Book parking near anna for 2 hours",
  "rag_context": [ { "id": "pricing-standard", ... } ],
  "rag_context_text": "[PRICING] Rate is ₹20 per hour.",
  "validation_ok":  true,
  "validation_msg": "Valid"
}
```

## Two Paths to an Intent

### Path A — Structured API

```python
# app.py inside api_book_slot()
engine = IntentEngine(trace_id)
intent = engine.create_structured_intent(
    INTENT_BOOK_SLOT, location=location_id, duration=duration
)
# confidence is always 1.0 for structured intents
```

Structured intents skip NLP parsing and RAG enrichment entirely.
They are validated by `IntentValidator` and then passed directly to BookingAgent.

### Path B — Natural Language

```python
# NLPAgent.process()
parsed = IntentEngine(trace_id).parse(text)
# → regex-based intent detection, location resolution, duration extraction
parsed = RAGModule.enrich_intent(parsed, text)
# → attach top-3 knowledge entries from parking_knowledge.json
ok, msg = IntentValidator(trace_id).validate(parsed)
```

NLP intents carry a `confidence` score (0.0–1.0).
Intents with `confidence < 0.4` are **never executed**.

## Confidence Scoring Formula

```
score = 0.0
if intent != UNKNOWN:  score += 0.4
if location resolved:  score += 0.3
if duration extracted: score += 0.3
```

| Input | Intent | Location | Duration | Score |
|---|---|---|---|---|
| "Book parking near mall for 2 hours" | BOOK_SLOT ✓ | mall-parking ✓ | 2 ✓ | 1.0 |
| "Show slots at Anna Nagar" | VIEW_SLOTS ✓ | anna-nagar ✓ | — | 0.7 |
| "Book parking somewhere" | BOOK_SLOT ✓ | — | — | 0.4 |
| "Hello there" | UNKNOWN | — | — | 0.0 |

## Validation Rules

### VIEW_SLOTS
- `location` — required

### BOOK_SLOT
- `location` — required
- `duration` — required, integer, 1–24

### RELEASE_SLOT
- `slot_id` OR `booking_id` — at least one required

## Location Alias System

The IntentEngine resolves informal location names to canonical IDs:

| User Input | Resolved To |
|---|---|
| "anna", "anna nagar", "annanagar" | `anna-nagar` |
| "t nagar", "tnagar", "t.nagar", "thyagaraya nagar" | `t-nagar` |
| "velachery" | `velachery` |
| "mall", "mall parking", "express avenue", "express" | `mall-parking` |

Matching is done longest-alias-first to prevent shorter aliases
(e.g. "anna") from shadowing longer ones (e.g. "anna nagar").

## RAG Integration in MCP

After `IntentEngine.parse()` runs, `RAGModule.enrich_intent()` is called.
It adds two keys to the intent dict:

- `rag_context` — list of raw knowledge entry dicts (for programmatic use)
- `rag_context_text` — formatted string (for display in the UI response)

The RAG context does **not** change the intent or its parameters.
It is informational — grounding the response in factual knowledge.

## Auditability

Every API response that involves an MCP action includes `mcp_intent` in the response body:

```json
{
  "message": "Slot AN-001 booked successfully!",
  "booking": { ... },
  "mcp_intent": {
    "intent": "BOOK_SLOT",
    "params": { "location": "anna-nagar", "duration": 2 },
    "confidence": 1.0
  },
  "trace_id": "A3F9BC12"
}
```

This allows:
- Frontend to display what action was taken
- Logs to correlate the intent with the trace ID
- Tests to assert on the exact MCP intent that was produced
