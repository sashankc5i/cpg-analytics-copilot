# Agent Design

## 1. Purpose

The CPG Analytics Copilot uses an LLM-powered agent to translate natural-language business questions into deterministic analytical operations.

The agent is designed around a simple principle:

> **The LLM determines what to investigate; deterministic analytics determine what the data actually says.**

This prevents the language model from becoming the source of truth for business metrics.

---

# 2. Agent Architecture

The agent sits between the API layer and the analytics tool layer.

```text
                         User
                           │
                           ▼
                      FastAPI API
                           │
                           ▼
                   Analytics Agent
                           │
                           ▼
                     Groq LLM
                           │
                    Tool Selection
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
       Sales             Product         Inventory
       Tools              Tools            Tools
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                   Deterministic Data
                           │
                           ▼
                      Tool Results
                           │
                           ▼
                       Groq LLM
                           │
                    Result Synthesis
                           │
                           ▼
                    Business Answer
```

---

# 3. Agent Responsibilities

The agent performs the following responsibilities:

1. Understand the user's business question.
2. Determine whether analytics are required.
3. Select appropriate analytics tools.
4. Execute one or more tools.
5. Receive deterministic results.
6. Determine whether additional investigation is required.
7. Synthesize the available evidence.
8. Produce a natural-language business response.
9. Preserve conversation context for follow-up questions.

The agent does **not** directly calculate business metrics.

---

# 4. LLM Responsibilities

The Groq model is responsible for probabilistic reasoning and language understanding.

Its responsibilities include:

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
Natural Language Generation
```

For example:

```text
User:

"What is our total revenue?"
```

The model identifies that the question requires:

```text
get_overall_sales
```

The model does not calculate:

```text
SUM(sales_amount)
```

itself.

Instead, the analytics tool performs that calculation.

---

# 5. Deterministic Analytics Boundary

The system establishes a strict boundary between the LLM and business data.

```text
                  LLM
                   │
                   │ Tool Call
                   ▼
            Analytics Tool
                   │
                   ▼
              SQL / Python
                   │
                   ▼
                SQLite
                   │
                   ▼
            Deterministic Result
                   │
                   ▼
                  LLM
                   │
                   ▼
             Explanation
```

This architecture provides several advantages:

* business calculations remain deterministic
* results can be independently tested
* analytical logic is reusable
* hallucinated metrics are reduced
* debugging becomes easier
* tool usage is observable

---

# 6. Available Analytics Tools

The agent currently has eight analytical capabilities.

| Tool                               | Purpose                               |
| ---------------------------------- | ------------------------------------- |
| `get_overall_sales`                | Overall sales KPIs                    |
| `get_sales_by_region`              | Regional performance                  |
| `get_monthly_sales_trend`          | Monthly sales trend                   |
| `get_top_products`                 | Top products by revenue               |
| `get_sales_by_category`            | Category performance                  |
| `get_customer_segment_performance` | Customer segment performance          |
| `get_promotion_impact`             | Promotion vs non-promotion comparison |
| `get_stockout_rate`                | Regional stockout analysis            |

Each tool represents a controlled capability rather than allowing the LLM to execute arbitrary database operations.

---

# 7. Tool Selection

Tool selection is performed using the LLM's function-calling capability.

The model receives:

```text
System Prompt
+
Conversation History
+
User Question
+
Available Tool Definitions
```

The model then decides whether a tool should be called.

Conceptually:

```text
User Question
      │
      ▼
     Groq
      │
      ├── No tool required
      │       │
      │       ▼
      │    Answer
      │
      └── Tool required
              │
              ▼
          Tool Call
```

---

# 8. Simple Analytical Questions

Simple questions generally require one analytical tool.

## Example

```text
"What is our total revenue?"
```

Expected behavior:

```text
get_overall_sales
```

Execution:

```text
User
 │
 ▼
Groq
 │
 ▼
get_overall_sales
 │
 ▼
SQLite
 │
 ▼
Revenue
 │
 ▼
Groq
 │
 ▼
Answer
```

Another example:

```text
"Which region performs best?"
```

maps naturally to:

```text
get_sales_by_region
```

---

# 9. Diagnostic Questions

Some business questions require investigation rather than a single lookup.

Examples:

```text
Why is revenue changing?

What is driving the decline?

Why is a region underperforming?

What caused the sales drop?

What is hurting performance?
```

For these questions, the agent should build an evidence chain.

---

# 10. Diagnostic Investigation Pattern

For a revenue diagnosis, the recommended investigation is:

```text
                 Revenue Question
                        │
                        ▼
                Monthly Trend
                        │
                        ▼
                 Regional Data
                        │
                        ▼
                Product Data
                        │
                        ▼
                Category Data
                        │
                        ▼
               Promotion Data
                        │
                        ▼
                Inventory Data
                        │
                        ▼
                  Synthesis
