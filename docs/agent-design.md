# Nexa Analytics Copilot --- Agent Design

## 1. Purpose

The agent layer is responsible for translating natural-language business
questions into controlled analytical actions and then converting
deterministic analytical evidence into useful business responses.

Nexa deliberately separates:

``` text
LLM reasoning
      from
data access
      from
analytical calculation
```

The core principle is:

> **The LLM is not the source of truth.**

The LLM can interpret intent, select approved tools, generate
investigation hypotheses, synthesize evidence, and challenge
conclusions. Numerical business results are produced by deterministic
analytics backed by the database.

------------------------------------------------------------------------

# 2. Agent Architecture

The normal conversational path is:

``` text
User
  │
  ▼
FastAPI
  │
  ▼
Analytics Agent
  │
  ▼
Groq
  │
  ├── Tool selection
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
Groq
  │
  ▼
Natural-language Response
```

The agent therefore acts as an orchestration layer rather than a
replacement for the analytics system.

------------------------------------------------------------------------

# 3. LLM Responsibilities

The LLM is responsible for tasks that benefit from language
understanding and flexible reasoning.

These include:

-   Understanding natural-language business questions
-   Interpreting conversational context
-   Selecting an appropriate approved tool
-   Supplying tool arguments
-   Interpreting structured analytical results
-   Producing natural-language explanations
-   Generating investigation hypotheses
-   Synthesizing investigation evidence
-   Challenging an existing investigation conclusion

The LLM is not responsible for:

-   Direct database access
-   Arbitrary SQL execution
-   Authoritative revenue calculations
-   Authoritative anomaly calculations
-   Replacing repository logic
-   Inventing unavailable evidence

------------------------------------------------------------------------

# 4. System Prompt Responsibilities

The agent receives a system prompt before processing the user question.

The prompt establishes behavioral constraints such as:

-   Data-governance expectations
-   Tool usage
-   Conversational context
-   Analytical grounding
-   Anomaly interpretation
-   Investigation behavior
-   Causality control
-   Response formatting

The prompt is therefore a behavioral contract between the application
and the model.

It does not replace application-level controls.

------------------------------------------------------------------------

# 5. Standard Analytics Agent

The primary agent is implemented through:

``` text
backend/app/agent/agent.py
```

The agent initializes the Groq client using application configuration.

The current configured model is:

``` text
openai/gpt-oss-20b
```

The Groq client is configured with retries disabled:

``` python
Groq(
    api_key=settings.groq_api_key,
    max_retries=0,
)
```

This keeps retry behavior explicit at the application level.

------------------------------------------------------------------------

# 6. Conversation Context

The agent receives conversation history when available.

Conceptually:

``` text
System Instructions
       │
       ▼
Conversation History
       │
       ▼
Current User Question
       │
       ▼
Groq
```

This allows follow-up questions to refer to previous analytical context.

For example:

``` text
User:
What are our total sales?

Assistant:
[revenue result]

User:
Break that down by region.
```

The second question can be interpreted using the existing conversation
context.

------------------------------------------------------------------------

# 7. Tool Definitions

The current analytics tool catalog contains:

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

These tools represent the approved analytical capabilities exposed to
the LLM.

The model does not receive a generic:

``` text
execute_sql(query)
```

tool.

That distinction is deliberate.

------------------------------------------------------------------------

# 8. Tool Selection

For each agent iteration, Groq receives:

-   System prompt
-   Conversation messages
-   Approved tool definitions
-   Current user request

The model can either:

``` text
Return a final answer
```

or:

``` text
Request one or more approved tools
```

The application then executes the requested tools and sends their
results back to the model.

Conceptually:

``` text
                    ┌──────────────┐
                    │     Groq     │
                    └──────┬───────┘
                           │
                    tool call / answer
                           │
              ┌────────────┴────────────┐
              │                         │
         Tool requested              No tool
              │                         │
              ▼                         ▼
      Execute approved tool       Final response
              │
              ▼
       Tool result
              │
              ▼
            Groq
```

