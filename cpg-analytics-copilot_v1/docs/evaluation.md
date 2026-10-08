# Evaluation Strategy

## 1. Purpose

The Nexa Consumer Products Analytics Copilot is evaluated as an
**enterprise analytical application**, not only as an LLM application.

A useful evaluation therefore has to answer several different questions:

1.  Does the system retrieve the correct data?
2.  Does it perform the analytical calculation correctly?
3.  Does the agent select appropriate tools?
4.  Does the final answer faithfully represent the evidence?
5.  Does the investigation workflow identify useful analytical
    dimensions?
6.  Does Challenge My Conclusion expose limitations or alternative
    explanations?
7.  Does the API and application behave reliably under expected failure
    conditions?

The core evaluation principle is:

> **LLM quality is only one part of system quality.**

The application deliberately separates deterministic analytics from LLM
interpretation so that these layers can be evaluated independently.

------------------------------------------------------------------------

# 2. Evaluation Philosophy

The system follows this model:

``` text
User Question
      ↓
Agent Interpretation
      ↓
Tool Selection
      ↓
Deterministic Analytics
      ↓
Evidence
      ↓
LLM Synthesis
      ↓
User Answer
```

Each stage has a different evaluation strategy.

  Layer               Primary evaluation
  ------------------- --------------------------------------------
  API                 Contract and integration tests
  Conversation        State and lifecycle tests
  Agent               Tool-selection and bounded-execution tests
  Tools               Argument validation and execution tests
  Analytics           Deterministic analytical tests
  Repository          Database/data-access tests
  Investigation       Workflow and evidence tests
  Challenge           Adversarial review tests
  Anomaly detection   Known-data analytical tests
  LLM synthesis       Groundedness and qualitative review
  Frontend            Build and integration validation

This prevents a good-looking natural-language answer from hiding an
incorrect analytical result.

------------------------------------------------------------------------

# 3. Evaluation Layers

## 3.1 Deterministic Layer

The deterministic layer includes:

-   SQLite queries
-   repository methods
-   analytics calculations
-   anomaly detection
-   visualization preparation
-   tool argument validation

These components should be tested with known inputs and expected
outputs.

For example:

``` text
Known sales data
      ↓
SQL aggregation
      ↓
Expected revenue
```

If the expected revenue is `100000`, the analytical function should
return `100000` within the expected numeric representation.

There should be no dependency on an LLM for this test.

------------------------------------------------------------------------

## 3.2 Agent Layer

The agent layer is evaluated separately.

Important questions include:

-   Did the model select the correct approved tool?
-   Were tool arguments valid?
-   Did the agent stop within the configured iteration limit?
-   Did the agent use conversation history correctly?
-   Did the model avoid inventing database values?
-   Did it use evidence returned by tools rather than unsupported
    assumptions?

The current implementation bounds tool execution through:

``` text
MAX_TOOL_ITERATIONS
```

The configured default is:

``` text
8
```

This creates a deterministic safety boundary around agent execution.

------------------------------------------------------------------------

## 3.3 Synthesis Layer

The final answer is evaluated against the evidence supplied to the
model.

The evaluation should focus on:

### Groundedness

Does the answer stay within the information contained in the tool
results?

### Numerical fidelity

Are reported values consistent with the deterministic results?

### Causality control

Does the answer distinguish:

``` text
Observed relationship
```

from:

``` text
Proven causal relationship
```

### Completeness

Does the response address the user's actual analytical question?

### Clarity

Can a business user understand the answer without reading the underlying
SQL?

------------------------------------------------------------------------

# 4. Test Pyramid

The project should use a test pyramid rather than relying primarily on
expensive end-to-end LLM calls.

``` text
                 /\
                /  \
               / E2E\
              /------\
             / Agent  \
            /----------\
           / Integration\
          /--------------\
         / Unit / Deterministic \
        /------------------------\
```

The largest number of tests should be deterministic and inexpensive.

LLM-powered tests should be fewer and targeted at orchestration and
synthesis behavior.

------------------------------------------------------------------------

# 5. Current Automated Test Coverage

