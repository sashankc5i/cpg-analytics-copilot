# Nexa Analytics Copilot --- Architecture

## 1. Purpose

Nexa Analytics Copilot is an enterprise-style conversational analytics
application for a fictional CPG organization.

The architecture is designed around a clear separation between:

-   User interaction
-   API orchestration
-   LLM reasoning
-   Approved analytical capabilities
-   Business analytics
-   Database access
-   Persistent analytical data

The central architectural principle is:

> **The LLM is not the source of truth.**

The database and deterministic analytics code provide the authoritative
numerical evidence. The LLM interprets user intent, selects approved
capabilities, interprets returned evidence, and produces a
natural-language response.

------------------------------------------------------------------------

## 2. High-Level Architecture

``` text
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                                                              │
│                  React + TypeScript + Vite                   │
│                                                              │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │   Copilot    │  │  Investigation │  │ Conversation UI │ │
│  └──────────────┘  └────────────────┘  └─────────────────┘ │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             │ REST / Streaming
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                         BACKEND                              │
│                                                              │
│                       FastAPI API                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  Agent / Workflow Layer                │  │
│  │                                                        │  │
│  │  Analytics Agent                                      │  │
│  │  Investigation Planner                                 │  │
│  │  Hypothesis Generator                                  │  │
│  │  Challenge Reviewer                                    │  │
│  │  Conversation Management                               │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    Tool Layer                          │  │
│  │                                                        │  │
│  │  Sales / Product / Customer / Promotion / Inventory    │  │
│  │  Analytics Tools                                       │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  Analytics Layer                       │  │
│  │                                                        │  │
│  │  Business calculations                                 │  │
│  │  Trend analysis                                        │  │
│  │  Anomaly detection                                     │  │
│  │  Investigation evidence                                │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                 Repository Layer                       │  │
│  │                                                        │  │
│  │  Approved domain-specific database operations           │  │
│  └───────────────────────────┬────────────────────────────┘  │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       SQLite        │
                    │                     │
                    │ customers           │
                    │ products            │
                    │ stores              │
                    │ sales               │
                    │ promotions          │
                    │ inventory           │
                    └─────────────────────┘

                         ┌─────────────┐
                         │    Groq     │
                         │    LLM      │
                         └──────┬──────┘
                                │
                    Reasoning / tool selection /
                    synthesis / challenge review
```

------------------------------------------------------------------------

# 3. Architectural Layers

## 3.1 Frontend Layer

### Technology

-   React
-   TypeScript
-   Vite
-   Plotly / `react-plotly.js`

### Responsibilities

The frontend is responsible for:

-   Rendering the conversational interface
-   Sending user questions to the backend
-   Maintaining the active conversation identity
-   Displaying conversation history
-   Switching between Copilot and Investigation workspaces
-   Displaying investigation progress
-   Displaying challenge responses
-   Rendering tables and visualizations
-   Managing conversation actions such as rename, archive, restore, and
    delete

The frontend does **not** perform analytical calculations.

It receives structured results from the backend and presents them to the
user.

------------------------------------------------------------------------

# 4. API Layer

The backend uses FastAPI as the application boundary between the
frontend and the internal AI/analytics services.

Responsibilities include:

-   Request validation
-   Conversation lifecycle endpoints
-   Chat orchestration
-   Investigation streaming
-   Challenge streaming
-   Error handling
-   Request logging
-   Middleware-level request tracking

The API layer should remain independent of the internal implementation
of analytics and database access.

Conceptually:

``` text
Frontend
   │
   ▼
FastAPI
   │
   ├── Conversation APIs
   ├── Chat API
   ├── Investigation API
   └── Challenge API
```

------------------------------------------------------------------------

# 5. Agent Layer

The agent layer is responsible for translating natural-language business
questions into controlled analytical actions.

The primary analytics agent uses Groq with the configured model:

``` text
openai/gpt-oss-20b
```

The agent receives:

-   System instructions
-   Conversation history
-   Current user question
-   Approved tool definitions

The agent can select only tools exposed through the tool layer.

------------------------------------------------------------------------

## 5.1 Standard Copilot Flow

