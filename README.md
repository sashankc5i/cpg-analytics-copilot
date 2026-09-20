# CPG Analytics Copilot

An enterprise-style conversational analytics application for a fictional Consumer Packaged Goods (CPG) company, built to demonstrate **Forward Deployed Engineer (FDE) patterns for AI-powered data applications**.

The application allows business users to ask natural-language questions about sales, products, customers, promotions, inventory, and regional performance.

Instead of allowing the LLM to directly query the database, the system uses a controlled architecture where:

> **The LLM understands the business question and selects analytics tools. Deterministic SQL and Python analytics remain the source of truth.**

---

# 1. Project Overview

The CPG Analytics Copilot simulates an enterprise analytics assistant for **Nexa Consumer Products**.

A business user can ask questions such as:

```text
What is our total revenue?
```

```text
Which region performs best?
```

```text
What are our top 10 products?
```

```text
Show me monthly revenue.
```

```text
How are our customer segments performing?
```

```text
Do promotions work?
```

```text
Are we having stockouts?
```

And more complex diagnostic questions:

```text
Why is revenue changing?
```

The system can investigate multiple analytical dimensions before generating a business-oriented explanation.

---

# 2. Core Design Principle

The most important architectural decision in this project is:

```text
                    USER
                      │
                      ▼
              Natural Language
                      │
                      ▼
                  LLM Agent
                      │
                Tool Selection
                      │
                      ▼
              Approved Tools
                      │
                      ▼
          Deterministic Analytics
                      │
                      ▼
                   SQLite
                      │
                      ▼
             Structured Results
                      │
                      ▼
                LLM Synthesis
                      │
                      ▼
              Business Response
```

The LLM is **not the source of truth**.

Business metrics come from deterministic analytics functions backed by SQLite.

This separation improves:

* reliability
* explainability
* testability
* security
* maintainability

---

# 3. Why This Project Exists

This project was built as an FDE-style engineering exercise rather than simply as a chatbot demo.

The goal is to demonstrate the ability to move from:

```text
Business Problem
      ↓
Data Model
      ↓
Analytics
      ↓
AI Agent
      ↓
Application API
      ↓
Frontend
      ↓
Evaluation
      ↓
Production Thinking
```

An FDE working on an enterprise AI deployment must understand all of these layers.

The project therefore intentionally includes:

* business-oriented analytics
* deterministic data processing
* LLM tool calling
* multi-turn conversations
* multi-tool reasoning
* structured API responses
* visual analytics
* validation
* logging
* health checks
* readiness checks
* evaluation
* tool safety
* production architecture considerations

---

# 4. Business Context

The fictional company is:

**Nexa Consumer Products**

The business operates across:

### Product Categories

* Personal Care
* Home Care
* Food & Beverages

### Regions

* South
* West
* North
* East

### Channels / Store Types

* Supermarket
* Convenience
* E-commerce
* Distributor

### Customer Segments

* Premium
* Standard
* Value

---

# 5. Questions the Copilot Can Answer

## Sales

```text
What is our total revenue?
```

Returns:

* transactions
* units sold
* revenue
* average transaction value

---

## Regional Performance

```text
Which region performs best?
```

Analyzes revenue and units by region.

---

## Products

```text
What are our top 10 products?
```

Returns product-level performance ranked by revenue.

---

## Trends

```text
Show me monthly revenue.
```

Returns monthly:

* transactions
* units
* revenue

and can generate a line chart.

---

## Categories

```text
Which category generates the most revenue?
```

Analyzes category-level performance.

---

## Customers

```text
How are our customer segments performing?
```

Analyzes:

* transactions
* customers
* units
* revenue
* average transaction value

by customer segment.

---

## Promotions

```text
Do promotions work?
```

Compares promotional and non-promotional transactions.

The response is descriptive rather than causal.

---

## Inventory

```text
Are we having stockouts?
```

Analyzes stockout rates by region.

---

## Diagnostic Questions

The system also supports questions such as:

```text
Why is revenue changing?
```

The agent can investigate multiple dimensions:

```text
Monthly Trend
      +
Regional Performance
      +
Product Performance
      +
Category Performance
      +
Promotion Impact
      +
Inventory Conditions
```

The final response distinguishes between:

```text
Observed Fact
      vs.
Possible Explanation
      vs.
Unsupported Assumption
```

---

# 6. Architecture

## High-Level Architecture

