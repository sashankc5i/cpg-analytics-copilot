# Architecture & Design Decisions

## 1. Purpose

This document records the important architectural decisions made while
building the Nexa Consumer Products Analytics Copilot.

The purpose is not to document every implementation detail. It is to
preserve the reasoning behind decisions that affect:

-   system boundaries
-   data access
-   AI orchestration
-   analytical correctness
-   investigation workflows
-   conversation state
-   reliability
-   future extensibility

These decisions provide context for future maintainers and demonstrate
the engineering trade-offs made during the project.

------------------------------------------------------------------------

# 2. Decision Summary

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Application architecture            Layered architecture

  Source of analytical truth          SQLite + deterministic analytics

  LLM responsibility                  Interpretation and orchestration

  Database access                     Repository layer

  SQL execution                       Restricted to repositories

  Agent data access                   Approved tools only

  Analytics logic                     Separate from database mechanics

  Standard agent loop                 Bounded tool-calling loop

  Investigation workflow              Structured multi-stage workflow

  Investigation state                 Separate analytical memory

  Conversation identity               Shared `conversation_id`

  Challenge workflow                  Direct adversarial review of
                                      existing evidence

  Anomaly detection                   Deterministic statistical logic

  Streaming                           NDJSON for long-running workflows

  Conversation persistence            In-memory for current training
                                      implementation

  Database                            SQLite

  Dataset                             Synthetic CPG data

  Authentication                      Not implemented

  Deployment                          Not implemented
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 3. Layered Application Architecture

## Decision

Use the following application boundary:

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

## Why

A conversational AI application can become difficult to maintain when
the LLM, SQL, business logic, and API behavior are mixed together.

The layered design gives each part a clear responsibility.

### Agent

Responsible for:

-   interpreting the user request
-   deciding which approved tool to use
-   coordinating tool calls
-   synthesizing evidence

### Tools

Responsible for:

-   exposing approved capabilities to the model
-   validating tool arguments
-   invoking analytics functions

### Analytics

Responsible for:

-   business calculations
-   aggregations
-   analytical transformations
-   deterministic reasoning

### Repositories

Responsible for:

-   SQL execution
-   database access
-   parameterized database operations
-   returning structured data

### Database

Responsible for:

-   storing source data
-   enforcing table relationships
-   executing queries

------------------------------------------------------------------------

# 4. LLM Is Not the Source of Truth

## Decision

The LLM should not independently calculate or invent analytical facts.

The system treats:

``` text
SQLite
+
Deterministic analytics
```

as the source of analytical truth.

The LLM is responsible for interpreting questions and explaining
evidence.

## Why

An LLM can produce fluent numerical statements even when the underlying
calculation is incorrect.

For business analytics, fluency is not sufficient.

The intended flow is:

``` text
User question
      ↓
LLM interpretation
      ↓
Approved analytical tool
      ↓
Deterministic computation
      ↓
Evidence
      ↓
LLM explanation
```

This separation makes analytical answers easier to test and audit.

------------------------------------------------------------------------

# 5. Repository Pattern

## Decision

All application SQL execution belongs in repositories.

Repository modules include:

``` text
sales_repository.py
product_repository.py
customer_repository.py
promotion_repository.py
inventory_repository.py
```

## Why

Before the repository boundary was established, analytical modules could
become coupled to database mechanics.

That creates several problems:

-   difficult testing
-   duplicated SQL
-   unclear ownership
-   harder database replacement
-   weaker architectural boundaries

The repository pattern gives the application a stable data-access
interface.

The intended relationship is:

``` text
Analytics
    ↓
Repository method
    ↓
Parameterized SQL
    ↓
SQLite
```

------------------------------------------------------------------------

# 6. No Arbitrary SQL Tool

## Decision

The agent does not receive a generic SQL execution tool.

Instead, it receives approved domain-specific tools such as:

``` text
get_overall_sales
get_sales_by_region
get_monthly_sales_trend
get_top_products
get_sales_by_category
get_customer_segment_performance
get_promotion_impact
get_stockout_rate
get_revenue_anomalies
```

## Why

A generic SQL tool would give the LLM much broader access to the data
layer.

That could make the system:

-   harder to govern
-   harder to test
-   harder to secure
-   harder to reason about
-   more vulnerable to malformed or unintended queries

Domain-specific tools provide a controlled capability boundary.

------------------------------------------------------------------------

# 7. Parameterized SQL

## Decision

Dynamic SQL values must be supplied through parameterized queries.

## Why

String concatenation should not be used to construct SQL from runtime
values.

Parameterized queries provide a safer and more predictable
database-access pattern.

The repository layer therefore owns both:

``` text
SQL structure
+
SQL parameters
```

while higher layers work with domain-level arguments.

------------------------------------------------------------------------

# 8. Standard Copilot Agent Loop