``` text
User Question
      │
      ▼
Analytics Agent
      │
      ├── No tool required ───────────────► Natural-language answer
      │
      └── Tool required
              │
              ▼
        Approved Tool
              │
              ▼
          Analytics
              │
              ▼
         Repository
              │
              ▼
           SQLite
              │
              ▼
      Deterministic Result
              │
              ▼
        Analytics Agent
              │
              ▼
       Final Response
```

This keeps the LLM involved in reasoning without allowing it to directly
manipulate the database.

------------------------------------------------------------------------

# 6. Tool Layer

The tool layer defines the capabilities available to the LLM.

Current analytical tools include:

-   `get_overall_sales`
-   `get_sales_by_region`
-   `get_monthly_sales_trend`
-   `get_top_products`
-   `get_sales_by_category`
-   `get_customer_segment_performance`
-   `get_promotion_impact`
-   `get_stockout_rate`
-   `get_revenue_anomalies`

The tool layer acts as a controlled capability boundary.

The LLM does not receive unrestricted database access.

------------------------------------------------------------------------

## 6.1 Tool Execution Boundary

``` text
                 LLM
                  │
                  ▼
          Tool selection
                  │
                  ▼
        execute_tool(...)
                  │
                  ▼
           Analytics API
                  │
                  ▼
            Repository
                  │
                  ▼
             Database
```

Tool arguments are validated before execution.

For example, product-ranking operations enforce a bounded maximum result
size.

This prevents the model from requesting arbitrarily large analytical
results.

------------------------------------------------------------------------

# 7. Analytics Layer

The analytics layer contains business and analytical logic.

Examples include:

-   Revenue aggregation
-   Regional sales analysis
-   Product ranking
-   Category analysis
-   Customer segment performance
-   Promotion impact analysis
-   Inventory stockout analysis
-   Revenue anomaly detection

The analytics layer should not be responsible for low-level database
connection management.

Instead:

``` text
Analytics
    │
    ▼
Repository
```

This separation allows analytical logic to be tested independently from
database mechanics.

------------------------------------------------------------------------

# 8. Repository Layer

The repository layer is the application's database access boundary.

Current repositories include:

``` text
sales_repository.py
product_repository.py
customer_repository.py
promotion_repository.py
inventory_repository.py
```

Repositories expose approved, domain-specific operations.

They do not expose arbitrary SQL execution to the agent or analytics
layers.

------------------------------------------------------------------------

## 8.1 Why the Repository Boundary Exists

Without a repository boundary, SQL can become distributed throughout:

``` text
Agent
Analytics
Tools
API
```

That makes the system harder to test and harder to migrate to another
database technology.

Instead, Nexa uses:

``` text
Agent
  ↓
Tools
  ↓
Analytics
  ↓
Repositories
  ↓
Database
```

The result is a clearer separation of concerns.

------------------------------------------------------------------------

## 8.2 Parameterized SQL

Dynamic SQL values are passed through parameterized database operations.

This prevents application code from constructing unsafe SQL through
direct string interpolation of user-controlled values.

The repository layer is therefore both a structural and security
boundary.

------------------------------------------------------------------------

# 9. Database Layer

SQLite is used as the current analytical datastore.

Primary tables:

``` text
customers
products
stores
sales
promotions
inventory
```

The database schema also includes indexes supporting common analytical
access patterns such as:

-   Sales by date
-   Sales by product
-   Sales by store
-   Sales by customer
-   Inventory by product/store
-   Inventory by date
-   Promotions by product
-   Promotions by date

Database connection management remains isolated in:

``` text
backend/app/database/connection.py
```

------------------------------------------------------------------------

# 10. Investigation Architecture

Investigation mode is a structured workflow rather than a single LLM
prompt.

The workflow is:

``` text
                 User Question
                      │
                      ▼
            ┌───────────────────┐
            │ Investigation      │
            │ Planner            │
            └─────────┬─────────┘
                      │
                      ▼
             Investigation Plan
                      │
                      ▼
            ┌───────────────────┐
            │ Hypothesis        │
            │ Generator         │
            └─────────┬─────────┘
                      │
                      ▼
                Hypotheses
                      │
                      ▼
            Evidence Collection
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Revenue      Region      Product
          │           │           │
          └───────────┼───────────┘
                      │
                      ▼
               Evidence Set
                      │
                      ▼
            Evidence Synthesis
                      │
                      ▼
               Conclusion
```

The investigation planner chooses relevant investigation areas from the
approved catalog.

