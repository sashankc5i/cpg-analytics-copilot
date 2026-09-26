# API Documentation

## 1. Overview

The Nexa Consumer Products Analytics Copilot exposes a REST API through
FastAPI.

The API is responsible for:

-   health and readiness checks
-   conversational analytics
-   conversation lifecycle management
-   streaming investigation workflows
-   streaming challenge/review workflows

The backend is the authoritative orchestration layer. The frontend
communicates with it through HTTP/JSON and NDJSON streaming.

------------------------------------------------------------------------

## 2. Base URL

For local development:

``` text
http://localhost:8000
```

All application endpoints are relative to this base URL.

Example:

``` text
POST http://localhost:8000/api/chat
```

------------------------------------------------------------------------

## 3. Request Identification

The backend middleware generates a request ID for incoming requests.

Streaming responses expose the request ID through:

``` text
X-Request-ID
```

This provides a correlation point between frontend activity and backend
logs.

------------------------------------------------------------------------

# 4. Health and Readiness

## 4.1 GET `/health`

Basic service health check.

### Response

``` json
{
  "status": "healthy",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

Use this endpoint to determine whether the HTTP service is responding.

------------------------------------------------------------------------

## 4.2 GET `/readiness`

Checks whether the application is ready to serve requests.

The readiness check verifies that the Groq API key is configured.

### Ready response

``` json
{
  "status": "ready",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

### Not-ready response

HTTP `503 Service Unavailable`

``` json
{
  "detail": {
    "status": "not_ready",
    "reason": "Groq API key is not configured."
  }
}
```

### Why both endpoints exist

`/health` answers:

> Is the service running?

`/readiness` answers:

> Is the service configured sufficiently to process requests?

This distinction is useful when the application is eventually deployed
behind a container platform or load balancer.

------------------------------------------------------------------------

# 5. Shared Chat Request Model

The Copilot, Investigation, and Challenge streaming endpoints use the
same request shape.

``` json
{
  "message": "Why did revenue change in August?",
  "conversation_id": "conversation-123"
}
```

## Fields

  ---------------------------------------------------------------------------------
  Field               Type                   Required Constraints   Description
  ------------------- ------------- ----------------- ------------- ---------------
  `message`           string                      Yes 1--4000       User question
                                                      characters    or
                                                                    investigation
                                                                    request

  `conversation_id`   string                      Yes 1--100        Shared
                                                      characters    conversation
                                                                    identity
  ---------------------------------------------------------------------------------

The backend model also defines `"default"` as the default value for
`conversation_id` when the request model is used without an explicit
value.

The frontend always supplies an explicit conversation ID.

------------------------------------------------------------------------

# 6. Conversational Analytics

## 6.1 POST `/api/chat`

Runs the standard Copilot workflow.

### Request

``` json
{
  "message": "Show me the top 10 products by revenue.",
  "conversation_id": "conversation-123"
}
```

### Processing flow

``` text
HTTP Request
    ↓
Conversation History
    ↓
Analytics Agent
    ↓
Groq
    ↓
Approved Analytics Tools
    ↓
Repositories
    ↓
SQLite
    ↓
Deterministic Results
    ↓
Groq Synthesis
    ↓
Visualization Builder
    ↓
HTTP Response
```

The agent receives the existing conversation history for the supplied
conversation ID.

The user and assistant messages are then stored in the conversation
manager.

### Response

``` json
{
  "answer": "The top products by revenue are ...",
  "tools_used": [
    "get_top_products"
  ],
  "tool_results": [
    {
      "tool": "get_top_products",
      "result": {}
    }
  ],
  "visualization": {
    "type": "bar",
    "title": "Top Products by Revenue",
    "x": [],
    "y": []
  },
  "conversation_id": "conversation-123"
}
```

`tool_results.result` contains the structured result returned by the
analytics tool. Its exact shape depends on the tool that was executed.

### Response fields

  -----------------------------------------------------------------------
  Field                   Type                    Description
  ----------------------- ----------------------- -----------------------
  `answer`                string                  Natural-language
                                                  analytical response

  `tools_used`            string\[\]              Approved tools executed
                                                  during the request

  `tool_results`          object\[\]              Structured outputs
                                                  returned by those tools

  `visualization`         object/null             Visualization-ready
                                                  data when a chart can
                                                  be generated

  `conversation_id`       string                  Conversation used for
                                                  the request
  -----------------------------------------------------------------------

### Visualization structure

When a chart is available:

``` json
{
  "type": "line",
  "title": "Monthly Revenue Trend",
  "x": ["2026-01", "2026-02"],
  "y": [34054689.3, 30545433.8]
}
```

Supported chart types currently include:

-   `line`
-   `bar`

The visualization is derived from deterministic tool results rather than
generated directly by the LLM.

### Error handling

Validation errors are returned as HTTP `400`.

Runtime and unexpected application errors are returned as HTTP `500`.

------------------------------------------------------------------------

# 7. Conversation Management

Conversation state is managed by the in-memory `ConversationManager`.

A conversation contains:

``` json
{
  "conversation_id": "conversation-123",
  "title": "Revenue Analysis",
  "created_at": "2026-09-26T10:00:00+00:00",
  "updated_at": "2026-09-26T10:05:00+00:00",
  "archived": false,
  "history": [
    {
      "role": "user",
      "content": "Show me regional revenue."
    },
    {
      "role": "assistant",
      "content": "..."
    }
  ]
}
```

## 7.1 POST `/api/conversations`

Creates a conversation.

### Request

``` json
{
  "title": "Revenue Analysis"
}
```

A client may also supply its own conversation ID:

``` json
{
  "conversation_id": "conversation-123",
  "title": "Revenue Analysis"
}
```

### Constraints

  Field               Type       Required Constraint
  ------------------- -------- ---------- -------------------
  `conversation_id`   string           No 1--100 characters
  `title`             string           No 1--200 characters

If `conversation_id` is omitted, the backend generates a UUID.

If `title` is omitted, it defaults to:

``` text
New Chat
```

### Response

HTTP `200`

``` json
{
  "conversation_id": "conversation-123",
  "title": "Revenue Analysis",
  "created_at": "2026-09-26T10:00:00+00:00",
  "updated_at": "2026-09-26T10:00:00+00:00",
  "archived": false,
  "history": []
}
```

------------------------------------------------------------------------

## 7.2 GET `/api/conversations`

Lists active conversations.

Archived conversations are excluded by default.

### Request

``` text
GET /api/conversations
```

### Include archived conversations

``` text
GET /api/conversations?include_archived=true
```

### Response

The endpoint returns a JSON array rather than a wrapper object.

``` json
[
  {
    "conversation_id": "conversation-123",
    "title": "Revenue Analysis",
    "created_at": "2026-09-26T10:00:00+00:00",
    "updated_at": "2026-09-26T10:05:00+00:00",
    "archived": false
  }
]
```

The list is sorted by `updated_at` in descending order.

------------------------------------------------------------------------

## 7.3 GET `/api/conversations/{conversation_id}`

Returns the complete conversation including message history.

### Example

``` text
GET /api/conversations/conversation-123
```

### Response

``` json
{
  "conversation_id": "conversation-123",
  "title": "Revenue Analysis",
  "created_at": "2026-09-26T10:00:00+00:00",
  "updated_at": "2026-09-26T10:05:00+00:00",
  "archived": false,
  "history": [
    {
      "role": "user",
      "content": "Why did revenue change?"
    },
    {
      "role": "assistant",
      "content": "Revenue changed because ..."
    }
  ]
}
```

------------------------------------------------------------------------

## 7.4 Rename Conversation

The frontend supports renaming a conversation through the conversation
lifecycle API.

Request body:

``` json
{
  "title": "August Revenue Investigation"
}
```

The title is trimmed and must not be empty.

Maximum title length:

``` text
200 characters
```

The conversation's `updated_at` value is refreshed when the title
changes.

------------------------------------------------------------------------

## 7.5 POST `/api/conversations/{conversation_id}/archive`

Archives a conversation.

### Example

``` text
POST /api/conversations/conversation-123/archive
```

The conversation remains stored but is excluded from the default
conversation list.

### Response

The conversation object is returned with:

``` json
{
  "archived": true
}
```

------------------------------------------------------------------------

## 7.6 POST `/api/conversations/{conversation_id}/unarchive`

Restores an archived conversation.

### Example

``` text
POST /api/conversations/conversation-123/unarchive
```

The conversation becomes visible again in the default conversation list.

------------------------------------------------------------------------

## 7.7 DELETE `/api/conversations/{conversation_id}`

Deletes the conversation from the `ConversationManager`.

### Example

``` text
DELETE /api/conversations/conversation-123
```

The operation is explicit and irreversible within the current in-memory
session.

------------------------------------------------------------------------

# 8. Investigation Mode

## 8.1 POST `/api/investigate/stream`

Runs Investigation Mode and streams the investigation lifecycle to the
client.

Unlike the standard Copilot endpoint, Investigation Mode is designed for
multi-dimensional analytical questions.

### Request

``` json
{
  "message": "Investigate why revenue declined and identify the most plausible drivers.",
  "conversation_id": "conversation-123"
}
```

### Investigation flow

``` text
User Question
      ↓
Investigation Planner
      ↓
Investigation Areas
      ↓
Hypothesis Generation
      ↓
Deterministic Evidence Collection
      ↓
Evidence Synthesis
      ↓
Streamed Answer
```

The investigation can inspect areas such as:

-   revenue trend
-   regional performance
-   product performance
-   category performance
-   customer segments
-   promotion impact
-   inventory stockouts

The planner selects the relevant investigation areas.

The evidence collector then executes the corresponding approved
analytics tools.

### Response type

The endpoint returns:

``` text
application/x-ndjson
```

Each line is an independent JSON event.

------------------------------------------------------------------------

## 8.2 Investigation Stream Events

### `investigation_started`

Signals that investigation processing has started.

``` json
{
  "type": "investigation_started"
}
```

### `plan`

Contains the selected investigation areas.

``` json
{
  "type": "plan",
  "data": [
    "revenue_trend",
    "regional_performance",
    "product_performance"
  ]
}
```

### `hypotheses`

Contains the generated hypotheses.

``` json
{
  "type": "hypotheses",
  "data": []
}
```

The exact hypothesis objects are generated by the investigation
planner/hypothesis stage.

### `answer_start`

Signals that final synthesis is beginning.

``` json
{
  "type": "answer_start"
}
```

### `token`

Contains a streamed piece of the final answer.

``` json
{
  "type": "token",
  "data": "Revenue "
}
```

Clients should append `data` values in order.

### `answer_end`

Signals completion of the streamed answer.

``` json
{
  "type": "answer_end"
}
```

### `error`

Signals an error during streaming.

``` json
{
  "type": "error",
  "data": "Error description"
}
```

------------------------------------------------------------------------

# 9. Challenge My Conclusion

## 9.1 POST `/api/investigate/challenge/stream`

Challenges the latest completed investigation associated with the
supplied conversation ID.

### Request

``` json
{
  "message": "Challenge my conclusion.",
  "conversation_id": "conversation-123"
}
```

The backend retrieves the completed investigation from investigation
memory.

The frontend does not send the original conclusion as part of the
request.

### Challenge flow

``` text
Completed Investigation
        ↓
Original Conclusion
        +
Existing Evidence
        ↓
Direct Challenge Reviewer
        ↓
One bounded Groq synthesis call
        ↓
Streamed Review
```

The challenge reviewer examines:

-   supporting evidence
-   contradicting or limiting evidence
-   missing evidence
-   alternative explanations
-   bottom-line assessment

The implementation intentionally reuses the completed investigation
evidence instead of launching another broad evidence-collection
workflow.

------------------------------------------------------------------------

## 9.2 Challenge Stream Events

### `challenge_started`

``` json
{
  "type": "challenge_started"
}
```

### `claims`

The current compatibility event for extracted claims.

The current challenge implementation no longer performs a separate
claim-extraction stage; the event remains part of the API stream for
frontend compatibility.

``` json
{
  "type": "claims",
  "data": []
}
```

### `challenge_plan`

Contains the challenge review plan.

``` json
{
  "type": "challenge_plan",
  "data": []
}
```

### `challenge_evidence`

Contains the evidence snapshot used by the reviewer.

``` json
{
  "type": "challenge_evidence",
  "data": {}
}
```

### `answer_start`

``` json
{
  "type": "answer_start"
}
```

### `token`

``` json
{
  "type": "token",
  "data": "The conclusion is "
}
```

### `answer_end`

``` json
{
  "type": "answer_end"
}
```

### `error`

``` json
{
  "type": "error",
  "data": "Error description"
}
```

------------------------------------------------------------------------

# 10. Shared Conversation Identity

The same `conversation_id` is used across the three user-facing
analytical modes:

``` text
Copilot
   │
   ├── conversation_id
   │
   ▼
Investigation
   │
   ├── conversation_id
   │
   ▼
Challenge
```

This allows the frontend to treat Copilot, Investigation, and Challenge
as different modes operating on the same analytical conversation.

The investigation subsystem also maintains analytical context associated
with the same ID, including:

-   latest investigation plan
-   latest evidence
-   latest synthesized answer
-   investigation history

------------------------------------------------------------------------

# 11. Error Model

The API uses normal HTTP errors for request-level failures and NDJSON
error events for failures occurring during streaming.

## Standard API errors

Common statuses include:

  Status   Meaning
  -------- -----------------------------------------
  `400`    Request or application validation error
  `500`    Unexpected server/runtime error
  `503`    Service is not ready

For example:

``` json
{
  "detail": "An unexpected error occurred."
}
```

The exact error detail depends on the endpoint and failure stage.

------------------------------------------------------------------------

# 12. Frontend Integration

The frontend API layer is implemented in:

``` text
frontend/src/services/api.ts
```

The shared TypeScript contracts are defined in:

``` text
frontend/src/types/chat.ts
```

The frontend uses normal JSON requests for:

``` text
/api/chat
/api/conversations
```

and NDJSON streaming for:

``` text
/api/investigate/stream
/api/investigate/challenge/stream
```

The streaming client processes events incrementally rather than waiting
for the entire response.

------------------------------------------------------------------------

# 13. API Design Principles

The API intentionally keeps responsibilities separated.

``` text
Frontend
   ↓
REST / Streaming API
   ↓
Agent / Investigation Orchestration
   ↓
Analytics Tools
   ↓
Repositories
   ↓
SQLite
```

Important boundaries:

1.  The frontend never accesses SQLite directly.
2.  The LLM never receives direct database access.
3.  Tool execution is controlled by the backend.
4.  Analytics calculations are performed deterministically.
5.  Conversation identity is explicitly carried through API requests.
6.  Investigation and Challenge use streaming so the UI can expose
    workflow progress.
7.  Visualization data is derived from analytical tool results.

------------------------------------------------------------------------

# 14. Current API Limitations

The current API is intentionally a training/development implementation.

### In-memory conversation storage

Conversation state is held in memory.

A backend restart clears:

-   conversation history
-   conversation metadata
-   investigation session memory

Persistent conversation storage is not implemented yet.

### Challenge history persistence

The current Challenge streaming path produces the challenge response but
does not persist that streamed challenge answer into the
`ConversationManager` history.

This is a known implementation limitation.

### Authentication

The current API does not implement enterprise authentication or
authorization.

### Multi-user isolation

Conversation IDs provide application-level conversation identity, but
there is no authenticated user boundary yet.

### Deployment

The documented API assumes local FastAPI execution. Production ingress,
TLS, authentication, rate limiting, and deployment-specific networking
are outside the current implementation.

------------------------------------------------------------------------

# 15. Example End-to-End Workflow

A typical user session looks like this:

## Step 1 --- Create conversation

``` http
POST /api/conversations
```

``` json
{
  "title": "Revenue Investigation"
}
```

------------------------------------------------------------------------

## Step 2 --- Ask a standard analytical question

``` http
POST /api/chat
```

``` json
{
  "message": "Show me monthly revenue for 2026.",
  "conversation_id": "conversation-123"
}
```

------------------------------------------------------------------------

## Step 3 --- Run a deeper investigation

``` http
POST /api/investigate/stream
```

``` json
{
  "message": "Investigate the main drivers of the revenue movement.",
  "conversation_id": "conversation-123"
}
```

The client consumes the NDJSON events and renders the investigation
progress and final answer.

------------------------------------------------------------------------

## Step 4 --- Challenge the conclusion

``` http
POST /api/investigate/challenge/stream
```

``` json
{
  "message": "Challenge my conclusion.",
  "conversation_id": "conversation-123"
}
```

The backend retrieves the latest completed investigation for that same
conversation and performs the bounded challenge review.

------------------------------------------------------------------------

## Step 5 --- Reload the conversation

``` http
GET /api/conversations/conversation-123
```

The frontend receives the stored conversation history.

------------------------------------------------------------------------

# 16. API Mental Model

The API is not simply:

> frontend → LLM → answer

It is:

``` text
                    ┌─────────────────────┐
                    │      React UI       │
                    └──────────┬──────────┘
                               │
                     REST / NDJSON
                               │
                    ┌──────────▼──────────┐
                    │     FastAPI API     │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
          Copilot        Investigation       Challenge
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Agent / Orchestration│
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Approved Analytics  │
                    │       Tools         │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Repositories      │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │      SQLite         │
                    └─────────────────────┘
```

The important FDE principle is that the API is the controlled boundary
between the user interface, AI orchestration, deterministic analytics,
and data layer.

------------------------------------------------------------------------

# 17. API Reference Summary

  ----------------------------------------------------------------------------------------------------------
  Method            Endpoint                                           Purpose             Response
  ----------------- -------------------------------------------------- ------------------- -----------------
  `GET`             `/health`                                          Basic service       JSON
                                                                       health              

  `GET`             `/readiness`                                       Dependency/config   JSON
                                                                       readiness           

  `POST`            `/api/chat`                                        Standard analytical JSON
                                                                       Copilot             

  `POST`            `/api/conversations`                               Create conversation JSON

  `GET`             `/api/conversations`                               List conversations  JSON array

  `GET`             `/api/conversations/{conversation_id}`             Retrieve            JSON
                                                                       conversation        

  `POST`            `/api/conversations/{conversation_id}/archive`     Archive             JSON
                                                                       conversation        

  `POST`            `/api/conversations/{conversation_id}/unarchive`   Restore             JSON
                                                                       conversation        

  `DELETE`          `/api/conversations/{conversation_id}`             Delete conversation JSON/status

  `POST`            `/api/investigate/stream`                          Run investigation   NDJSON

  `POST`            `/api/investigate/challenge/stream`                Challenge latest    NDJSON
                                                                       conclusion          
  ----------------------------------------------------------------------------------------------------------

The conversation rename operation is exposed through the conversation
lifecycle API used by the frontend; its exact HTTP route should be kept
aligned with the implementation in `main.py` and
`frontend/src/services/api.ts`.