```text
┌───────────────────────────────┐
│        React Frontend         │
│                               │
│ Chat UI + Plotly Charts       │
└───────────────┬───────────────┘
                │
                │ REST / JSON
                ▼
┌───────────────────────────────┐
│          FastAPI              │
│                               │
│ Validation                    │
│ Sessions                      │
│ Request IDs                   │
│ Error Handling                │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       Analytics Agent         │
│                               │
│ Groq LLM                      │
│ Prompt                        │
│ Tool Selection                │
│ Multi-turn Reasoning          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│      Analytics Tool Layer     │
│                               │
│ Sales                         │
│ Products                      │
│ Customers                     │
│ Promotions                    │
│ Inventory                     │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│            SQLite             │
│                               │
│ Customers                     │
│ Products                      │
│ Stores                        │
│ Sales                         │
│ Promotions                    │
│ Inventory                     │
└───────────────────────────────┘
```

---

# 7. Technology Stack

| Layer          | Technology           |
| -------------- | -------------------- |
| Frontend       | React + TypeScript   |
| Build Tool     | Vite                 |
| Backend        | FastAPI              |
| Language       | Python               |
| LLM            | Groq                 |
| Model          | `openai/gpt-oss-20b` |
| Database       | SQLite               |
| Analytics      | SQL + Python         |
| Visualization  | Plotly               |
| HTTP Client    | Axios                |
| Testing        | Pytest               |
| API Validation | Pydantic             |
| Configuration  | Pydantic Settings    |
| Logging        | Python Logging       |

---

# 8. Project Structure

```text
cpg-analytics-copilot/
│
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── agent.py
│   │   │   ├── prompts.py
│   │   │   ├── session.py
│   │   │   └── tools.py
│   │   │
│   │   ├── analytics/
│   │   │   ├── customers.py
│   │   │   ├── inventory.py
│   │   │   ├── products.py
│   │   │   ├── promotions.py
│   │   │   ├── sales.py
│   │   │   └── visualization.py
│   │   │
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── generate_data.py
│   │   │   ├── init_db.py
│   │   │   └── schema.sql
│   │   │
│   │   ├── models/
│   │   │   └── chat.py
│   │   │
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── main.py
│   │   └── middleware.py
│   │
│   ├── data/
│   │   ├── raw/
│   │   └── processed/
│   │
│   ├── tests/
│   │   ├── evaluation_cases.py
│   │   ├── test_agent_evaluation.py
│   │   ├── test_conversation_evaluation.py
│   │   ├── test_data_integrity.py
│   │   └── test_tool_safety.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChartRenderer.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── LoadingIndicator.tsx
│   │   │   └── Message.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts
│   │   │
│   │   ├── types/
│   │   │   └── chat.ts
│   │   │
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   │
│   └── package.json
│
├── docs/
│   ├── architecture.md
│   ├── agent-design.md
│   ├── data-model.md
│   ├── api.md
│   └── evaluation.md
│
├── .env.example
├── .gitignore
└── README.md
```

---

# 9. Data Model

The database contains six primary tables:

```text
customers
products
stores
sales
promotions
inventory
```

The central relationship is:

```text
Customers ─────┐
               │
Products ──────┼──► Sales ◄── Stores
               │
               │
Promotions ────┘
               
Inventory ─────────► Products + Stores
```

The `sales` table is the primary transactional fact table.

---

# 10. Synthetic Dataset

The project uses reproducible synthetic data.

Approximate dataset size:

| Entity     | Records |
| ---------- | ------: |
| Customers  |  10,000 |
| Products   |     100 |
| Stores     |     200 |
| Promotions |     300 |
| Inventory  | 100,000 |
| Sales      | 250,000 |

The generator uses:

```python
random.seed(42)
```

so the dataset can be reproduced consistently.

---

# 11. Analytics Layer

The analytics layer contains deterministic business functions.

Current capabilities include:

```text
get_overall_sales()
get_sales_by_region()
get_monthly_sales_trend()
get_top_products()
get_sales_by_category()
get_customer_segment_performance()
get_promotion_impact()
get_stockout_rate()
```

Each function owns its own SQL logic.

For example:

```text
User Question
     ↓
Agent
     ↓
get_sales_by_region()
     ↓
SQL
     ↓
SQLite
     ↓
Regional Results
```

The LLM never needs to construct arbitrary SQL.

---