The evidence collector then executes deterministic analytical
operations.

The LLM synthesizes the resulting evidence rather than inventing the
underlying numerical facts.

------------------------------------------------------------------------

# 11. Investigation Catalog

The current investigation catalog contains:

``` text
revenue_trend
regional_performance
product_performance
category_performance
customer_segments
promotion_impact
inventory_stockouts
```

These investigation areas map to approved analytical tools.

This creates a controlled relationship:

``` text
Investigation Area
       │
       ▼
Approved Tool
       │
       ▼
Deterministic Evidence
```

------------------------------------------------------------------------

# 12. Hypothesis Generation

The investigation workflow generates hypotheses after the initial plan.

For example, a question such as:

> Why is revenue changing?

can lead to hypotheses involving:

-   Product mix
-   Regional fluctuations
-   Customer-segment changes
-   Promotion effects
-   Inventory stockouts

Each hypothesis is associated with relevant evidence areas.

The hypotheses are investigation directions, not facts.

The evidence collection stage determines what the available data
supports.

------------------------------------------------------------------------

# 13. Evidence Synthesis

Evidence is collected deterministically before synthesis.

Conceptually:

``` text
Hypothesis
    │
    ▼
Evidence requirements
    │
    ▼
Approved analytics
    │
    ▼
Structured evidence
    │
    ▼
LLM synthesis
```

The synthesis layer is instructed to distinguish evidence from
interpretation.

This reduces the risk of presenting unsupported causal claims as
established facts.

------------------------------------------------------------------------

# 14. Challenge My Conclusion

Challenge mode reuses the completed investigation rather than starting
an unrelated second investigation.

Architecture:

``` text
Completed Investigation
        │
        ├── Original conclusion
        └── Existing evidence
                 │
                 ▼
        Direct Challenge Reviewer
                 │
                 ▼
              Groq
                 │
                 ▼
        ┌──────────────────────┐
        │ Supporting evidence  │
        │ Contradicting limits │
        │ Missing evidence     │
        │ Alternative causes   │
        │ Bottom line          │
        └──────────────────────┘
```

The current implementation uses one bounded Groq synthesis call for the
challenge review.

This keeps the challenge workflow focused and avoids unnecessarily
repeating the entire investigation process.

------------------------------------------------------------------------

# 15. Anomaly Detection Architecture

Revenue anomaly detection is deterministic.

The engine:

1.  Retrieves monthly revenue data.
2.  Requires at least three months of history.
3.  Calculates the expected revenue as the mean of the previous three
    months.
4.  Compares the current month against that baseline.
5.  Calculates percentage deviation.
6.  Classifies the deviation.

``` text
Monthly Revenue
      │
      ▼
Previous 3 Months
      │
      ▼
Historical Mean
      │
      ▼
Current Month Comparison
      │
      ▼
Deviation %
      │
      ▼
Classification
```

Thresholds:

``` text
< 10%       Normal
10–20%      Low
20–30%      Medium
>= 30%      High
```

The current synthetic dataset produces no non-normal monthly revenue
anomalies under these thresholds.

------------------------------------------------------------------------

# 16. Conversation Architecture

Conversation identity is shared across the application's conversational
workflows.

``` text
                    Conversation
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Copilot      Investigation    Challenge
          │              │              │
          └──────────────┼──────────────┘
                         │
                  conversation_id
```

This allows a user to move between Copilot and Investigation without
creating unrelated conversational contexts.

The conversation manager currently maintains:

-   Conversation ID
-   Title
-   Created timestamp
-   Updated timestamp
-   Archive state
-   Message history

Investigation memory additionally maintains:

-   Latest investigation plan
-   Latest evidence
-   Latest answer

------------------------------------------------------------------------

# 17. Conversation Lifecycle

``` text
Create
  │
  ▼
Active Conversation
  │
  ├── Rename
  │
  ├── Continue conversation
  │
  ├── Archive ─────► Archived
  │                     │
  │                     └── Restore
  │
  └── Delete
```

Conversation titles are initially derived from the first user question.

The frontend provides conversation management actions while the backend
owns the conversation lifecycle operations.

------------------------------------------------------------------------

# 18. Streaming Architecture

Investigation and challenge workflows use streaming responses so that
long-running AI workflows can communicate progress/results to the
frontend.