The project currently contains tests covering:

-   conversation session behavior
-   conversation API behavior
-   chat/conversation integration
-   investigation memory
-   investigation workflow behavior
-   challenge behavior
-   anomaly detection
-   analytics behavior
-   repository/data-access behavior
-   agent/tool behavior

The latest full backend test run completed with:

``` text
76 passed, 2 deselected, 1 warning
```

The warning was an `anyio`/Starlette deprecation warning originating
from the installed dependency stack and was not treated as a project
test failure.

------------------------------------------------------------------------

# 6. Conversation Evaluation

Conversation state is a core part of the application because Copilot,
Investigation, and Challenge share the same conversation identity.

## Test objectives

Verify that:

-   a new conversation can be created
-   supplied conversation IDs are preserved
-   generated IDs are unique
-   conversation titles are stored
-   messages are appended correctly
-   conversation timestamps update
-   conversations can be renamed
-   conversations can be archived
-   archived conversations can be restored
-   conversations can be deleted
-   archived conversations are hidden from the default list
-   conversations remain isolated from one another

### Example scenario

``` text
Conversation A
    ├── User message A1
    └── Assistant answer A1

Conversation B
    ├── User message B1
    └── Assistant answer B1
```

Messages from A must never appear in B.

------------------------------------------------------------------------

# 7. Copilot Evaluation

A standard Copilot request should be evaluated as an end-to-end
analytical interaction.

## Example

Question:

``` text
What are the top 10 products by revenue?
```

Expected behavior:

``` text
User question
    ↓
Agent selects get_top_products
    ↓
Repository retrieves product-level results
    ↓
Analytics/tool layer returns structured data
    ↓
Agent synthesizes answer
    ↓
Visualization builder may create a bar chart
```

Evaluation checks:

-   correct tool selected
-   valid product limit
-   deterministic result returned
-   answer references returned products
-   visualization corresponds to returned data
-   no unsupported products are invented

------------------------------------------------------------------------

# 8. Tool-Selection Evaluation

Tool selection is an important agent quality metric.

The current approved analytics tools include:

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

A test matrix can map representative questions to expected tools.

  User question                                Expected analytical capability
  -------------------------------------------- --------------------------------
  "What were total sales?"                     Overall sales
  "Which region generated the most revenue?"   Regional sales
  "Show monthly revenue."                      Monthly trend
  "Which products sell the most?"              Top products
  "Which category performs best?"              Category performance
  "How do customer segments compare?"          Segment performance
  "Did promotions affect sales?"               Promotion impact
  "What is the stockout rate?"                 Stockout rate
  "Are there unusual revenue movements?"       Revenue anomalies

The evaluation should focus on whether the selected tool is appropriate,
not whether a particular natural-language wording is reproduced.

------------------------------------------------------------------------

# 9. Analytics Evaluation

Analytics functions should be evaluated independently from the LLM.

For example:

``` text
get_monthly_sales_trend()
```

should be tested using the underlying dataset and expected aggregation
logic.

Important checks include:

-   correct grouping
-   correct aggregation
-   correct ordering
-   correct filtering
-   correct handling of empty results
-   correct numeric values
-   correct date handling

This is one of the most important boundaries in the project because
analytical correctness should not depend on model behavior.

------------------------------------------------------------------------

# 10. Anomaly Detection Evaluation

The anomaly engine uses historical revenue to calculate deviations.

Current design:

``` text
Minimum history = 3 months
Expected revenue = mean(previous 3 months)
Deviation = current vs expected
```

Classification thresholds are:

    Deviation Classification
  ----------- ----------------
      `< 10%` Normal
     `10–20%` Low
     `20–30%` Medium
     `>= 30%` High

The current implementation skips the first three months because there is
insufficient history for the configured baseline.

Zero-baseline situations are also skipped.

## Example test

Given:

``` text
Month 1 = 100
Month 2 = 100
Month 3 = 100
Month 4 = 140
```

Expected baseline for Month 4:

``` text
(100 + 100 + 100) / 3 = 100
```

Deviation:

``` text
(140 - 100) / 100 × 100 = 40%
```