## Decision

The standard Copilot uses a bounded tool-calling loop.

Conceptually:

``` text
User
 ↓
Groq
 ↓
Tool call?
 ├── No → Final answer
 └── Yes
       ↓
    Execute tool
       ↓
    Tool result
       ↓
     Groq again
       ↓
    ...
```

The loop is controlled by:

``` text
MAX_TOOL_ITERATIONS
```

with the current default:

``` text
8
```

and configuration validation restricting the value to:

``` text
1–20
```

## Why

An agent should not be allowed to continue calling tools indefinitely.

A bounded loop provides:

-   predictable runtime
-   cost control
-   protection against orchestration loops
-   easier debugging
-   clearer operational behavior

------------------------------------------------------------------------

# 9. Temperature and Determinism

## Decision

The standard agent and challenge synthesis use:

``` text
temperature = 0
```

where supported by the current implementation.

## Why

This application is primarily an analytical assistant.

The goal is not creative generation. The goal is consistent
interpretation and grounded synthesis.

Lower randomness makes behavior more repeatable, although it does not
make LLM output perfectly deterministic.

------------------------------------------------------------------------

# 10. Investigation Architecture

## Decision

Investigation is treated as a structured workflow rather than a single
prompt.

The conceptual pipeline is:

``` text
Question
   ↓
Planning
   ↓
Hypotheses
   ↓
Evidence collection
   ↓
Synthesis
```

## Why

A complex analytical question often requires several pieces of evidence.

For example:

``` text
Revenue decline
      ↓
Regional performance
      +
Product performance
      +
Category performance
      +
Promotion impact
      +
Inventory
```

Separating these stages makes the investigation process easier to
inspect and debug.

------------------------------------------------------------------------

# 11. Investigation Catalog

## Decision

Investigations operate through a predefined catalog.

Current investigation areas include:

``` text
revenue_trend
regional_performance
product_performance
category_performance
customer_segments
promotion_impact
inventory_stockouts
```

Each investigation area maps to approved analytical capabilities.

## Why

This prevents the investigation planner from inventing arbitrary
data-access operations.

The planner selects from known capabilities rather than defining its own
database behavior.

------------------------------------------------------------------------

# 12. Hypothesis Generation

## Decision

The investigation workflow generates explicit hypotheses before evidence
synthesis.

Conceptually:

``` text
Question
  ↓
Potential explanations
  ↓
Evidence collection
  ↓
Evaluate explanations
```

## Why

A hypothesis-driven investigation is easier to reason about than simply
collecting large amounts of data.

It also provides a useful structure for Challenge Mode because the
original reasoning can be examined against evidence.

------------------------------------------------------------------------

# 13. Deterministic Evidence Collection

## Decision

Evidence collection is performed through deterministic application
tools.

The LLM may select the analytical area, but the actual evidence comes
from:

``` text
Approved tools
    ↓
Analytics
    ↓
Repositories
    ↓
Database
```

## Why

This preserves the source-of-truth boundary.

The LLM decides what evidence may be relevant.

The application determines what the evidence actually is.

------------------------------------------------------------------------

# 14. Causality Control

## Decision

The system distinguishes observed relationships from proven causal
relationships.

For example:

``` text
Revenue decreased
+
Promotion activity decreased
```

does not automatically prove:

``` text
Promotion decrease caused revenue decrease
```

## Why

Business analytics frequently contains correlated signals.

The system should therefore distinguish:

-   observed fact
-   supporting evidence
-   plausible explanation
-   causal claim

unless the available evidence actually supports a stronger conclusion.

------------------------------------------------------------------------

# 15. Challenge My Conclusion

## Decision

Challenge Mode directly reviews the completed investigation rather than
starting an entirely new investigation.

The architecture is:

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
             One Groq call
                 │
                 ▼
          Challenge report
```

## Why

The purpose of Challenge Mode is to stress-test an existing conclusion.

Repeating the complete investigation would:

-   duplicate evidence collection
-   increase latency
-   increase cost
-   make the challenge less focused

Reusing the existing evidence makes the challenge an actual review of
the conclusion.

------------------------------------------------------------------------

# 16. Bounded Challenge Synthesis

## Decision

Challenge synthesis is limited to one bounded Groq call with a
controlled output size.

The current implementation uses:

``` text
MAX_CHALLENGE_SYNTHESIS_TOKENS = 900
```

and limits the amount of evidence included in the challenge context.

## Why

Challenge Mode is intended to critique the existing investigation, not
become an unbounded second agent.

Bounding the context and output helps control:

-   latency
-   token consumption
-   response size
-   operational unpredictability

------------------------------------------------------------------------

# 17. Anomaly Detection

## Decision

Revenue anomaly detection is deterministic rather than LLM-generated.

Current approach:

``` text
Previous 3 months
       ↓