# 12. Agent Architecture

The agent is built around Groq tool calling.

The agent receives:

```text
System Prompt
+
Conversation History
+
User Question
+
Available Tools
```

The model determines whether a tool is required.

If a tool is selected:

```text
LLM
 ↓
Tool Call
 ↓
Argument Validation
 ↓
Deterministic Function
 ↓
Tool Result
 ↓
LLM
```

The process can repeat for multi-tool investigations.

---

# 13. Tool Calling

Available tools are explicitly registered.

Example:

```text
get_overall_sales
get_sales_by_region
get_monthly_sales_trend
get_top_products
get_sales_by_category
get_customer_segment_performance
get_promotion_impact
get_stockout_rate
```

The tool layer validates requests before execution.

For example, `get_top_products` enforces:

```text
1 ≤ limit ≤ 50
```

Invalid arguments are rejected.

---

# 14. Multi-Tool Reasoning

Simple questions may require one tool.

Example:

```text
"What is our revenue?"
```

```text
get_overall_sales
```

Diagnostic questions may require multiple tools.

Example:

```text
"Why is revenue changing?"
```

Potential workflow:

```text
Monthly Trend
      ↓
Regional Performance
      ↓
Product Performance
      ↓
Category Performance
      ↓
Promotion Impact
      ↓
Inventory
      ↓
Evidence Synthesis
```

The agent is instructed not to call irrelevant tools simply to increase the number of tool calls.

---

# 15. Conversational Context

The system supports multi-turn conversations through `conversation_id`.

Example:

```text
User:
Which region performs best?

Assistant:
South.

User:
Why?
```

The second question is sent with the same conversation ID.

The backend retrieves the previous history and provides it to the agent.

Current conversation state is held in memory.

---

# 16. Structured API Response

The `/api/chat` endpoint returns structured data:

```json
{
  "answer": "...",
  "tools_used": [],
  "tool_results": [],
  "visualization": null,
  "conversation_id": "..."
}
```

This allows the frontend to separately render:

* natural-language answer
* charts
* future evidence/tool information

The frontend does not need to parse charts out of natural language.

---

# 17. Visualization

The backend creates a visualization configuration.

Example:

```json
{
  "type": "bar",
  "title": "Revenue by Region",
  "x": ["South", "West", "North", "East"],
  "y": [5000000, 4200000, 3500000, 2800000]
}
```

React uses Plotly to render the actual chart.

Supported visualization patterns include:

```text
Monthly Revenue
    → Line Chart

Revenue by Region
    → Bar Chart

Top Products
    → Bar Chart

Revenue by Category
    → Bar Chart
```

Architecture:

```text
Backend
  ↓
Chart Configuration
  ↓
REST Response
  ↓
React
  ↓
Plotly
```

---

# 18. REST API

## Health

```http
GET /health
```

Example:

```json
{
  "status": "healthy",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

---

## Readiness

```http
GET /readiness
```

Checks whether required configuration is available.

---

## Chat

```http
POST /api/chat
```

Request:

```json
{
  "message": "Which region performs best?",
  "conversation_id": "demo-session"
}
```

---

# 19. Request Validation

The API validates incoming requests through Pydantic.

Current limits:

```text
message:
1–4000 characters

conversation_id:
1–100 characters
```

This prevents malformed or excessively large requests from reaching the agent.

---

# 20. Error Handling

The API distinguishes between:

```text
Validation Errors
Runtime Errors
Unexpected Errors
Readiness Failures
```

Typical HTTP statuses:

| Status | Meaning                    |
| -----: | -------------------------- |
|    200 | Successful request         |
|    422 | Validation failure         |
|    500 | Internal application error |
|    503 | Service not ready          |

Unexpected errors are logged while the client receives a controlled response.

---

# 21. Request Tracing

Every request receives a unique request ID.

Example:

```text
request_started
      ↓
chat_request
      ↓
chat_completed
      ↓