Conceptually:

``` text
Backend workflow
      │
      ├── Start
      ├── Plan
      ├── Hypothesis
      ├── Evidence
      ├── Answer tokens
      └── Complete
               │
               ▼
            Frontend
```

This allows the interface to represent a multi-stage analytical process
rather than waiting silently for one large response.

------------------------------------------------------------------------

# 19. Security and Reliability Boundaries

The current implementation applies several application-level controls.

### Controlled LLM capabilities

The LLM can only call explicitly defined tools.

### Bounded tool execution

Agent execution is limited by a maximum tool-iteration configuration.

### Bounded challenge synthesis

Challenge generation uses a bounded output size and one controlled
synthesis call.

### Parameterized database operations

Repository operations use parameterized SQL values.

### No direct LLM database access

The model cannot directly issue arbitrary SQL against the database.

### Error isolation

Tool execution errors are converted into structured error results rather
than allowing uncontrolled failures to propagate through the entire
agent workflow.

------------------------------------------------------------------------

# 20. Observability

The backend includes application logging and request middleware.

Logging can capture information such as:

-   Request ID
-   HTTP method
-   API path
-   Conversation ID
-   Investigation activity
-   Tool execution activity
-   Workflow stages

This creates a traceable application flow such as:

``` text
Request
  ↓
Conversation ID
  ↓
Agent / workflow
  ↓
Tool
  ↓
Analytics
  ↓
Repository
  ↓
Result
```

The current implementation is an application-level observability
foundation rather than a complete production telemetry platform.

------------------------------------------------------------------------

# 21. Deployment Boundary

The current project is designed primarily as a local development and FDE
training implementation.

The logical deployment boundary is:

``` text
Browser
   │
   ▼
Frontend Application
   │
   ▼
FastAPI Service
   │
   ├── Groq API
   │
   └── SQLite
```

The architecture deliberately keeps the application layers separated so
that individual infrastructure components can later be replaced.

For example:

``` text
SQLite
  ↓
Production relational/analytical database
```

could be introduced primarily through the repository/data-access
boundary rather than rewriting the entire agent.

------------------------------------------------------------------------

# 22. Current Architectural Limitations

The current architecture intentionally contains several limitations.

## In-memory conversation state

Conversation management currently uses in-memory application state.

Therefore:

``` text
Frontend refresh
      ↓
Same backend process
      ↓
Conversation state remains
```

but:

``` text
Backend restart
      ↓
In-memory state cleared
      ↓
Conversation history lost
```

Persistent conversation storage is a future hardening item.

## SQLite

SQLite provides a lightweight, portable development datastore but is not
intended to represent the final enterprise-scale data platform.

## Synthetic data

The CPG dataset is generated synthetic data and does not represent a
real organization's production data.

## Frontend bundle size

The current frontend build reports a bundle-size warning. Code splitting
and dependency optimization are future optimization work.

------------------------------------------------------------------------

# 23. Architectural Principles

The implementation follows these principles:

### Separation of concerns

Each layer owns a distinct responsibility.

### Least privilege for AI

The model receives only the analytical capabilities explicitly exposed
as tools.

### Deterministic source of truth

Numerical business calculations remain deterministic.

### Evidence before conclusion

Investigation workflows collect evidence before synthesis.

### Explicit uncertainty

The system should distinguish evidence, interpretation, and unsupported
causal claims.

### Testable boundaries

Analytics, repositories, agent behavior, and API behavior can be tested
independently.

### Replaceable infrastructure

Database-specific mechanics are isolated from business analytics and
agent logic.

------------------------------------------------------------------------

# 24. Final Architecture Summary

Nexa's architecture can be summarized as:

``` text
                         USER
                           │
                           ▼
                    React Frontend
                           │
                           ▼
                      FastAPI
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       Conversational Agent       Investigation
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                    Approved Tools
                           │
                           ▼
                      Analytics
                           │
                           ▼
                     Repositories
                           │
                           ▼
                        SQLite
```

With Groq providing:

``` text
Intent interpretation
Tool selection
Hypothesis generation
Evidence synthesis
Natural-language response
Challenge review
```

and the application providing:

``` text
Data access
Business calculations
Evidence generation
Validation
Execution boundaries
Conversation management
```

This separation is the core architectural pattern demonstrated by the
project.