Mean baseline
       ↓
Current month
       ↓
Deviation %
       ↓
Threshold classification
```

Thresholds:

``` text
< 10%       Normal
10–20%      Low
20–30%      Medium
>= 30%      High
```

The first three months do not have sufficient history for anomaly
detection.

## Why

Anomaly detection is fundamentally a numerical analytical task.

Using deterministic logic provides:

-   repeatability
-   testability
-   transparent thresholds
-   predictable output

The LLM can later explain the anomaly but should not determine whether a
numerical threshold was crossed.

------------------------------------------------------------------------

# 18. Conversation and Investigation Memory

## Decision

Conversation history and investigation analytical state are represented
separately.

``` text
Conversation Manager
    ↓
Messages and conversation metadata

Investigation Session Manager
    ↓
Plan
Evidence
Latest answer
```

Both are linked through:

``` text
conversation_id
```

## Why

A chat message and an analytical investigation are not the same type of
state.

Conversation history answers:

> What did the user and assistant say?

Investigation memory answers:

> What analytical work was performed and what evidence supported the
> conclusion?

Keeping the concepts separate makes Challenge Mode possible without
reconstructing the investigation from raw chat text.

------------------------------------------------------------------------

# 19. Shared Conversation Identity

## Decision

Copilot, Investigation, and Challenge use the same conversation
identity.

``` text
conversation_id
```

is the shared boundary.

Example:

``` text
Copilot
   │
   ├── conversation_id = ABC
   │
Investigation
   │
   ├── conversation_id = ABC
   │
Challenge
   │
   └── conversation_id = ABC
```

## Why

Users should not have to manually connect three different contexts.

A single conversation provides continuity across:

``` text
Ask
 ↓
Investigate
 ↓
Challenge
```

------------------------------------------------------------------------

# 20. In-Memory Conversation Storage

## Decision

Conversation state is currently stored in memory.

## Why

This project is an FDE training implementation rather than a production
deployment.

In-memory storage keeps the architecture simple while demonstrating:

-   conversation lifecycle
-   history management
-   archive/restore
-   investigation memory
-   shared conversation identity

## Trade-off

The state is lost when the backend process restarts.

A production implementation would require durable storage.

------------------------------------------------------------------------

# 21. SQLite

## Decision

SQLite is used as the application datastore.

## Why

The project is designed for learning and local development.

SQLite provides:

-   zero infrastructure setup
-   SQL support
-   relational modeling
-   easy local execution
-   deterministic test environments

It also allows the project to demonstrate repository and analytical
architecture without introducing unnecessary infrastructure.

------------------------------------------------------------------------

# 22. Synthetic Data

## Decision

The CPG dataset is synthetic.

The dataset represents:

``` text
Customers
Products
Stores
Sales
Promotions
Inventory
```

## Why

Synthetic data provides:

-   reproducibility
-   safe development
-   controlled scenarios
-   no sensitive business data
-   predictable test conditions

The generator also uses a fixed random seed so that the dataset can be
reproduced.

------------------------------------------------------------------------

# 23. Streaming with NDJSON

## Decision

Investigation and Challenge responses use:

``` text
application/x-ndjson
```

rather than waiting for one large JSON response.

## Why

These workflows can take longer than a simple analytical query.

Streaming allows the UI to show progress:

``` text
Started
  ↓
Plan
  ↓
Hypotheses
  ↓
Answer starts
  ↓
Tokens
  ↓
Complete
```

This improves perceived responsiveness and exposes useful intermediate
workflow state.

------------------------------------------------------------------------

# 24. REST API Boundary

## Decision

The React frontend communicates with the backend through REST endpoints.

Core endpoints include:

``` text
GET  /health
GET  /readiness

POST /api/chat

POST /api/investigate/stream
POST /api/investigate/challenge/stream

POST   /api/conversations
GET    /api/conversations
GET    /api/conversations/{id}
...
```

## Why

REST provides a clear boundary between:

``` text
Frontend
```

and:

``` text
Backend application
```

It also makes the backend independently testable.

------------------------------------------------------------------------

# 25. Configuration Through Environment Variables

## Decision

Application configuration is loaded through Pydantic Settings and
environment variables.

Important variables include:

``` text
GROQ_API_KEY
GROQ_MODEL
MAX_TOOL_ITERATIONS
CORS_ORIGINS
APP_NAME
APP_VERSION
```

## Why

Secrets and environment-specific configuration should not be hard-coded
into application source.

The committed `.env.example` documents the expected configuration
without exposing real credentials.

------------------------------------------------------------------------

# 26. No Authentication Yet

## Decision

Authentication and authorization are not implemented in the current
training application.

## Why

The current objective is to demonstrate:

-   agent architecture
-   analytics
-   investigation
-   conversation state
-   enterprise integration patterns

Authentication is therefore treated as a deployment/enterprise-hardening
concern rather than part of the current feature scope.

## Production implication

A production implementation would need:

``` text
Identity
 ↓