```

Not every diagnostic question requires every tool.

The agent should use tools that are relevant to the question.

---

# 11. Diagnostic Reasoning Framework

The agent follows this conceptual process.

## Step 1 — Establish the observation

Determine whether the data actually shows:

* an increase
* a decrease
* stability
* or no meaningful change

Example:

```text
Revenue decreased from one month to another.
```

This should be based on the monthly sales tool.

---

## Step 2 — Identify where the change occurred

The agent can examine:

* region
* category
* product
* customer segment
* channel/store type where supported

Example:

```text
The largest revenue contribution came from the South region.
```

---

## Step 3 — Identify contributing products or categories

The agent can examine product and category performance.

Example:

```text
Several high-revenue products showed weaker performance.
```

---

## Step 4 — Examine promotions

The agent can compare:

```text
Promotion
vs.
No Promotion
```

This can identify differences in:

* transaction volume
* quantity
* revenue
* average transaction value

---

## Step 5 — Examine inventory

The agent can inspect stockout rates.

This helps determine whether periods of weak performance coincide with elevated stockout activity.

---

## Step 6 — Synthesize

The model combines the evidence into a business-oriented explanation.

---

# 12. Causality Control

The agent is explicitly instructed not to assume causality.

Consider:

```text
Revenue decreased.
Stockout rate increased.
```

This does not automatically prove:

```text
Stockouts caused the revenue decline.
```

The appropriate interpretation is:

```text
Revenue declined during a period where stockout
rates were elevated. This suggests a possible
relationship, but the available data does not
establish causation.
```

This distinction is important in business analytics because observational data frequently contains correlations without controlled causal evidence.

---

# 13. Conversation Context

The agent supports multi-turn conversations.

Conversation history is maintained by the session manager.

Conceptually:

```text
Conversation ID
      │
      ▼
Conversation History
      │
      ├── User Question
      ├── Assistant Answer
      ├── User Follow-up
      └── Assistant Answer
```

The history is supplied to the agent along with the new user question.

---

# 14. Follow-Up Questions

Consider:

```text
User:
Which region performs best?
```

The assistant might determine:

```text
South
```

The user can then ask:

```text
Why?
```

The second question is ambiguous in isolation.

However, with conversation history:

```text
Previous topic:
Regional performance

Current question:
Why?
```

the agent can infer that the user is asking about the previously discussed region.

This is why conversation history is passed into the agent.

---

# 15. Tool Execution Loop

The agent supports iterative tool execution.

Conceptually:

```text
User Question
      │
      ▼
     LLM
      │
      ▼
  Tool Call
      │
      ▼
 Tool Execution
      │
      ▼
 Tool Result
      │
      ▼
     LLM
      │
      ├── Need more evidence?
      │          │
      │          └── Yes
      │               │
      │               ▼
      │            Tool Call
      │
      └── No
           │
           ▼
       Final Answer
```

This enables multi-tool investigations.

---

# 16. Tool Iteration Limit

The agent has a configurable maximum number of tool-calling iterations.

Current configuration:

```text
MAX_TOOL_ITERATIONS = 8
```

This prevents uncontrolled loops.

For example, if the model repeatedly requests tools without reaching a final answer:

```text
Tool
 ↓
Tool
 ↓
Tool
 ↓
Tool
 ↓
...
```

the agent eventually terminates with a controlled runtime error.

This creates an operational safety boundary around the LLM.

---

# 17. Tool Argument Validation

The LLM does not have unlimited control over tool parameters.

For example:

```text
get_top_products(limit)
```

has a defined valid range:

```text
1 <= limit <= 50
```

Invalid examples:

```text
limit = -1
limit = 1000
limit = "100"
```

are rejected by the tool execution layer.

The architecture therefore has two validation boundaries:

```text
                User
                  │
                  ▼
            API Validation
                  │
                  ▼
                 LLM
                  │
                  ▼
           Tool Arguments
                  │
                  ▼
          Tool Validation
                  │
                  ▼
             Analytics
```

---

# 18. Error Handling

Tool failures are captured rather than silently ignored.

Conceptually:

```text
Tool Call
   │
   ▼
Execute Tool
   │
   ├── Success
   │     │
   │     ▼
   │   Result
   │
   └── Failure
         │
         ▼
     Error Result
```

The agent can then continue or return an appropriate error depending on the execution state.

---

# 19. Prompt Design

The system prompt establishes the agent's operating rules.

The prompt defines:

* business context
* data governance
* conversation behavior
* tool usage
* diagnostic reasoning
* causality restrictions
* answer structure

The most important instructions are:

```text
Never invent business metrics.

Never fabricate numbers.

SQLite is the source of truth.

Use analytics tools for business-data questions.

Do not assume correlation means causation.
```

---

# 20. Answer Strategy

The agent uses different response strategies depending on the question.

## Simple Question

Example:

```text
"What is our total revenue?"
```

Expected response style:

```text
Concise
+
Direct
+
Data-backed
```

---

## Diagnostic Question

Example:

```text
"Why is revenue changing?"
```

Expected structure:

```text
1. Executive finding

2. Supporting evidence

3. Main contributing dimensions

4. Possible explanations

5. Caveat / limitation
```

This allows the same agent to support both quick business questions and deeper investigation.

---

# 21. Grounding Strategy

Grounding is achieved through architecture rather than relying solely on prompt instructions.

The system uses:

```text
Natural Language
      │
      ▼
     LLM
      │
      ▼
