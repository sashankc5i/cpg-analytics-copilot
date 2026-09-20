# System Architecture

## 1. Overview

**CPG Analytics Copilot** is an enterprise-style AI analytics application designed to help business users investigate Consumer Packaged Goods (CPG) performance using natural language.

The system combines:

* React + TypeScript for the user interface
* FastAPI for the application API
* Groq for natural-language reasoning and tool selection
* SQLite as the structured data store
* SQL and Python for deterministic analytics
* Plotly for analytical visualizations
* Pytest for automated testing

The core architectural principle is:

> **The LLM is not the source of truth. Deterministic analytics systems are.**

The LLM is responsible for understanding the user's intent, selecting appropriate analytics capabilities, interpreting returned results, and communicating insights.

Business metrics are calculated by deterministic SQL/Python components.

---

# 2. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │       React          │
                         │    TypeScript UI     │
                         │                      │
                         │  Chat + Visualization│
                         └──────────┬───────────┘
                                    │
                                    │ HTTP / REST
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │      API Layer       │
                         │                      │
                         │ Validation           │
                         │ Request IDs          │
                         │ Error Handling       │
                         │ Response Contracts   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Analytics Agent   │
                         │                      │
                         │ Conversation Context │
                         │ Tool Orchestration   │
                         │ Reasoning            │
                         └──────────┬───────────┘
                                    │
                                    │ Tool Calls
                                    ▼
                         ┌──────────────────────┐
                         │       Groq LLM       │
                         │                      │
                         │ Intent Understanding │
                         │ Tool Selection       │
                         │ Result Synthesis     │
                         └──────────┬───────────┘
                                    │
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │ SQL         │       │ Python      │       │ Visualization│
       │ Analytics   │       │ Analytics   │       │ Builder      │
       └──────┬──────┘       └──────┬──────┘       └─────────────┘
              │                     │
              ▼                     ▼
       ┌─────────────────────────────────────┐
       │              SQLite                 │
       │                                     │
       │ Customers                           │
       │ Products                            │
       │ Stores                              │
       │ Sales                               │
       │ Promotions                          │
       │ Inventory                           │
       └─────────────────────────────────────┘
```

---

# 3. Architectural Layers

The application is divided into the following logical layers:

```text
Presentation Layer
        ↓
API Layer
        ↓
Agent / Orchestration Layer
        ↓
Analytics Tool Layer
        ↓
Data Layer
```

Cross-cutting concerns surround these layers:

```text
Configuration
Logging
Validation
Error Handling
Testing
Observability
```

---

# 4. Presentation Layer

## Technology

* React
* TypeScript
* Vite
* Axios
* Plotly

## Responsibilities

The frontend is responsible for:

* collecting user questions
* maintaining the local chat display
* showing loading states
* displaying errors
* rendering assistant responses
* displaying tool usage information
* rendering analytical visualizations

The frontend does **not** perform business calculations.

For example, the frontend does not calculate:

```text
Revenue
=
SUM(sales_amount)
```

Instead, the backend returns deterministic analytical results and the frontend renders them.

---

# 5. API Layer

## Technology

FastAPI.

The API acts as the boundary between the frontend and backend application.

Primary endpoints:

```text
GET  /health
GET  /readiness
POST /api/chat
```

## Responsibilities

The API layer handles:

* HTTP requests
* request validation
* CORS
* request IDs
* exception handling
* response validation
* conversation/session routing

The API does not contain the core business analytics logic.

---

# 6. Request Lifecycle

A typical request follows this flow:

```text
User
 │
 │ "Why is revenue changing?"
 ▼
React
 │
 │ POST /api/chat
 ▼
FastAPI
 │
 ├── Validate request
 │
 ├── Generate request ID
 │
 ├── Load conversation history
 │
 ▼
Analytics Agent
 │
 ▼
Groq
 │
 │ Determine required tools
 ▼
Analytics Tools
 │
 ├── Monthly Sales
 ├── Regional Sales
 ├── Product Performance
 ├── Category Performance
 ├── Promotion Impact
 └── Inventory Performance
 │
 ▼
SQLite / Python Analytics
 │
 ▼
Deterministic Results
 │
 ▼
Groq
 │
 │ Synthesize evidence
 ▼
Analytics Agent
 │
 ▼
FastAPI
 │
 ├── Build visualization
 ├── Validate response
 └── Return structured response
 │
 ▼
React
 │
 ├── Render answer
 └── Render chart