request_completed
```

The API also returns:

```http
X-Request-ID
```

This makes it easier to trace a request through application logs.

---

# 22. Configuration

Configuration is environment-driven.

Example `.env`:

```env
GROQ_API_KEY=your_api_key
GROQ_MODEL=openai/gpt-oss-20b
MAX_TOOL_ITERATIONS=8
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
APP_NAME=CPG Analytics Copilot
APP_VERSION=0.1.0
```

The repository contains:

```text
.env.example
```

but the real `.env` should never be committed.

---

# 23. Local Setup

## Prerequisites

Install:

* Python 3.10+
* Node.js
* npm
* Git
* Groq API key

---

# 24. Clone the Repository

```bash
git clone <your-repository-url>
cd cpg-analytics-copilot
```

---

# 25. Backend Setup

Move into the backend:

```bash
cd backend
```

Create a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 26. Environment Configuration

Create your environment file from the template.

From the project root:

```bash
copy .env.example backend\.env
```

On macOS/Linux:

```bash
cp .env.example backend/.env
```

Then replace:

```env
GROQ_API_KEY=your_groq_api_key_here
```

with your actual Groq API key.

Do not commit the real `.env` file.

---

# 27. Initialize the Database

From:

```text
backend/
```

run the database initialization process used by the project.

The database setup creates the SQLite schema and synthetic dataset.

The resulting database should contain:

```text
customers
products
stores
sales
promotions
inventory
```

---

# 28. Run the Backend

From `backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend should become available at:

```text
http://127.0.0.1:8000
```

---

# 29. Verify Backend Health

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "CPG Analytics Copilot",
  "version": "0.1.0"
}
```

Then verify readiness:

```text
http://127.0.0.1:8000/readiness
```

---

# 30. Run the Frontend

Open a second terminal.

Move into:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The Vite development server should expose the frontend at approximately:

```text
http://localhost:5173
```

---

# 31. End-to-End Flow

Once both services are running:

```text
Browser
   ↓
React
   ↓
POST /api/chat
   ↓
FastAPI
   ↓
Analytics Agent
   ↓
Groq
   ↓
Analytics Tool
   ↓
SQLite
   ↓
Tool Result
   ↓
LLM Synthesis
   ↓
Structured Response
   ↓
React
   ↓
Answer + Chart
```

---

# 32. Example Questions for Testing

Start with simple questions:

```text
What is our total revenue?
```

```text
Which region performs best?
```

```text
What are our top 10 products?
```

Then test visualization:

```text
Show me monthly revenue.
```

```text
Show revenue by region.
```

Then test conversational context:

```text
Which region performs best?
```

followed by:

```text
Why?
```

Finally test diagnostic reasoning:

```text
Why is revenue changing?
```

---

# 33. Running Tests

From the backend directory:

```bash
pytest
```

The test suite covers multiple layers.

```text
Data Integrity
      +
Tool Contracts
      +
Tool Safety
      +
Conversation Evaluation
```

---

# 34. Data Integrity Tests

The project verifies that dimensional results reconcile with overall results.

For example:

```text
Σ Regional Revenue
=
Overall Revenue
```

and:

```text
Σ Regional Units
=
Overall Units
```

These checks help catch analytics regressions.

---

# 35. Tool Safety Tests

The system validates:

```text
Unknown tools
Invalid limits
Excessive limits
Invalid argument types
Valid arguments
```

This is important because LLM-generated tool parameters should be treated as untrusted input.

---

# 36. LLM Evaluation

The project also defines evaluation cases for model behavior.

Examples:

```text
EV001
What is our total revenue?

EV002
Which region performs best?

EV003
What are our top 10 products?

EV004
Show me monthly revenue?

EV005
How are our customer segments performing?

EV006
Do promotions work?

EV007
Are we having stockouts?

EV008
Why is revenue changing?
```

---

# 37. Deterministic vs LLM Evaluation

A major lesson from the project is that not every test should invoke the LLM.

The preferred model is:

```text
                Test Suite
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Deterministic Tests    Live LLM Tests
          │                   │
          ▼                   ▼
      Frequent             Controlled
       CI runs              Runs
