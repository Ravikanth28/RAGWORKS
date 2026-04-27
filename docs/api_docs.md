# API Documentation

Base URL: `http://localhost:5000`

All requests and responses use `application/json`.  
All responses include a `trace_id` field for log correlation (NLP and write endpoints).

---

## Endpoints Summary

| Method | Path | Description |
|---|---|---|
| GET | `/api/locations` | List all locations with availability |
| GET | `/api/slots` | Get slot detail for one location |
| POST | `/api/book` | Book a parking slot |
| POST | `/api/release` | Release an active booking |
| GET | `/api/bookings` | List all active bookings |
| GET | `/api/booking/<id>` | Get a single booking by ID |
| POST | `/api/nlp` | Natural-language parking assistant |

---

## GET `/api/locations`

Returns all parking locations with real-time available-slot counts.

**Response `200 OK`**

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
    },
    {
      "id": "t-nagar",
      "name": "T Nagar",
      "address": "Usman Road, T Nagar, Chennai - 600017",
      "totalSlots": 6,
      "availableSlots": 5,
      "ratePerHour": 20
    }
  ]
}
```

---

## GET `/api/slots?location=<location_id>`

Returns detailed slot status for a single location.

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `location` | string | Yes | Canonical location ID (e.g. `anna-nagar`) |

**Response `200 OK`**

```json
{
  "location": "Anna Nagar",
  "location_id": "anna-nagar",
  "address": "2nd Avenue, Anna Nagar, Chennai - 600040",
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

**Error Responses**

| Status | Condition |
|---|---|
| `400` | `location` query parameter missing |
| `404` | Location ID not found |

---

## POST `/api/book`

Books a parking slot.

**Request Body**

```json
{
  "location": "anna-nagar",
  "duration": 2,
  "slot_id": "AN-003"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `location` | string | Yes | Canonical location ID |
| `duration` | integer | Yes | Hours to book (1–24) |
| `slot_id` | string | No | Specific slot to book; if omitted, first free slot is used |

**Response `201 Created`**

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
    "booked_at": "2026-04-27T10:00:00.000000",
    "expires_at": "2026-04-27T12:00:00.000000",
    "status": "active"
  },
  "mcp_intent": {
    "intent": "BOOK_SLOT",
    "params": { "location": "anna-nagar", "duration": 2 },
    "confidence": 1.0
  },
  "trace_id": "A3F9BC12"
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | `location` or `duration` missing or invalid |
| `409` | Requested slot is already occupied, or no free slots remain |
| `429` | Rate limit exceeded (30 req / 60 s) |

---

## POST `/api/release`

Releases an active booking. Accepts either `booking_id` or `slot_id`.

**Request Body**

```json
{ "booking_id": "A1B2C3D4" }
```
or
```json
{ "slot_id": "AN-003" }
```

**Response `200 OK`**

```json
{
  "message": "Slot AN-003 released successfully!",
  "booking_id": "A1B2C3D4",
  "mcp_intent": {
    "intent": "RELEASE_SLOT",
    "params": { "booking_id": "A1B2C3D4", "slot_id": "AN-003" },
    "confidence": 1.0
  },
  "trace_id": "B5C6D7E8"
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | Neither `booking_id` nor `slot_id` provided |
| `404` | Booking not found or already released |

---

## GET `/api/bookings`

Returns all currently active bookings.

**Response `200 OK`**

```json
{
  "bookings": [
    {
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
    }
  ]
}
```

---

## GET `/api/booking/<booking_id>`

Returns a single booking record by ID.

**Response `200 OK`**

```json
{ "booking": { "booking_id": "A1B2C3D4", ... } }
```

**Error `404`** — booking ID not found

---

## POST `/api/nlp`

Natural-language interface. Runs through the full MCP + RAG + agent pipeline.

**Request Body**

```json
{ "text": "Book parking near mall for 2 hours" }
```

**Response `200 OK` — BOOK_SLOT intent**

```json
{
  "parsed": {
    "intent": "BOOK_SLOT",
    "params": {
      "location": "mall-parking",
      "duration": 2,
      "slot_id": null
    },
    "confidence": 1.0,
    "raw_input": "Book parking near mall for 2 hours",
    "rag_context": [
      {
        "id": "pricing-standard",
        "category": "pricing",
        "keywords": ["price", "cost", "rate"],
        "content": "Standard parking rate is ₹20 per hour..."
      }
    ],
    "rag_context_text": "[PRICING] Standard parking rate is ₹20 per hour...",
    "validation_ok": true,
    "validation_msg": "Valid"
  },
  "action": "book",
  "prefill": { "location": "mall-parking", "duration": 2 },
  "message": "Ready to book at Mall Parking for 2 hour(s). Cost: ₹40. Confirm to proceed.",
  "context": "[PRICING] Standard parking rate is ₹20 per hour...",
  "trace_id": "C6D7E8F9"
}
```

**Response `200 OK` — VIEW_SLOTS intent**

```json
{
  "parsed": { "intent": "VIEW_SLOTS", "confidence": 0.7, ... },
  "result": {
    "location": "Anna Nagar",
    "available": 7,
    "total": 8
  },
  "message": "Anna Nagar has 7/8 slots available.",
  "trace_id": "D7E8F9A0"
}
```

**Response `200 OK` — low confidence**

```json
{
  "parsed": { "intent": "UNKNOWN", "confidence": 0.0, ... },
  "message": "I couldn't understand that. Try: 'Book parking at Mall for 2 hours'",
  "trace_id": "E8F9A0B1"
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | `text` field missing or empty |
| `429` | Rate limit exceeded |

---

## Data Models

### Location (from `/api/locations`)

| Field | Type | Description |
|---|---|---|
| `id` | string | Canonical ID (`anna-nagar`, `t-nagar`, etc.) |
| `name` | string | Display name |
| `address` | string | Full street address |
| `totalSlots` | int | Total slot count |
| `availableSlots` | int | Real-time free slot count |
| `ratePerHour` | int | Rate in INR |

### Slot (from `/api/slots`)

| Field | Type | Description |
|---|---|---|
| `id` | string | Slot ID (e.g. `AN-001`) |
| `status` | string | `"free"` or `"occupied"` |
| `booking_id` | string | Present only when `status == "occupied"` |

### Booking

| Field | Type | Description |
|---|---|---|
| `booking_id` | string | 8-char uppercase ID (e.g. `A1B2C3D4`) |
| `location_id` | string | Canonical location ID |
| `location_name` | string | Location display name |
| `slot_id` | string | Booked slot ID |
| `duration` | int | Hours booked (1–24) |
| `cost` | int | Total cost = `duration × ratePerHour` |
| `currency` | string | Always `"₹"` |
| `booked_at` | ISO 8601 | Booking creation timestamp |
| `expires_at` | ISO 8601 | Booking expiry timestamp |
| `status` | string | `"active"` or `"released"` |
| `released_at` | ISO 8601 | Present only when released |
| `auto_released` | bool | `true` if released by auto-expiry timer |