```

---

# 7. Agent Layer

The agent is the central orchestration component.

## Responsibilities

The agent is responsible for:

1. Understanding the user's question.
2. Determining whether analytics tools are required.
3. Selecting appropriate tools.
4. Executing tools.
5. Passing tool results back to the LLM.
6. Supporting multi-tool investigations.
7. Using conversation context.
8. Synthesizing grounded business explanations.

The agent is **not responsible for calculating business metrics**.

---

# 8. LLM Responsibilities

Groq is used as the reasoning and language layer.

The model performs:

```text
Natural Language Understanding
            ↓
Intent Identification
            ↓
Tool Selection
            ↓
Result Interpretation
            ↓
Evidence Synthesis
            ↓
Natural Language Response
```

The model does not directly query SQLite.

Instead:

```text
User
 ↓
LLM
 ↓
Tool
 ↓
SQLite / Python
 ↓
Result
 ↓
LLM
 ↓
Answer
```

This creates a controlled boundary between probabilistic reasoning and deterministic computation.

---

# 9. Tool Layer

The agent exposes specialized analytics capabilities.

## Available Tools

| Tool                               | Responsibility                                                      |
| ---------------------------------- | ------------------------------------------------------------------- |
| `get_overall_sales`                | Overall revenue, transactions, units, and average transaction value |
| `get_sales_by_region`              | Regional sales performance                                          |
| `get_monthly_sales_trend`          | Monthly sales trends                                                |
| `get_top_products`                 | Top products by revenue                                             |
| `get_sales_by_category`            | Category-level performance                                          |
| `get_customer_segment_performance` | Customer segment performance                                        |
| `get_promotion_impact`             | Promotion vs non-promotion comparison                               |
| `get_stockout_rate`                | Regional stockout rates                                             |

Each tool represents a controlled analytical capability.

The LLM cannot arbitrarily execute SQL.

---

# 10. Simple Tool Execution

For a simple question:

```text
"What is our total revenue?"
```

the expected flow is:

```text
User Question
      ↓
Groq
      ↓
get_overall_sales
      ↓
SQLite
      ↓
Revenue Result
      ↓
Groq
      ↓
Business Answer
```

This keeps the analytical computation deterministic.

---

# 11. Multi-Tool Diagnostic Workflow

Some questions cannot be answered reliably using a single metric.

For example:

```text
"Why is revenue changing?"
```

The agent can investigate several dimensions.

```text
                Revenue Change
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
     Trend         Region        Products
        │             │             │
        └─────────────┼─────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Category   Promotions   Inventory
          │           │           │
          └───────────┼───────────┘
                      ▼
                 Evidence
                      │
                      ▼
                 Synthesis
```

The agent is instructed to:

1. Determine whether a measurable change exists.
2. Identify where the change occurred.
3. Identify products/categories contributing to it.
4. Examine promotion behavior.
5. Examine inventory/stockout behavior.
6. Synthesize the evidence.
7. Distinguish facts from possible explanations.

---

# 12. Causality Boundary

The system deliberately separates correlation from causation.

For example, the system should not automatically conclude:

```text
Stockouts caused the revenue decline.
```

when the available data only shows:

```text
Revenue declined
+
Stockout rates increased
```

Instead, the system should communicate:

```text
Revenue declined during periods with elevated
stockout rates. This suggests a possible
relationship, but the available data does not
establish causation.
```

This prevents unsupported causal claims.

---

# 13. Data Layer

SQLite is the current system of record.

The database contains six primary tables:

```text
Customers
Products
Stores
Sales
Promotions
Inventory
```

The transactional center of the model is the `sales` table.

```text
Customers ──────┐
                │
Products ───────┼──→ Sales
                │
Stores ─────────┘

Products ───────→ Promotions
Stores ─────────→ Promotions

Products ───────→ Inventory
Stores ─────────→ Inventory
```

---

# 14. Analytics Layer

The analytics layer is intentionally deterministic.

It consists primarily of:

* SQL
* Python
* Pandas
* NumPy

Examples include:

```text
SUM(sales_amount)
GROUP BY region
GROUP BY category
GROUP BY customer_segment
Monthly aggregation
Promotion comparison
Stockout rate calculation
```

The analytics layer can therefore be tested independently of the LLM.

---

# 15. Visualization Architecture

Visualization follows the same separation principle.

The backend determines:

```text
What data should be visualized?
What chart type is appropriate?
What labels/data should be provided?
```

The frontend determines:

```text
How the chart is rendered.
```

The flow is:

```text
Analytics Tool
      ↓
