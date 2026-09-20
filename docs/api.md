# API Documentation

## 1. Overview

The CPG Analytics Copilot exposes a REST API through a **FastAPI** backend.

The API provides the interface between the React frontend and the backend analytics agent.

The core request flow is:

```text
React Frontend
      │
      │ HTTP / JSON
      ▼
FastAPI REST API
      │
      ▼
Conversation Manager
      │
      ▼
Analytics Agent
      │
      ▼
Analytics Tools
      │
      ▼
SQLite
```

The API is intentionally responsible for:

* request validation
* conversation management
* agent invocation
* visualization generation
* structured response construction
* error handling
* request tracing
* health checks

The API does **not** directly perform business analytics.

---

# 2. Base URL

During local development, the backend runs on:

```text
http://127.0.0.1:8000
```

The API endpoints are therefore accessed through:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/readiness
http://127.0.0.1:8000/api/chat
```

The frontend communicates with the backend using the `/api/chat` endpoint.

---

# 3. API Endpoints

The current API exposes three primary endpoints.

| Endpoint     | Method | Purpose                    |
| ------------ | ------ | -------------------------- |
| `/health`    | GET    | Basic service health       |
| `/readiness` | GET    | Service readiness          |
| `/api/chat`  | POST   | Submit analytics questions |

---

# 4. Health Endpoint

## Endpoint

```http
GET /health
```

## Purpose

The health endpoint provides a lightweight indication that the FastAPI application is running.

It is intended for basic service health checks.

## Example

```bash
curl http://127.0.0.1:8000/health
```

## Response

Example:

```json
{
  "status": "healthy",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

## Response Fields

| Field     | Description                      |
| --------- | -------------------------------- |
| `status`  | Current application health state |
| `service` | Application name                 |
| `version` | Application version              |

---

# 5. Readiness Endpoint

## Endpoint

```http
GET /readiness
```

## Purpose

The readiness endpoint determines whether the application is ready to process requests.

Unlike `/health`, readiness checks the availability of required configuration.

The current implementation verifies that the Groq API key is configured.

## Example

```bash
curl http://127.0.0.1:8000/readiness
```

## Successful Response

```json
{
  "status": "ready",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

## Failure Response

If the required configuration is unavailable:

```http
503 Service Unavailable
```

Example:

```json
{
  "detail": {
    "status": "not_ready",
    "reason": "Groq API key is not configured."
  }
}
```

---

# 6. Health vs Readiness

The distinction is intentional.

```text
/health
   │
   └── Is the application running?

/readiness
   │
   └── Can the application process requests?
```

This distinction becomes important when the application is deployed to an orchestration platform.

For example:

```text
Container starts
      │
      ▼
/health
      │
      ├── Healthy
      │
      ▼
/readiness
      │
      ├── Ready
      │
      ▼
Receive traffic
```

In a production Azure environment, these endpoints could be connected to platform health probes.

---

# 7. Chat Endpoint

## Endpoint

```http
POST /api/chat
```

This is the primary application endpoint.

It receives a natural-language business question and returns:

* the generated answer
* tools used
* deterministic tool results
* visualization configuration
* conversation ID

---

# 8. Chat Request

The request body follows the `ChatRequest` model.

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"
```

## Request Schema

```json
{
  "message": "What is our total revenue?",
  "conversation_id": "default"
}
```

---

# 9. Request Fields

| Field             | Type   | Required | Constraints       |
| ----------------- | ------ | -------: | ----------------- |
| `message`         | string |      Yes | 1–4000 characters |
| `conversation_id` | string |       No | 1–100 characters  |

The `conversation_id` defaults to:

```text
default
```

when it is not explicitly provided.

---

# 10. Input Validation

FastAPI/Pydantic validates incoming requests before they reach the analytics agent.

For example:

```text
message = ""
```

is rejected because the minimum length is one character.

Similarly, an excessively long message is rejected.

The API limits messages to:

```text
4000 characters
```

This provides a basic protection boundary around the agent.

---

# 11. Example Chat Request

Using `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What is our total revenue?\",\"conversation_id\":\"demo-session\"}"
```

---

# 12. Chat Response

The endpoint returns a structured `ChatResponse`.

The response model is:

```python
class ChatResponse(BaseModel):
    answer: str
    tools_used: list[ToolResult]
    tool_results: list[ToolResult]
    visualization: Visualization | None
    conversation_id: str
```

Conceptually:

```text
ChatResponse
│
├── answer
├── tools_used
├── tool_results
├── visualization
└── conversation_id
```

---

# 13. Example Response

A simplified response looks like:

```json
{
  "answer": "Total revenue is ₹X across Y transactions.",
  "tools_used": [
    "get_overall_sales"
  ],
  "tool_results": [
    {
      "tool": "get_overall_sales",
      "result": {
        "transactions": 250000,
        "units_sold": 500000,
        "revenue": 12345678.90,
        "average_transaction_value": 49.38
      }
    }
  ],
  "visualization": null,
  "conversation_id": "demo-session"
}
```

The actual numerical values are generated from the SQLite database.

---

# 14. Answer Field

The `answer` field contains the natural-language response generated by the analytics agent.

Example:

```json
{
  "answer": "The South region currently generates the highest revenue."
}
```

The answer is produced by the LLM after it has received deterministic analytics results.

The LLM should not independently invent business metrics.

---

# 15. Tools Used

The `tools_used` field records the analytics tools invoked during the request.

Example:

```json
{
  "tools_used": [
    "get_monthly_sales_trend",
    "get_sales_by_region",
    "get_top_products"
  ]
}
```

This is particularly useful for diagnostic questions.

For example:

```text
Why is revenue changing?
```

may trigger multiple analytical tools.

The frontend can use this information for transparency, debugging, and future observability.

---

# 16. Tool Results

The `tool_results` field contains the deterministic outputs returned by the analytics layer.

Example:

```json
{
  "tool_results": [
    {
      "tool": "get_sales_by_region",
      "result": [
        {
          "region": "South",
          "transactions": 50000,
          "units_sold": 100000,
          "revenue": 5000000
        }
      ]
    }
  ]
}
```

This creates a clear separation between:

```text
LLM interpretation
        vs.
Deterministic business data
```

---

# 17. Visualization

The API can return a visualization configuration.

Example:

```json
{
  "visualization": {
    "type": "bar",
    "title": "Revenue by Region",
    "x": [
      "South",
      "West",
      "North",
      "East"
    ],
    "y": [
      5000000,
      4200000,
      3500000,
      2800000
    ]
  }
}
```

The backend does not render the chart.

Instead, it provides the data and chart configuration to the React frontend.

---

# 18. Visualization Architecture

The visualization flow is:

```text
Analytics Tool
      │
      ▼
Tool Result
      │
      ▼
build_visualization()
      │
      ▼
Visualization JSON
      │
      ▼
FastAPI Response
      │
      ▼
React
      │
      ▼
Plotly
```

This keeps rendering concerns in the frontend.

---

# 19. Supported Visualization Types

The current visualization layer supports:

### Line charts

Used for:

```text
Monthly revenue
```

Example:

```json
{
  "type": "line",
  "title": "Monthly Revenue"
}
```

### Bar charts

Used for:

```text
Revenue by region
Top products
Revenue by category
```

Example:

```json
{
  "type": "bar",
  "title": "Revenue by Region"
}
```

---

# 20. Conversation IDs

The API uses `conversation_id` to maintain conversational context.

Example:

### First request

```json
{
  "message": "Which region performs best?",
  "conversation_id": "session-123"
}
```

### Follow-up

```json
{
  "message": "Why?",
  "conversation_id": "session-123"
}
```

The backend retrieves the history associated with:

```text
session-123
```

and passes that context to the analytics agent.

---

# 21. Conversation Lifecycle

The current implementation follows:

```text
Request
   │
   ▼
Get conversation history
   │
   ▼
Run agent
   │
   ▼
Generate answer
   │
   ▼
Store user message
   │
   ▼
Store assistant response
   │
   ▼
Return response
```

This allows subsequent questions to reference earlier discussion.

---

# 22. Conversation Isolation

Different conversation IDs maintain separate histories.

Example:

```text
session-A
   ├── Question 1
   ├── Answer 1
   ├── Question 2
   └── Answer 2

session-B
   ├── Question 1
   └── Answer 1
```

The conversation manager therefore prevents unrelated sessions from sharing conversational context.

---

# 23. Current Session Storage

The current implementation uses an in-memory `ConversationManager`.

Conceptually:

```python
class ConversationManager:
    def __init__(self):
        self.sessions = defaultdict(list)
```

This is appropriate for the training project and local development.

However, it has an important production limitation.

If the backend process restarts:

```text
Process restart
      ↓
Memory cleared
      ↓
Conversation history lost
```

---

# 24. Production Conversation Storage

A production deployment could move conversation state into a persistent store.

Possible architecture:

```text
React
  ↓
FastAPI
  ↓
Conversation Service
  ↓
Azure SQL / Redis / other approved store
```

The exact implementation would depend on:

* conversation volume
* retention requirements
* latency requirements
* security requirements
* multi-instance deployment
* compliance requirements

---

# 25. Request IDs

Each incoming request receives a unique request ID.

The middleware generates:

```text
UUID
```

and stores it in:

```text
request.state.request_id
```

The response includes:

```http
X-Request-ID
```

This provides request-level traceability.

---

# 26. Request Logging

A typical request lifecycle produces logs similar to:

```text
request_started
      ↓
chat_request
      ↓
chat_completed
      ↓
request_completed
```

Example:

```text
2026-09-18 10:00:00 | INFO | request_started | request_id=abc...
2026-09-18 10:00:00 | INFO | chat_request | request_id=abc... | conversation_id=session-1
2026-09-18 10:00:03 | INFO | chat_completed | request_id=abc... | tools=['get_sales_by_region']
2026-09-18 10:00:03 | INFO | request_completed | request_id=abc... | status=200 | duration_ms=3021
```

This is useful when diagnosing production incidents.

---

# 27. Error Handling

The API categorizes backend failures into several classes.

## Validation Errors

Invalid request data is rejected by FastAPI/Pydantic.

Examples:

```text
Empty message
Message longer than 4000 characters
Invalid conversation ID
```

---

## Runtime Errors

Agent execution failures can return:

```http
500 Internal Server Error
```

The backend logs the error while returning a controlled API response.

---

## Unexpected Errors

Unexpected exceptions are caught and logged.

The API returns:

```json
{
  "detail": "An unexpected error occurred."
}
```

This prevents internal exception details from being unnecessarily exposed to the client.

---

# 28. HTTP Status Codes

The current API uses the following primary statuses:

| Status | Meaning                            |
| -----: | ---------------------------------- |
|  `200` | Successful request                 |
|  `422` | Request validation failure         |
|  `500` | Internal application/agent failure |
|  `503` | Service not ready                  |

---

# 29. CORS

The FastAPI application uses `CORSMiddleware`.

Configured origins are controlled through:

```text
CORS_ORIGINS
```

Example:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

This allows the Vite React development server to communicate with the backend.

The configuration is environment-driven rather than hard-coded into the application.

---

# 30. API Security Boundary

The API is an important security boundary.

The frontend should not have direct access to:

* Groq API credentials
* SQLite internals
* analytics implementation details
* database connection details
* internal tool execution logic

Instead:

```text
Browser
   │
   │ Public application API
   ▼
FastAPI
   │
   ├── Agent
   ├── Tools
   └── Database
```

Secrets remain on the backend.

---

# 31. LLM Boundary

The API also establishes a boundary between the LLM and the database.

The request does **not** follow:

```text
User
 ↓
LLM
 ↓
Generate arbitrary SQL
 ↓
Database
```

Instead:

```text
User
 ↓
FastAPI
 ↓
Analytics Agent
 ↓
Approved Tool
 ↓
Deterministic Query
 ↓
SQLite
```

This reduces the ability of the model to directly manipulate the database layer.

---

# 32. API and Analytics Separation

The API layer does not contain SQL queries.

For example:

```text
/api/chat
```

does not directly execute:

```sql
SELECT SUM(sales_amount)
FROM sales;
```

Instead, the API invokes:

```text
agent.run()
```

and the agent invokes:

```text
get_overall_sales()
```

The analytics function owns the SQL.

This separation improves maintainability.

---

# 33. API and Visualization Separation

The API also does not contain React rendering logic.

The backend returns:

```json
{
  "type": "bar",
  "title": "Revenue by Region",
  "x": ["South", "West"],
  "y": [5000000, 4200000]
}
```

The frontend decides how to render it.

This follows:

```text
Backend
   ↓
Data + visualization configuration

Frontend
   ↓
Visual rendering
```

---

# 34. Example End-to-End Request

Consider:

```text
"What are our top products?"
```

The request enters:

```http
POST /api/chat
```

with:

```json
{
  "message": "What are our top products?",
  "conversation_id": "demo"
}
```

The backend:

```text
1. Validates request
2. Creates request ID
3. Retrieves conversation history
4. Calls AnalyticsAgent
5. Groq selects get_top_products
6. Tool executes deterministic SQL
7. Result is returned to agent
8. Agent generates answer
9. Visualization builder creates chart configuration
10. Conversation history is updated
11. Structured response is returned
```

The frontend then renders:

```text
Natural-language answer
        +
Top product chart
```

---

# 35. Example Diagnostic Request

For:

```text
"Why is revenue changing?"
```

the API may trigger several tools:

```text
get_monthly_sales_trend
get_sales_by_region
get_top_products
get_sales_by_category
get_promotion_impact
get_stockout_rate
```

The response therefore provides both:

```text
Business explanation
```

and:

```text
Evidence used to construct the explanation
```

This is important for enterprise analytical workflows.

---

# 36. API Observability

The current API provides basic observability through:

* request IDs
* structured logging
* request duration
* HTTP status
* conversation ID
* tools used
* error logging

A production implementation could extend this with:

```text
Application Insights
       +
Distributed tracing
       +
LLM telemetry
       +
Tool latency
       +
Token usage
       +
Error rates
```

---

# 37. Production API Evolution

The current API is intentionally small.

A future enterprise API could introduce endpoints such as:

```text
GET    /api/conversations
GET    /api/conversations/{id}
DELETE /api/conversations/{id}

GET    /api/analytics/regions
GET    /api/analytics/products

GET    /api/metrics
GET    /api/evaluations
```

However, these should only be introduced when there is a concrete product requirement.

The current `/api/chat` endpoint is sufficient for the conversational application.

---

# 38. Deployment Considerations

The local API runs as a FastAPI process.

A future Azure deployment could follow:

```text
                    Internet
                       │
                       ▼
                 Frontend
                       │
                       ▼
              Azure Container Apps
                       │
                       ▼
                    FastAPI
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Agent        Analytics     Config
          │            │
          ▼            ▼
        Groq        Azure SQL
```

Additional enterprise services could be introduced around this core architecture as required.

---

# 39. FDE Perspective

The API is the **contract between the user experience and the intelligence layer**.

An FDE should think about an API in terms of:

```text
Contract
Reliability
Security
Observability
Validation
Scalability
Failure handling
```

Not simply:

```text
"Which endpoint should I create?"
```

The important architecture is:

```text
Frontend
   ↓
Stable API Contract
   ↓
Application Logic
   ↓
Agent
   ↓
Deterministic Tools
   ↓
Data
```

Each layer has a clearly defined responsibility.

---

# 40. API Design Principles

The current implementation follows several principles.

### 1. Validate at the boundary

Invalid requests should not reach the agent.

### 2. Keep business logic out of routes

Routes should orchestrate services rather than contain SQL.

### 3. Keep secrets server-side

The browser never receives the Groq API key.

### 4. Return structured responses

The frontend should not need to parse natural-language text to discover charts or tool usage.

### 5. Make requests traceable

Every request receives a request ID.

### 6. Separate health from readiness

Application availability and dependency readiness are different concepts.

### 7. Keep the LLM behind an application boundary

The LLM should not directly control infrastructure or arbitrary database operations.

---

# 41. Mental Model

The simplest way to understand the API is:

```text
                  USER
                    │
                    ▼
               React UI
                    │
                    │ JSON
                    ▼
             ┌──────────────┐
             │   FastAPI    │
             │     API      │
             └──────┬───────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
    Conversation         Analytics
       State               Agent
                             │
                             ▼
                        Tool Layer
                             │
                             ▼
                          SQLite
                             │
                             ▼
                      Deterministic
                         Results
                             │
                             ▼
                       LLM Synthesis
                             │
                             ▼
                    Structured Response
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
             Answer                   Chart Data
                │                         │
                └────────────┬────────────┘
                             ▼
                         React UI
```

---

# 42. Summary

The CPG Analytics Copilot API provides a thin but structured REST layer around the analytics agent.

The primary endpoint is:

```text
POST /api/chat
```

while:

```text
GET /health
GET /readiness
```

provide operational health and readiness signals.

The API provides:

* validated inputs
* conversation context
* agent orchestration
* deterministic analytics results
* structured visualization data
* request tracing
* controlled errors
* configurable CORS
* a clear backend/frontend boundary

The central design principle is:

> **The API should expose business capabilities and structured application contracts, while hiding infrastructure and implementation details from the client.**

This creates a clean foundation for evolving the training project toward a production-style enterprise AI application.