```

Deterministic tests cover:

* data integrity
* tool contracts
* validation
* safety
* application logic

Live LLM tests cover:

* tool selection
* conversation interpretation
* reasoning
* groundedness
* answer quality

---

# 38. Rate-Limit Lesson

During Phase 7, repeated live Groq evaluations caused a:

```text
429 RateLimitError
```

This exposed an important engineering lesson.

A naive evaluation architecture can accidentally turn:

```text
16 evaluation cases
```

into:

```text
many LLM requests
```

and exceed token-per-minute limits.

The evaluation strategy was therefore redesigned to move as much testing as possible into deterministic tests.

This makes the test suite:

* faster
* cheaper
* more reliable
* CI-friendly
* less dependent on external API limits

---

# 39. Security Principles

The application follows several important boundaries.

### Secrets stay server-side

The Groq API key is never sent to React.

### LLM cannot directly execute arbitrary SQL

The model selects approved analytics tools.

### Tool arguments are validated

Tool inputs are checked before execution.

### API validates requests

Malformed requests are rejected before agent execution.

### Errors are controlled

Internal implementation details are not unnecessarily returned to clients.

---

# 40. Known Limitations

This project is intentionally designed as an FDE training application.

It is not yet a production deployment.

Current limitations include:

### 1. SQLite

SQLite is appropriate for local development but would normally be replaced by an enterprise database.

### 2. In-memory conversation state

Conversation history is lost when the backend process restarts.

### 3. Synthetic data

The dataset does not represent real business data.

### 4. Inventory modeling

The synthetic sales generator does not enforce inventory availability.

Therefore, stockout analysis should not be interpreted as proof of causal revenue impact.

### 5. Promotion analysis

Promotion analysis is descriptive.

It does not establish causal promotional effectiveness.

### 6. Limited analytics surface

Only the currently implemented business tools are available.

### 7. No authentication

The training application does not currently implement enterprise identity and access management.

### 8. No production deployment

The current project is designed for local development.

---

# 41. Future Production Architecture

A production version could evolve toward Azure.

A possible architecture:

```text
                         Users
                           │
                           ▼
                  React / Web Application
                           │
                           ▼
                 Azure Container Apps
                           │
                           ▼
                        FastAPI
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
           Agent       Analytics    Conversation
              │            │            │
              ▼            ▼            ▼
       Azure AI Foundry  Azure SQL    Persistent Store
              │
              ▼
        Approved Models
```

Additional enterprise services could include:

```text
Azure Blob Storage
Azure AI Search
Microsoft Entra ID
Azure Key Vault
Azure VNet
Private Endpoints
Azure Monitor
Application Insights
Microsoft Defender for Cloud
Azure Policy
Azure DevOps
```

These services would be introduced based on production requirements rather than added simply for architectural complexity.

---

# 42. Production Evolution

The current local architecture:

```text
SQLite
+
In-memory sessions
+
Local FastAPI
+
Local React
```

could evolve into:

```text
Azure SQL
+
Persistent Conversation Store
+
Container Apps
+
Enterprise Identity
+
Centralized Monitoring
+
Secure Networking
+
CI/CD
```

The important point is that the business-facing agent architecture can remain relatively stable while infrastructure evolves.

---

# 43. Why Tools Instead of Direct SQL?

One of the most important design choices in the project is avoiding unrestricted LLM-generated SQL.

Instead of:

```text
User
 ↓
LLM
 ↓
Generate SQL
 ↓
Database
```

the application uses:

```text
User
 ↓
LLM
 ↓
Approved Tool
 ↓
Controlled SQL
 ↓
Database
```

This provides stronger control over:

* data access
* query behavior
* validation
* performance
* security
* testing

It also creates a clean contract between the agent and analytics layer.

---

# 44. Why Structured Responses?

A purely textual response would make frontend behavior difficult to control.

For example:

```text
"The South region generated the most revenue..."
```

The frontend would have to infer whether a chart should be displayed.

Instead, the API returns:

```json
{
  "answer": "...",
  "visualization": {
    "type": "bar",
    "title": "Revenue by Region",
    "x": [],
    "y": []
  }
}
```

The frontend can therefore render the chart deterministically.

---

# 45. Why Multi-Tool Reasoning?

Simple analytics questions require one metric.

Diagnostic business questions are different.

For:

```text
Why is revenue changing?
```

a single metric is insufficient.

The system therefore investigates multiple dimensions:

```text
Trend
+
Region
+
Product
+
Category
+
Promotion
+
Inventory
```

This moves the application from:

```text
Question → Metric
```

toward:

```text
Question → Investigation → Evidence → Explanation
```

This is closer to how enterprise analytical workflows operate.

---

# 46. FDE Engineering Lessons

This project demonstrates several FDE principles.

## 1. Start with the business problem

Do not start with:

```text
"What LLM should I use?"
```

Start with:

```text
"What business problem are we solving?"
```

---

## 2. Build deterministic foundations first

The analytics layer should work before introducing the LLM.

```text
Data
 ↓
SQL
 ↓
Analytics
 ↓
Tests
 ↓