Tool Result
      ↓
Visualization Builder
      ↓
Visualization Configuration
      ↓
FastAPI Response
      ↓
React
      ↓
Plotly
```

For example:

```text
get_monthly_sales_trend
          ↓
Visualization Builder
          ↓
type = line
x = months
y = revenue
          ↓
React Plotly
```

---

# 16. Conversation Architecture

Conversation state is currently maintained through an in-memory session manager.

```text
conversation_id
       │
       ▼
ConversationManager
       │
       ├── User message
       ├── Assistant response
       ├── User message
       └── Assistant response
```

This enables follow-up questions such as:

```text
User:
Which region performs best?

Assistant:
South performs best...

User:
Why?
```

The second question can use the previous conversation context.

## Production Evolution

The current in-memory implementation can later be replaced by:

```text
Conversation API
      ↓
Redis / persistent session store
```

without changing the core agent architecture.

---

# 17. Configuration Architecture

Configuration is centralized through Pydantic Settings.

```text
Environment Variables
        │
        ▼
    config.py
        │
        ├── Groq API Key
        ├── Groq Model
        ├── Tool Iteration Limit
        ├── CORS Origins
        ├── Application Name
        └── Application Version
```

Application components consume configuration through the settings layer instead of reading environment variables independently.

This makes the system easier to configure across:

```text
Development
Testing
Staging
Production
```

---

# 18. Logging and Request Tracing

Every HTTP request receives a unique request ID.

```text
Request
   │
   ▼
Request ID
   │
   ├── API Log
   ├── Agent Log
   ├── Tool Execution
   └── Completion Log
```

The request ID is also returned through:

```text
X-Request-ID
```

This provides a basic correlation mechanism for debugging.

Example:

```text
request_id=abc123
```

can be used to correlate:

```text
request_started
chat_request
chat_completed
request_completed
```

---

# 19. Error Handling

The system separates common failure boundaries.

```text
Invalid Request
      ↓
HTTP 400

Runtime Failure
      ↓
HTTP 500

Service Not Ready
      ↓
HTTP 503
```

Tool execution errors are captured by the agent and returned as structured tool results rather than silently disappearing.

The application also limits agent tool-calling iterations to prevent runaway execution.

---

# 20. Input Validation

The API validates user input before it reaches the agent.

Current boundaries include:

```text
message
 ├── minimum length
 └── maximum length

conversation_id
 ├── minimum length
 └── maximum length
```

Tool arguments are also validated.

For example:

```text
get_top_products(limit)
```

only accepts:

```text
1 <= limit <= 50
```

This creates two validation boundaries:

```text
User
 ↓
API Validation
 ↓
Agent
 ↓
Tool Validation
 ↓
Analytics
```

---

# 21. Agent Reliability

The agent has a maximum number of tool-calling iterations.

```text
MAX_TOOL_ITERATIONS = 8
```

This protects against an agent entering an uncontrolled loop.

The execution pattern is:

```text
LLM
 ↓
Tool Call
 ↓
Tool Result
 ↓
LLM
 ↓
Tool Call
 ↓
Tool Result
 ↓
...
 ↓
Final Answer
```

If the iteration limit is exceeded, the agent raises a controlled runtime error.

---

# 22. API Response Contract

The API uses a Pydantic response model.

Conceptually:

```text
ChatResponse
 ├── answer
 ├── tools_used
 ├── tool_results
 ├── visualization
 └── conversation_id
```

This ensures the frontend receives a predictable response structure.

The contract also provides a clear boundary between backend and frontend teams.

---

# 23. Health and Readiness

The application exposes two operational endpoints.

## Health

```text
GET /health
```

Answers:

> Is the application process alive?

## Readiness

```text
GET /readiness
```

Answers:

> Is the application sufficiently configured to serve requests?

This distinction becomes important when the application is eventually deployed to a containerized environment.

---

# 24. Testing Architecture

Testing is divided into deterministic and LLM-dependent evaluation.

```text
                    Testing
                       │
          ┌────────────┴────────────┐
          │                         │
    Deterministic Tests       Live LLM Evaluation
          │                         │
          ▼                         ▼
       Pytest                 Explicit benchmark
          │                         │
          ├── Analytics             ├── Tool selection
          ├── Safety                ├── Groundedness
          ├── Integrity             ├── Reasoning
          ├── Conversation          └── Model behavior
          └── API