------------------------------------------------------------------------

# 9. Bounded Tool Iterations

Agent execution is bounded by:

``` text
MAX_TOOL_ITERATIONS
```

This prevents an uncontrolled tool-calling loop.

The configured value is obtained through application settings rather
than being hard-coded inside the agent.

If the agent exceeds the allowed number of iterations, the application
raises an explicit runtime error.

This is a reliability boundary.

------------------------------------------------------------------------

# 10. Tool Argument Handling

Tool arguments are received from the model as JSON.

The application:

1.  Parses the JSON arguments.
2.  Executes the approved tool.
3.  Serializes the result.
4.  Returns the result to the model as a tool message.

Errors are converted into structured error results.

This prevents a malformed tool call from automatically terminating the
entire agent process.

------------------------------------------------------------------------

# 11. Tool Result Boundary

Tool results are treated as structured evidence.

Conceptually:

``` text
LLM
 │
 │ tool request
 ▼
Application
 │
 │ deterministic execution
 ▼
Tool result
 │
 ▼
LLM
```

The model can interpret the returned result, but the result itself
originates from the application's analytical layer.

------------------------------------------------------------------------

# 12. Analytics Layer Separation

The agent does not contain business calculations.

For example, the agent does not calculate:

``` text
total revenue = sum(...)
```

itself.

Instead:

``` text
Agent
  ↓
get_overall_sales
  ↓
Analytics
  ↓
Repository
  ↓
SQLite
```

This prevents model reasoning from becoming the numerical source of
truth.

------------------------------------------------------------------------

# 13. Repository Boundary

The analytics layer communicates with repositories rather than directly
executing database SQL.

``` text
Agent
  ↓
Tools
  ↓
Analytics
  ↓
Repositories
  ↓
SQLite
```

Repositories expose domain-specific operations such as retrieving sales
data or product performance.

This provides:

-   Data-access isolation
-   Testability
-   Controlled SQL
-   Clear ownership of database behavior
-   A migration boundary if the datastore changes later

------------------------------------------------------------------------

# 14. Investigation Agent Architecture

Investigation mode is a structured multi-stage workflow.

``` text
User Question
      │
      ▼
Investigation Planner
      │
      ▼
Investigation Plan
      │
      ▼
Hypothesis Generator
      │
      ▼
Hypotheses
      │
      ▼
Evidence Collector
      │
      ▼
Deterministic Analytics
      │
      ▼
Evidence Set
      │
      ▼
Synthesis
      │
      ▼
Conclusion
```

The investigation workflow is implemented in:

``` text
backend/app/agent/investigation.py
```

------------------------------------------------------------------------

# 15. Investigation Catalog

The investigation system uses an explicit catalog:

``` text
revenue_trend
regional_performance
product_performance
category_performance
customer_segments
promotion_impact
inventory_stockouts
```

Each investigation area maps to an approved analytics tool.

This creates a controlled planning boundary.

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

# 16. Investigation Planning

The planner receives the user's investigation question and produces a
structured plan.

The planner's output is validated by the application.

The application does not blindly trust arbitrary model-generated
investigation areas.

Only valid catalog entries are accepted.

This prevents the model from dynamically inventing unsupported evidence
domains.

------------------------------------------------------------------------

# 17. Hypothesis Generation

The hypothesis generator creates possible explanations that can be
investigated.

For example:

``` text
Question:
Why is revenue changing?

Possible investigation hypotheses:

H1:
Revenue change may be driven by product mix.

H2:
Revenue change could result from regional fluctuations.

H3:
Revenue change might be linked to customer-segment changes.

H4:
Revenue change may be influenced by promotions.

H5:
Revenue change could stem from inventory stockouts.
```

These are hypotheses, not established facts.

Each hypothesis is associated with evidence areas.

The purpose is to organize investigation, not to declare causality
before evidence is collected.