Expected classification:

``` text
High anomaly
```

This can be tested without Groq.

------------------------------------------------------------------------

# 11. Investigation Evaluation

Investigation Mode has multiple stages and therefore needs
stage-specific evaluation.

``` text
Question
   ↓
Planner
   ↓
Hypotheses
   ↓
Evidence Collection
   ↓
Synthesis
```

## Planner evaluation

Check whether the planner selects relevant investigation areas.

For example, a broad revenue-decline investigation may reasonably
select:

``` text
revenue_trend
regional_performance
product_performance
category_performance
customer_segments
promotion_impact
inventory_stockouts
```

The evaluation should not require an identical plan for every valid
wording.

Instead, assess whether the selected areas are relevant to the question.

------------------------------------------------------------------------

## Hypothesis evaluation

Hypotheses should be:

-   relevant to the question
-   analytically testable
-   distinguishable from one another
-   connected to available evidence

Bad hypothesis:

``` text
The company probably had management problems.
```

Better hypothesis:

``` text
The revenue decline may be concentrated in one region.
```

The second can be tested using available analytical tools.

------------------------------------------------------------------------

## Evidence evaluation

Evidence collection should be deterministic.

If the investigation plan includes:

``` text
regional_performance
```

the corresponding approved analytical tool should be executed.

The evidence should be traceable to the tool output.

------------------------------------------------------------------------

## Synthesis evaluation

The final investigation answer should:

-   distinguish evidence from hypotheses
-   summarize relevant evidence
-   avoid unsupported causal claims
-   identify uncertainty
-   answer the original question
-   remain understandable to a business user

------------------------------------------------------------------------

# 12. Challenge My Conclusion Evaluation

Challenge Mode is deliberately evaluated differently from ordinary
synthesis.

The purpose is not to produce another generic answer.

It should actively inspect the completed investigation for:

``` text
Supporting evidence
Contradicting / limiting evidence
Missing evidence
Alternative explanations
Bottom line
```

## Evaluation questions

A successful challenge should:

1.  Identify what evidence genuinely supports the conclusion.
2.  Identify evidence that weakens or limits the conclusion.
3.  Identify meaningful missing evidence.
4.  Provide plausible alternative explanations where appropriate.
5.  Avoid inventing contradictory data.
6.  Avoid presenting correlation as proven causation.

The current design intentionally reuses the completed investigation
evidence rather than launching another broad investigation.

------------------------------------------------------------------------

# 13. Causality Evaluation

Causality is a major evaluation dimension for an analytics copilot.

The system should distinguish statements such as:

``` text
Revenue fell in the West region.
```

from:

``` text
The West region caused the revenue decline.
```

The first is descriptive.

The second is causal.

The available analytical evidence may support the first without proving
the second.

Therefore, evaluation should penalize unsupported causal language.

Preferred wording:

``` text
Revenue decline was concentrated in the West region.
```

More cautious wording:

``` text
The West region is a plausible contributor to the decline, based on the observed regional pattern.
```

Unsupported wording:

``` text
The West region caused the decline.
```

unless the available evidence actually supports such a conclusion.

------------------------------------------------------------------------

# 14. Groundedness Evaluation

A useful groundedness test compares every material claim in the final
answer with the available evidence.

Example:

### Tool result

``` json
{
  "region": "West",
  "revenue_change_pct": -18.4
}
```

### Grounded answer

``` text
West revenue declined by 18.4%.
```

### Ungrounded answer

``` text
West revenue declined by 18.4% because two major distributors stopped ordering.
```

The second statement introduces information not present in the supplied
evidence.

The evaluation should therefore distinguish:

``` text
Evidence-supported claim
```

from:

``` text
Unsupported inference
```

------------------------------------------------------------------------

# 15. Numerical Accuracy Evaluation

Numbers are especially important in an analytics application.

Evaluation should verify:

-   totals
-   percentages
-   rankings
-   date ranges
-   revenue values
-   quantities
-   anomaly deviations
-   chart values

For example, if the tool returns:

``` text
Revenue = 34,054,689.30
```

the generated answer should not silently report:

``` text
Revenue = 43,054,689.30
```

Formatting differences are acceptable:

``` text
₹34.05M
```

if the underlying number is represented correctly.

------------------------------------------------------------------------

# 16. Visualization Evaluation

Charts are generated from structured analytical results.

Evaluation should verify:

1.  chart type matches the analytical result
2.  x-axis values are correct
3.  y-axis values are correct
4.  title describes the data
5.  chart does not introduce values absent from the tool result

For example:

``` text
Monthly trend → line chart
Top products → bar chart
```

The chart is a presentation layer over deterministic data, not an
independent source of truth.

------------------------------------------------------------------------

# 17. Streaming Evaluation

Investigation and Challenge use NDJSON streaming.

A streaming test should verify event order.

### Investigation

Expected sequence:

``` text
investigation_started
        ↓
plan
        ↓
hypotheses
        ↓
answer_start
        ↓
token
        ↓
token
        ↓
...
        ↓
answer_end
```

### Challenge

Expected sequence:

``` text
challenge_started
        ↓
claims
        ↓
challenge_plan
        ↓
challenge_evidence
        ↓
answer_start
        ↓
token
        ↓
...
        ↓
answer_end
```

An `error` event may occur instead of normal completion when processing
fails.

The frontend should tolerate multiple `token` events and reconstruct the
final answer by concatenating them in order.

------------------------------------------------------------------------

# 18. API Evaluation

API tests should verify:

-   valid request acceptance
-   request validation
-   response shape
-   conversation ID propagation
-   HTTP status codes
-   streaming content type
-   request ID headers
-   conversation lifecycle behavior
-   error behavior

The API should be testable without requiring a browser.

------------------------------------------------------------------------

# 19. Reliability Evaluation

Reliability tests should include controlled failure scenarios.

Examples:

### Missing Groq API key

Expected:

``` text
/readiness → 503
```

### Invalid tool arguments

Expected:

``` text
controlled validation error
```

### Tool execution failure

Expected:

``` text
error returned to orchestration layer
```

### LLM failure

Expected:

``` text
controlled application error
```

### Maximum tool iterations exceeded

Expected:

``` text
RuntimeError
```

The important principle is that failures should be bounded and
observable rather than causing uncontrolled execution.

------------------------------------------------------------------------

# 20. Data Access Boundary Evaluation

The architecture establishes a strict data-access boundary:

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

Evaluation should ensure:

-   the LLM does not execute SQL
-   tools do not execute SQL directly
-   analytics modules do not create database connections
-   repositories own SQL execution
-   dynamic SQL values are parameterized
-   repository results are structured Python data

This is an architectural quality check as much as a functional test.

------------------------------------------------------------------------

# 21. Security Evaluation

The current project is a training/development implementation, so
security evaluation focuses on the implemented boundaries.

Checks include:

-   secrets are loaded through environment configuration
-   API keys are not hardcoded
-   `.env` files are excluded from source control
-   SQL parameters are used for dynamic values
-   tool access is allow-listed
-   product result limits are enforced
-   agent iterations are bounded
-   CORS is configurable
-   error messages do not intentionally expose secrets

Enterprise authentication and authorization are not yet implemented.

------------------------------------------------------------------------

# 22. Evaluation Dataset

A future production-grade evaluation suite should maintain a fixed set
of representative business questions.

Example categories:

### Sales

``` text
What is total revenue?
Show monthly revenue.
Which region generated the most revenue?
```

### Products

``` text
Which products have the highest revenue?
Which category contributes the most sales?
```

### Customers

``` text
How do customer segments perform?
Which segment generates the most revenue?
```

### Promotions

``` text
Did promoted products perform differently?
```

### Inventory

``` text
What is the stockout rate?
```

### Investigation

``` text
Investigate the reasons behind the revenue decline.
```

### Challenge

``` text
Challenge my conclusion.
```

Each evaluation case should eventually contain:

``` text
Question
Expected analytical capability
Expected evidence
Expected numerical facts
Acceptable answer characteristics
Known limitations
```

------------------------------------------------------------------------