```

Normal `pytest` execution does not depend on repeated live LLM calls.

This prevents:

* rate-limit failures
* unnecessary token consumption
* slow test execution
* nondeterministic CI behavior

Live LLM evaluation is intentionally treated as a separate activity.

---

# 25. Evaluation Architecture

The evaluation framework measures several dimensions.

## Tool Selection

Does the agent choose the correct analytical capability?

## Groundedness

Does the answer have supporting tool execution and results?

## Data Integrity

Do dimensional results reconcile with overall totals?

For example:

```text
Sum(regional revenue)
        =
Overall revenue
```

## Multi-turn Reasoning

Can follow-up questions use previous context?

## Tool Safety

Are invalid tool arguments rejected?

---

# 26. Security Boundary

The current implementation establishes basic security-oriented boundaries:

```text
Environment secrets
        ↓
Configuration layer

User input
        ↓
API validation

LLM tool arguments
        ↓
Tool validation

Business calculations
        ↓
Deterministic analytics
```

The current training implementation does not yet include:

* user authentication
* authorization
* role-based access control
* network isolation
* managed identity
* production secret management

These are deployment-stage concerns for a production Azure implementation.

---

# 27. Current Deployment Model

The current project is intentionally local.

```text
Developer Machine
│
├── FastAPI
├── SQLite
├── Groq API
└── React/Vite
```

No production deployment is currently configured.

This keeps the training project focused on:

* system design
* AI orchestration
* data engineering
* analytics
* application engineering
* evaluation

---

# 28. Future Production Architecture

A future enterprise deployment could evolve toward:

```text
                         Users
                           │
                           ▼
                    Azure Front Door
                           │
                           ▼
                 React / Static Web App
                           │
                           ▼
                  Azure Container Apps
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        FastAPI Agent              Background Jobs
              │
              ├───────────────┐
              │               │
              ▼               ▼
       Azure AI Foundry   Analytics Tools
              │               │
              │               ▼
              │         Azure SQL
              │
              ▼
       Azure AI Services
```

Additional enterprise services could include:

```text
Microsoft Entra ID
Azure Key Vault
Azure AI Search
Azure Monitor
Application Insights
Microsoft Defender for Cloud
Azure Policy
Private Endpoints
Azure DevOps
```

These are future production extensions rather than requirements of the current training implementation.

---

# 29. Key Architectural Decisions

## Decision 1 — LLM does not directly access the database

Reason:

* improves control
* reduces hallucination risk
* improves testability
* creates explicit analytical capabilities

## Decision 2 — Deterministic analytics

Reason:

* business metrics must be reproducible
* easier debugging
* easier validation
* easier evaluation

## Decision 3 — Tool-based architecture

Reason:

* modular capabilities
* explicit boundaries
* easier extension
* easier observability

## Decision 4 — Separate visualization generation from rendering

Reason:

* backend controls analytical intent
* frontend controls presentation
* keeps UI flexible

## Decision 5 — Separate deterministic tests from live LLM evaluation

Reason:

* prevents rate-limit dependency
* reduces cost
* improves test speed
* makes CI more reliable

## Decision 6 — In-memory conversation state for training

Reason:

* simple implementation
* sufficient for local development
* easy to replace with persistent storage later

---

# 30. Architectural Mental Model

The entire system can be summarized as:

```text
                     USER
                       │
                       ▼
                  React UI
                       │
                       ▼
                  FastAPI
                       │
              Validation + ID
                       │
                       ▼
                 Agent Layer
                       │
                       ▼
                     Groq
                       │
                "What tools?"
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
       Sales        Products      Inventory
         │             │             │
         └─────────────┼─────────────┘
                       ▼
                Deterministic
                   Analytics
                       │
                       ▼
                  SQLite Data
                       │
                       ▼
                  Tool Results
                       │
                       ▼
                     Groq
                       │
                "What does it
                  mean?"
                       │
                       ▼
                Business Answer
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          Text Answer         Chart Config
             │                   │
             └─────────┬─────────┘
                       ▼
                    React
```

The fundamental separation is:

```text
             ┌──────────────────────┐
             │     Probabilistic    │
             │        Layer         │
             │                      │
             │        Groq          │
             │     Reasoning        │
             └──────────┬───────────┘
                        │
                  Tool Boundary
                        │
             ┌──────────▼───────────┐
             │     Deterministic    │
             │        Layer         │
             │                      │
             │ SQL / Python / Data  │
             └──────────────────────┘
```

This boundary is the core architectural decision of the CPG Analytics Copilot.

> **Use AI for understanding and reasoning. Use deterministic systems for facts, calculations, and business truth.**