Structured Tool
      │
      ▼
Deterministic Data
      │
      ▼
Tool Result
      │
      ▼
     LLM
      │
      ▼
Grounded Answer
```

This means the model receives actual business data before producing analytical conclusions.

---

# 22. Why the LLM Does Not Generate SQL Directly

The current architecture intentionally avoids giving the model unrestricted SQL access.

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

the system uses:

```text
User
 ↓
LLM
 ↓
Select Approved Tool
 ↓
Tool
 ↓
Controlled Query
 ↓
Database
```

This provides:

* stronger control
* predictable analytical behavior
* simpler testing
* reduced SQL injection surface
* easier auditing
* reusable analytical capabilities

A future system could introduce a controlled semantic SQL layer, but that would require additional validation and authorization controls.

---

# 23. Agent Observability

The application records information about:

* request ID
* conversation ID
* selected tools
* request lifecycle
* completion status
* runtime failures

This allows an FDE to investigate questions such as:

```text
Why did the agent choose this tool?

Which tools executed?

Did a tool fail?

How long did the request take?

Did the agent reach the iteration limit?
```

This is important because debugging an AI application requires visibility into both:

```text
Application behavior
```

and:

```text
Model behavior
```

---

# 24. Agent Evaluation

The agent is evaluated separately from deterministic analytics.

The evaluation framework examines:

### Tool Selection

Did the model select the expected analytics capability?

### Groundedness

Did the answer have supporting tool execution and results?

### Multi-turn Behavior

Did the agent use conversation context?

### Safety

Were invalid tool arguments rejected?

### Data Integrity

Did deterministic analytical results reconcile?

The evaluation architecture intentionally separates live LLM evaluation from the normal automated test suite.

---

# 25. Testing Strategy

The system uses two categories of testing.

## Deterministic Tests

Run through Pytest.

These cover:

* analytics
* data integrity
* tool execution
* tool safety
* API behavior
* conversation mechanics

These tests should remain fast and repeatable.

---

## Live LLM Evaluation

Live Groq calls are used when evaluating actual model behavior.

They are kept separate because LLM API calls introduce:

* token consumption
* rate limits
* latency
* external service dependency
* model variability

This separation prevents normal development tests from becoming dependent on an external model service.

---

# 26. Agent Mental Model

The simplest way to understand the agent is:

```text
                 ┌─────────────────┐
                 │      User       │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │       LLM       │
                 │                 │
                 │ "What does the  │
                 │  user need?"    │
                 └────────┬────────┘
                          │
                    Tool Selection
                          │
                          ▼
                 ┌─────────────────┐
                 │      Tools      │
                 │                 │
                 │ "What does the  │
                 │  data say?"     │
                 └────────┬────────┘
                          │
                    Deterministic
                       Results
                          │
                          ▼
                 ┌─────────────────┐
                 │       LLM       │
                 │                 │
                 │ "How should I   │
                 │  explain this?" │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Business Answer │
                 └─────────────────┘
```

The LLM therefore acts as:

```text
Interpreter
+
Orchestrator
+
Reasoner
+
Communicator
```

while the analytics layer acts as:

```text
Calculator
+
Data Access Layer
+
Business Logic
+
Source of Truth
```

---

# 27. FDE Perspective

This architecture demonstrates an important Forward Deployed Engineer pattern.

An FDE should not approach an enterprise AI problem as:

```text
"Where can I add an LLM?"
```

The better question is:

```text
"What part of the customer's workflow benefits
from probabilistic reasoning, and where must
the system remain deterministic?"
```

In this project:

```text
Business Question
       │
       ▼
Natural Language
       │
       ▼
LLM Reasoning
       │
       ▼
Enterprise Capability
       │
       ▼
Deterministic Data
       │
       ▼
Business Insight
```

The model is therefore integrated into an existing analytical architecture rather than replacing the underlying analytical system.

---

# 28. Future Agent Extensions

The current agent can be extended with additional capabilities such as:

* forecasting
* anomaly detection
* customer lifetime value analysis
* churn analysis
* price elasticity
* promotion optimization
* inventory forecasting
* semantic search
* business-document RAG
* external enterprise system integrations

Each new capability should follow the same pattern:

```text
New Business Capability
          │
          ▼
Deterministic / Controlled Implementation
          │
          ▼
Tool Definition
          │
          ▼
Agent Tool Selection
          │
          ▼
Grounded Business Response
```

This allows the agent to grow without turning the LLM into an uncontrolled execution layer.

---

# 29. Summary

The CPG Analytics Copilot agent is intentionally designed as a controlled orchestration layer.

Its core architecture is:

```text
User
 ↓
LLM
 ↓
Tool Selection
 ↓
Controlled Analytics
 ↓
Deterministic Results
 ↓
LLM Synthesis
 ↓
Business Answer
```

The most important design principle is:

> **The LLM decides what to investigate. The data and analytics layer decide what is true.**

This separation provides the foundation for a more reliable, testable, observable, and extensible enterprise AI application.