# 23. Human Evaluation

Not every LLM behavior can be fully captured with deterministic
assertions.

Human review can therefore assess:

  -----------------------------------------------------------------------
  Dimension                           Review question
  ----------------------------------- -----------------------------------
  Relevance                           Did the answer address the
                                      question?

  Groundedness                        Are important claims supported by
                                      evidence?

  Clarity                             Is the explanation understandable?

  Causality discipline                Does it avoid unsupported causal
                                      claims?

  Usefulness                          Does the answer help the user
                                      investigate the issue?

  Transparency                        Does it communicate uncertainty and
                                      limitations?

  Challenge quality                   Does the challenge meaningfully
                                      question the conclusion?
  -----------------------------------------------------------------------

Human evaluation should review the evidence and answer together.

------------------------------------------------------------------------

# 24. Example Evaluation Record

A useful evaluation record can look like:

``` json
{
  "question": "Why did revenue decline?",
  "mode": "investigation",
  "conversation_id": "evaluation-001",
  "selected_areas": [
    "revenue_trend",
    "regional_performance",
    "product_performance"
  ],
  "grounded": true,
  "numerically_correct": true,
  "causal_claim_supported": false,
  "answer_relevant": true,
  "challenge_required": true,
  "notes": "Regional concentration was supported, but causality remained uncertain."
}
```

This separates individual quality dimensions instead of collapsing
everything into one model score.

------------------------------------------------------------------------

# 25. What Should Not Be Used as the Only Metric

The project should not evaluate the copilot using only:

``` text
LLM response quality
```

or only:

``` text
accuracy
```

A natural-language answer can sound convincing while containing
incorrect numbers.

Likewise, a tool can return correct numbers while the final answer
misinterprets them.

The complete evaluation chain is:

``` text
Data correctness
      +
Analytical correctness
      +
Tool correctness
      +
Agent orchestration
      +
Evidence grounding
      +
Answer quality
      +
Application reliability
```

------------------------------------------------------------------------

# 26. Current Evaluation Status

  Area                                   Status
  -------------------------------------- -------------
  Repository tests                       Implemented
  Analytics tests                        Implemented
  Anomaly detection tests                Implemented
  Agent/tool tests                       Implemented
  Conversation tests                     Implemented
  Investigation tests                    Implemented
  Challenge tests                        Implemented
  API tests                              Implemented
  Frontend build validation              Implemented
  Formal LLM evaluation dataset          Planned
  Automated groundedness benchmark       Planned
  Automated numerical-answer benchmark   Planned
  Production load testing                Planned
  Enterprise security testing            Planned

------------------------------------------------------------------------

# 27. FDE Perspective

The important lesson from this project is that evaluating an AI
application is different from evaluating only a model.

An FDE should be able to answer:

> Where did the answer come from?

For Nexa, the answer should be traceable through:

``` text
User Question
      ↓
Agent Decision
      ↓
Tool
      ↓
Repository
      ↓
Database
      ↓
Deterministic Result
      ↓
LLM Interpretation
      ↓
Final Answer
```

That traceability makes debugging possible.

If the answer is wrong, the team can ask:

``` text
Was the database wrong?
        ↓
Was the SQL wrong?
        ↓
Was the analytical function wrong?
        ↓
Was the wrong tool selected?
        ↓
Was the evidence interpreted incorrectly?
        ↓
Did the final synthesis introduce an unsupported claim?
```

This is the core evaluation mindset for an enterprise AI application.

------------------------------------------------------------------------

# 28. Final Evaluation Mental Model

``` text
                 ┌───────────────────┐
                 │   User Question   │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ Agent / Planner   │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ Approved Tools    │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ Deterministic     │
                 │ Analytics         │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ Evidence          │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ LLM Synthesis     │
                 └─────────┬─────────┘
                           ↓
                 ┌───────────────────┐
                 │ Final Answer      │
                 └───────────────────┘

          Evaluate every boundary independently.
```

The central principle is:

> **Do not ask only whether the AI gave a good answer. Ask whether the
> entire system produced a correct, grounded, traceable, and reliable
> answer.**