------------------------------------------------------------------------

# 18. Evidence Collection

The evidence collector maps investigation areas to deterministic tools.

For example:

``` text
revenue_trend
      ↓
get_monthly_sales_trend

regional_performance
      ↓
get_sales_by_region

product_performance
      ↓
get_top_products

category_performance
      ↓
get_sales_by_category

customer_segments
      ↓
get_customer_segment_performance

promotion_impact
      ↓
get_promotion_impact

inventory_stockouts
      ↓
get_stockout_rate
```

The evidence collector executes these tools and stores the resulting
structured evidence.

------------------------------------------------------------------------

# 19. Evidence as the Source for Synthesis

The synthesis stage receives collected evidence.

Conceptually:

``` text
Question
   │
   ▼
Plan
   │
   ▼
Hypotheses
   │
   ▼
Evidence
   │
   ▼
LLM Synthesis
```

The synthesis model is instructed to distinguish:

``` text
Observed evidence
        from
Interpretation
        from
Possible explanation
```

This is particularly important for business questions that contain
causal language.

------------------------------------------------------------------------

# 20. Causality Control

Nexa should not automatically convert correlation into causation.

For example:

``` text
Promotion activity increased
AND
Product sales increased
```

supports an observed relationship.

It does not by itself prove:

``` text
Promotion caused the entire sales increase.
```

The investigation prompts therefore encourage evidence-based language
and alternative explanations.

------------------------------------------------------------------------

# 21. Challenge My Conclusion

Challenge mode is deliberately different from the original
investigation.

It starts from:

``` text
Completed Investigation
        │
        ├── Original conclusion
        └── Existing evidence
```

and sends that context to a direct challenge reviewer.

Architecture:

``` text
Completed Investigation
        │
        ▼
Challenge Reviewer
        │
        ▼
One bounded Groq synthesis call
        │
        ▼
Challenge Report
```

The challenge report considers:

-   Supporting evidence
-   Contradicting or limiting evidence
-   Missing evidence
-   Alternative explanations
-   Bottom line

------------------------------------------------------------------------

# 22. Why Challenge Reuses Existing Evidence

The challenge workflow does not launch another complete investigation.

This avoids:

-   Duplicate evidence collection
-   Unnecessary tool calls
-   Re-running the planner
-   Re-generating the same hypotheses
-   Increasing latency without a clear benefit

Instead, Challenge acts as an adversarial review of the investigation
that already happened.

This gives the feature a clear responsibility:

> **Stress-test the existing conclusion rather than produce a second
> unrelated analysis.**

------------------------------------------------------------------------

# 23. Challenge Output Controls

Challenge synthesis is bounded by:

``` text
MAX_CHALLENGE_SYNTHESIS_TOKENS = 900
```

Evidence supplied to the challenge context is also bounded.

The implementation limits:

-   Evidence rows per investigation
-   Evidence digest size
-   Maximum synthesis output

The challenge uses:

``` text
temperature = 0
```

and disables additional model reasoning output.

These controls help keep the challenge workflow predictable and compact.

------------------------------------------------------------------------

# 24. Anomaly Detection

Revenue anomaly detection is deterministic and implemented outside the
LLM.

The anomaly engine:

``` text
Monthly revenue
      ↓
Previous 3 months
      ↓
Historical mean
      ↓
Current month deviation
      ↓
Classification
```

Constants include:

``` text
MIN_HISTORY_MONTHS = 3

LOW_ANOMALY_THRESHOLD = 10%

MEDIUM_ANOMALY_THRESHOLD = 20%

HIGH_ANOMALY_THRESHOLD = 30%
```

The current synthetic revenue series does not produce non-normal
anomalies under these thresholds.

This means the model does not decide whether a number is anomalous.

The deterministic analytics engine does.

------------------------------------------------------------------------

# 25. Anomaly → Investigation Relationship

Anomaly detection can be used as an analytical signal.