Agent
```

---

## 3. Treat the LLM as an orchestration layer

The model is valuable for:

* understanding natural language
* selecting tools
* interpreting results
* synthesizing explanations

It should not replace deterministic business logic.

---

## 4. Validate model-generated inputs

LLM tool arguments are still inputs.

Therefore:

```text
LLM output
     ↓
Validation
     ↓
Execution
```

---

## 5. Design for observability

Request IDs, logs, tool usage, and latency are essential when debugging AI applications.

---

## 6. Evaluate continuously

A successful demo does not prove production reliability.

Evaluation should evolve with the system.

---

## 7. Separate deterministic and probabilistic testing

This was one of the most important lessons from the project.

Not every test should call an LLM.

---

# 47. Documentation

Detailed documentation is available under:

```text
docs/
```

### Architecture

```text
docs/architecture.md
```

Explains the complete application architecture and production evolution.

### Agent Design

```text
docs/agent-design.md
```

Explains:

* tool calling
* agent reasoning
* multi-tool workflows
* conversation context
* grounding
* causality controls

### Data Model

```text
docs/data-model.md
```

Explains:

* tables
* relationships
* dimensions
* facts
* synthetic data
* indexing
* data limitations

### API

```text
docs/api.md
```

Explains:

* REST endpoints
* request/response schemas
* health
* readiness
* chat
* sessions
* error handling
* request tracing

### Evaluation

```text
docs/evaluation.md
```

Explains:

* test architecture
* evaluation cases
* tool safety
* groundedness
* diagnostic evaluation
* LLM evaluation
* rate-limit lessons

---

# 48. Project Development Phases

The project was developed progressively.

```text
Phase 1
Data + SQLite
       ↓
Phase 2
Analytics Engine
       ↓
Phase 3
Groq Tool Calling
       ↓
Phase 4
Agent + Conversation
       ↓
Phase 5
React UI + Visualization
       ↓
Phase 6
Enterprise Hardening
       ↓
Phase 7
Evaluation
       ↓
Phase 8
Documentation + GitHub Polish
```

This progression mirrors a practical FDE development workflow.

---

# 49. Final Architecture Mental Model

The entire application can be remembered as:

```text
                         BUSINESS USER
                              │
                              ▼
                       NATURAL LANGUAGE
                              │
                              ▼
                    ┌──────────────────┐
                    │   React + Vite   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     FastAPI      │
                    │                  │
                    │ Validation       │
                    │ Sessions         │
                    │ Observability    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Analytics Agent │
                    │                  │
                    │ Groq LLM         │
                    │ Prompt           │
                    │ Tool Selection   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Tool Boundary   │
                    │                  │
                    │ Sales            │
                    │ Products         │
                    │ Customers        │
                    │ Promotions       │
                    │ Inventory        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │      SQLite      │
                    │                  │
                    │ Source of Truth  │
                    └────────┬─────────┘
                             │
                             ▼
                    DETERMINISTIC RESULTS
                             │
                             ▼
                       LLM SYNTHESIS
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Structured Response  │
                  │                      │
                  │ Answer               │
                  │ Tool Results         │
                  │ Visualization        │
                  │ Conversation ID      │
                  └──────────┬───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ React + Plotly   │
                    └──────────────────┘
```

---

# 50. Final Project Positioning

The CPG Analytics Copilot is more than a chatbot.

It demonstrates an end-to-end approach to building an enterprise AI analytics application:

```text
Business Understanding
        +
Data Engineering
        +
Analytics Engineering
        +
LLM Integration
        +
Agent Design
        +
API Engineering
        +
Frontend Engineering
        +
Testing
        +
Observability
        +
Production Architecture
```

The key architectural principle remains:

> **Use AI for understanding and reasoning, but keep business truth deterministic, controlled, observable, and testable.**

---

# 51. Project Status

Current implementation status:

```text
Phase 1 — Data + SQLite                  ✅
Phase 2 — Analytics Engine               ✅
Phase 3 — Groq Tool Calling              ✅
Phase 4 — Agent + Conversation           ✅
Phase 5 — Frontend + Visualization       ✅
Phase 6 — Enterprise Hardening           ✅
Phase 7 — Evaluation                     ✅
Phase 8 — Documentation                  ✅
```

The project is therefore at a **complete training-project state**, with the remaining work being deployment and optional production extensions rather than unfinished core functionality.
