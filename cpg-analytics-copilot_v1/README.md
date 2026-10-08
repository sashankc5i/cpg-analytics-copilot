# Nexa Analytics Copilot

Nexa Analytics Copilot is an enterprise-style conversational analytics
application for a fictional CPG company, **Nexa Consumer Products**.

It allows business users to ask questions about sales, products,
regions, customers, promotions, and inventory using natural language.
The system combines an LLM-powered agent with deterministic analytics
and controlled data access so that the LLM interprets business questions
without becoming the source of truth for numerical results.

------------------------------------------------------------------------

## 1. What Nexa Does

Nexa is designed around a simple principle:

> **The LLM interprets the business question; deterministic analytics
> and the database remain the source of truth.**

A user can ask questions such as:

-   What is our total revenue?
-   Which region performs best?
-   What are our top products?
-   Show me monthly revenue.
-   Why is revenue changing?
-   What is driving our sales performance?
-   Challenge my conclusion.

The application can return natural-language explanations, structured
analytical results, and visualizations where appropriate.

------------------------------------------------------------------------

## 2. Core Capabilities

### Conversational Analytics

The Copilot can answer business questions using approved analytics tools
backed by the Nexa CPG dataset.

### Investigation Planning

Investigation mode converts a broad business question into a structured
investigation plan.

The planner can consider areas including:

-   Revenue trends
-   Regional performance
-   Product performance
-   Category performance
-   Customer segments
-   Promotion impact
-   Inventory stockouts

### Evidence Collection and Synthesis

Investigation workflows collect deterministic evidence from approved
analytics functions and use that evidence to produce a business-oriented
synthesis.

### Challenge My Conclusion

After an investigation produces a conclusion, Nexa can challenge it
using the existing investigation evidence.

The challenge review considers:

-   Supporting evidence
-   Contradicting or limiting evidence
-   Missing evidence
-   Alternative explanations
-   A final evidence-based bottom line

### Anomaly Detection

The anomaly engine compares monthly revenue against a rolling
three-month historical baseline.

Current thresholds:

    Deviation Classification
  ----------- ----------------
       \< 10% Normal
      10--20% Low
      20--30% Medium
      \>= 30% High

The current synthetic dataset does not produce a non-normal revenue
anomaly under this rule.

### Conversation Management

The application supports:

-   Multiple conversations
-   Conversation history
-   Shared conversation identity across Copilot, Investigation, and
    Challenge
-   Automatic conversation titles based on the first user question
-   Rename
-   Archive
-   Restore
-   Delete
-   Archived conversation browsing

------------------------------------------------------------------------

## 3. Architecture

``` text
React + TypeScript
        |
        | REST / streaming
        v
FastAPI
        |
        v
Analytics Agent
        |
        | approved tools
        v
Analytics Layer
        |
        v
Repository Layer
        |
        v
SQLite
```

For investigation workflows:

``` text
User Question
      |
      v
Investigation Planner
      |
      v
Hypotheses
      |
      v
Deterministic Evidence Collection
      |
      v
Evidence Synthesis
      |
      v
Business Conclusion
      |
      v
Challenge Review
```

### Data Access Boundary

The application intentionally separates reasoning from data access:

``` text
Agent
  |
  v
Tools
  |
  v
Analytics
  |
  v
Repositories
  |
  v
Database
```

The LLM does **not** execute SQL directly.

Agent tools do **not** execute SQL directly.

Repositories are the application layer responsible for database access.

This keeps analytical logic, data access, and LLM orchestration
independently testable.

------------------------------------------------------------------------

## 4. Technology Stack

  Layer             Technology
  ----------------- ----------------------------
  Frontend          React + TypeScript + Vite
  Backend           FastAPI + Python
  LLM               Groq
  Model             `openai/gpt-oss-20b`
  Database          SQLite
  Analytics         SQL + Python
  Visualization     Plotly / `react-plotly.js`
  API               REST + streaming responses
  Testing           Pytest
  Version Control   Git

------------------------------------------------------------------------

## 5. CPG Data Model

The synthetic Nexa dataset contains six primary tables:

``` text
customers
products
stores
sales
promotions
inventory
```

The generated dataset contains approximately:

-   10,000 customers
-   100 products
-   200 stores
-   300 promotions
-   100,000 inventory records
-   250,000 sales transactions

The dataset is deterministic and generated with a fixed random seed so
that development and testing can be reproduced.

------------------------------------------------------------------------

## 6. Repository Structure

``` text
cpg-analytics-copilot/
│
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── analytics/
│   │   ├── database/
│   │   │   └── repositories/
│   │   ├── models/
│   │   ├── config.py
│   │   ├── main.py
│   │   └── ...
│   │
│   ├── data/
│   │   ├── raw/
│   │   └── processed/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── ...
│   └── ...
│
├── docs/
│
├── .env.example
├── .gitignore
└── README.md
```

------------------------------------------------------------------------

## 7. Getting Started

### Prerequisites

Install:

-   Python 3.11+ recommended
-   Node.js and npm
-   A Groq API key

### Backend

From the repository root:

``` powershell
cd backend
```

Create and activate a virtual environment:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

``` powershell
pip install -r requirements.txt
```

Configure environment variables using `.env`.

Then start FastAPI:

``` powershell
uvicorn app.main:app --reload
```

The backend runs by default at:

``` text
http://127.0.0.1:8000
```

### Frontend

Open a second terminal:

``` powershell
cd frontend
npm install
npm run dev
```