Authentication
 ↓
Authorization
 ↓
Conversation ownership
 ↓
Data-access controls
```

------------------------------------------------------------------------

# 27. No Persistent Multi-User State Yet

## Decision

The current application does not implement durable multi-user
conversation storage or authorization boundaries.

## Why

The application currently demonstrates the domain behavior with
in-memory state.

This is intentionally documented as a limitation rather than presented
as production-ready persistence.

------------------------------------------------------------------------

# 28. Frontend Visualization

## Decision

The backend can return structured visualization data rather than
returning chart instructions as arbitrary prose.

The visualization contract contains:

``` text
type
title
x
y
```

The frontend renders the visualization through Plotly.

## Why

Charts should be driven by structured data.

The intended boundary is:

``` text
Analytics result
    ↓
Visualization structure
    ↓
Frontend chart renderer
```

rather than asking the LLM to generate executable chart code.

------------------------------------------------------------------------

# 29. Error Handling

## Decision

Known application errors are converted into controlled API responses.

The backend distinguishes between:

``` text
Validation errors
Runtime errors
Unexpected errors
```

The objective is to avoid exposing internal implementation details
unnecessarily while still providing useful diagnostics in logs.

------------------------------------------------------------------------

# 30. Observability

## Decision

The backend uses application logging around important workflows.

Examples include:

``` text
conversation creation
chat execution
investigation execution
challenge execution
```

## Why

Agentic applications are difficult to debug from the final answer alone.

Operational logging helps answer:

``` text
What request arrived?
What workflow ran?
What failed?
Where did it fail?
```

A future production implementation would expand this into structured
telemetry, traces, metrics, and model/tool observability.

------------------------------------------------------------------------

# 31. Data Quality Limitation

## Decision

The current synthetic sales generator does not constrain sales based on
inventory stockouts.

Therefore:

``` text
stockout_flag = 1
```

does not automatically mean:

``` text
a sale was lost
```

## Why this is documented

The inventory analytics can identify stockout patterns, but causal
lost-sales conclusions require stronger data modeling.

This limitation is explicitly preserved rather than hidden.

------------------------------------------------------------------------

# 32. What Was Deliberately Not Built

The project intentionally stops at the defined feature scope.

The following are not currently implemented as production capabilities:

-   enterprise authentication
-   role-based authorization
-   durable conversation database
-   multi-user tenant isolation
-   production deployment
-   distributed job execution
-   enterprise observability
-   formal LLM evaluation benchmark
-   production load testing
-   advanced model routing

These belong to future hardening or productionization work.

------------------------------------------------------------------------

# 33. FDE Perspective

The architectural decisions demonstrate several important Forward
Deployed Engineer principles.

## 33.1 Protect the source of truth

Do not allow the LLM to become the database.

``` text
Business data
     ↓
Deterministic system
     ↓
Evidence
     ↓
LLM explanation
```

## 33.2 Give AI bounded capabilities

Tools are explicit interfaces.

``` text
LLM
 ↓
Approved capability
```

rather than:

``` text
LLM
 ↓
Unlimited system access
```

## 33.3 Separate business logic from infrastructure

Analytics should describe business computation.

Repositories should describe data access.

The database should not leak into the agent layer.

## 33.4 Make workflows inspectable

Investigation planning, hypotheses, evidence, and synthesis are
separated so that an engineer can understand what happened.

## 33.5 Design for failure

Tool limits, streaming errors, validation, configuration checks, and
bounded challenge synthesis are all part of the application design.

------------------------------------------------------------------------

# 34. Decision-Making Mental Model

When adding or changing a feature, ask:

``` text
1. Who owns this responsibility?
2. Is the operation deterministic?
3. Does the LLM actually need to perform it?
4. Can the capability be exposed as a bounded tool?
5. Where should database access happen?
6. How will the behavior be tested?
7. What happens when it fails?
8. Does the change weaken an existing boundary?
```

A good implementation should make these answers obvious.

------------------------------------------------------------------------

# 35. Final Architecture Principle

The most important architectural decision in Nexa is the separation
between:

``` text
Interpretation
```

and:

``` text
Truth
```

The model interprets the user's intent.

The application retrieves and computes the evidence.

The model explains that evidence.

Therefore:

``` text
                LLM
                 │
        Interpretation
                 │
                 ▼
        Approved Tools
                 │
                 ▼
          Deterministic
           Analytics
                 │
                 ▼
          Repositories
                 │
                 ▼
            Database
                 │
                 ▼
             Evidence
                 │
                 ▼
                LLM
                 │
            Explanation
```

This separation is the foundation on which the rest of the Nexa
architecture is built.