The conceptual relationship is:

``` text
Anomaly detected
       │
       ▼
Potential investigation trigger
       │
       ▼
Investigate contributing dimensions
```

However, an anomaly is not automatically treated as a causal
explanation.

It is a signal that warrants further investigation.

------------------------------------------------------------------------

# 26. Conversation Memory

Conversation memory is separated into two related concepts.

### Conversation memory

Managed by:

``` text
ConversationManager
```

It stores:

-   Conversation ID
-   Title
-   Created timestamp
-   Updated timestamp
-   Archive state
-   Message history

### Investigation memory

Managed by:

``` text
InvestigationSessionManager
```

It stores:

-   Investigation history
-   Latest plan
-   Latest evidence
-   Latest answer

The two systems share the same conversation identity at the
API/application level.

------------------------------------------------------------------------

# 27. Shared Conversation Identity

Copilot, Investigation, and Challenge operate within the same
conversation context.

``` text
                  conversation_id
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       Copilot    Investigation    Challenge
```

This allows a user to move from:

``` text
Question
  ↓
Follow-up
  ↓
Investigation
  ↓
Conclusion
  ↓
Challenge
```

without creating separate unrelated conversations.

------------------------------------------------------------------------

# 28. Agent Error Handling

The agent handles tool execution errors by creating structured error
results.

Conceptually:

``` text
Tool request
     │
     ▼
Execution
     │
 ┌───┴────┐
 │        │
Success   Error
 │        │
 ▼        ▼
Result   Error object
 │        │
 └───┬────┘
     ▼
    Groq
```

This provides the model with explicit information about tool failures
rather than silently hiding them.

------------------------------------------------------------------------

# 29. Security Boundaries

The agent architecture deliberately avoids unrestricted model access.

The LLM cannot directly:

-   Execute arbitrary SQL
-   Open a database connection
-   Modify database schema
-   Choose arbitrary tables outside the approved tool layer
-   Retrieve unlimited result sets

The model is therefore operating inside a capability boundary defined by
the application.

------------------------------------------------------------------------

# 30. Reliability Boundaries

The current implementation includes several controls.

### Bounded agent iterations

Prevents indefinite tool-calling loops.

### Bounded product results

Top-product operations enforce a maximum result limit.

### Bounded challenge synthesis

Challenge evidence and output are size-limited.

### Deterministic calculations

Important numerical calculations are kept outside model reasoning.

### Structured validation

Investigation plans and hypotheses are validated before downstream
execution.

------------------------------------------------------------------------

# 31. Agent Design Mental Model

The easiest way to understand Nexa's agent architecture is:

``` text
              LLM
               │
       "What does the user want?"
               │
               ▼
          Tool Selection
               │
               ▼
       "What evidence do we need?"
               │
               ▼
       Deterministic Analytics
               │
               ▼
       "What does the evidence say?"
               │
               ▼
          LLM Synthesis
               │
               ▼
        Business Response
```

For investigation:

``` text
Question
   ↓
Plan
   ↓
Hypotheses
   ↓
Evidence
   ↓
Synthesis
   ↓
Challenge
```

The important architectural boundary is that the model controls
**interpretation and orchestration**, while the application controls
**data access and deterministic computation**.

------------------------------------------------------------------------

# 32. Agent Design Summary

Nexa's agent architecture demonstrates a controlled AI-to-data
integration pattern:

``` text
Natural Language
       ↓
LLM
       ↓
Approved Capabilities
       ↓
Deterministic Analytics
       ↓
Repositories
       ↓
Database
       ↓
Evidence
       ↓
LLM
       ↓
Natural Language
```

This design provides a practical balance between the flexibility of an
LLM and the reliability required for business analytics.

The model is useful because it understands language and can reason over
evidence.

The application remains authoritative because it controls:

-   Tools
-   Data access
-   Business calculations
-   Evidence generation
-   Validation
-   Execution limits
-   Conversation state