The Vite development server normally runs at:

``` text
http://localhost:5173
```

------------------------------------------------------------------------

## 8. Environment Configuration

Create a `.env` file based on `.env.example`.

At minimum, the application requires the Groq API key.

Example:

``` env
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Do not commit real credentials to Git.

------------------------------------------------------------------------

## 9. Running the Application

Start the backend first:

``` powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Then start the frontend:

``` powershell
cd frontend
npm run dev
```

Open the frontend in a browser and use the Nexa Copilot workspace.

------------------------------------------------------------------------

## 10. Example User Flow

### Simple analytics

``` text
User:
What are our top products?

        ↓

Agent selects approved analytics tool

        ↓

Deterministic product analysis

        ↓

Groq interprets the result

        ↓

Nexa response + table/chart
```

### Investigation

``` text
User:
Why is revenue changing?

        ↓

Investigation Planner

        ↓

Hypotheses

        ↓

Evidence collection

        ↓

Revenue / region / product /
category / customer / promotion /
inventory analysis

        ↓

Evidence synthesis

        ↓

Business conclusion
```

### Challenge

``` text
Completed investigation
        ↓
Existing evidence
        ↓
Challenge reviewer
        ↓
Supporting evidence
Contradicting evidence
Missing evidence
Alternative explanations
        ↓
Challenge conclusion
```

------------------------------------------------------------------------

## 11. API Surface

The application exposes conversation, chat, investigation, and challenge
functionality through FastAPI.

Core conversation operations include:

``` text
POST   /api/conversations
GET    /api/conversations
GET    /api/conversations/{conversation_id}
PATCH  /api/conversations/{conversation_id}
POST   /api/conversations/{conversation_id}/archive
POST   /api/conversations/{conversation_id}/unarchive
DELETE /api/conversations/{conversation_id}
```

Chat and analytical workflows include the chat and streaming
investigation/challenge endpoints implemented by the backend.

Detailed request, response, and streaming contracts are documented
separately in `docs/api.md`.

------------------------------------------------------------------------

## 12. Testing

Backend tests:

``` powershell
cd backend
pytest -q
```

Frontend production build:

``` powershell
cd frontend
npm run build
```

The test suite covers areas including:

-   Analytics logic
-   Repository/data-access behavior
-   Agent behavior
-   Investigation workflow
-   Challenge workflow
-   Anomaly detection
-   Conversation management
-   Chat/conversation integration

------------------------------------------------------------------------

## 13. Important Design Principles

### 1. LLM is not the source of truth

Numerical and analytical results come from deterministic application
logic and the database.

### 2. Controlled tool access

The LLM can only use the analytics capabilities explicitly exposed
through the agent tool layer.

### 3. Repository boundary

SQL execution is isolated inside repositories instead of being
distributed across the application.

### 4. Deterministic analytics

Business calculations that need numerical correctness are implemented in
Python/SQL rather than delegated to free-form model reasoning.

### 5. Evidence-based investigation

Investigation conclusions are expected to be grounded in collected
evidence.

### 6. Causality control

The system should distinguish observed relationships from proven causal
explanations.

### 7. Bounded agent behavior

Tool-calling loops and challenge synthesis are bounded to prevent
uncontrolled execution.

------------------------------------------------------------------------

## 14. Current Limitations

This project is intentionally an FDE training and portfolio
implementation rather than a fully productionized enterprise deployment.

Known limitations include:

-   Conversation state is currently stored in memory.
-   Conversation history is therefore lost when the backend process is
    restarted.
-   The CPG dataset is synthetic.
-   SQLite is used as the analytical datastore for simplicity and
    portability.
-   The current frontend bundle can be optimized further.
-   The generated sales data does not currently model inventory
    stockouts as a constraint on sales generation.
-   The current implementation does not yet provide enterprise
    authentication, authorization, deployment infrastructure, or
    production-grade persistent conversation storage.

These are documented limitations rather than hidden assumptions.

------------------------------------------------------------------------

## 15. Project Status

### Feature implementation

-   [x] Investigation planning
-   [x] Evidence collection
-   [x] Evidence synthesis
-   [x] Challenge My Conclusion
-   [x] Revenue anomaly detection
-   [x] Conversation memory
-   [x] Shared conversation identity
-   [x] Conversation rename
-   [x] Archive / restore
-   [x] Delete
-   [x] Markdown table rendering
-   [x] Conversational frontend UI

The feature build is considered **frozen** at this point.

The next project phase is documentation and hardening rather than adding
new product functionality.

------------------------------------------------------------------------

## 16. Documentation

Detailed documentation is maintained under `docs/`:

``` text
docs/
├── architecture.md
├── data-model.md
├── agent-design.md
├── api.md
├── evaluation.md
├── testing.md
├── decisions.md
└── roadmap.md
```

These documents explain the architecture, data model, agent design, API
contracts, evaluation strategy, testing strategy, architectural
decisions, and known limitations/future hardening areas.

------------------------------------------------------------------------

## 17. Project Goal

Nexa is designed to demonstrate an important FDE pattern:

> **Build AI systems that connect models to reliable business
> capabilities rather than treating the model itself as the
> application.**

The project therefore emphasizes:

-   API engineering
-   AI orchestration
-   deterministic analytics
-   enterprise-style data access boundaries
-   investigation workflows
-   evidence-based reasoning
-   reliability controls
-   conversational product design
-   testing and evaluation
-   architectural decision-making
