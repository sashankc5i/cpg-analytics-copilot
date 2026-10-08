# Roadmap

## 1. Purpose

This roadmap describes the future evolution of the Nexa Consumer
Products Analytics Copilot after the current training implementation.

The current project scope is considered complete for the defined five
features:

``` text
1. Investigation Planning
2. Investigation / Evidence / Synthesis
3. Challenge My Conclusion
4. Anomaly Detection
5. Conversation / Investigation Memory
```

The roadmap therefore focuses on **hardening, productionization,
evaluation, and enterprise readiness** rather than introducing another
core feature into the current build.

------------------------------------------------------------------------

# 2. Current State

The application currently provides:

  Capability                        Status
  --------------------------------- ----------
  Conversational Copilot            Complete
  Approved analytics tools          Complete
  Deterministic analytics           Complete
  Repository data-access boundary   Complete
  Investigation workflow            Complete
  Hypothesis generation             Complete
  Evidence collection               Complete
  Evidence synthesis                Complete
  Challenge My Conclusion           Complete
  Revenue anomaly detection         Complete
  Conversation history              Complete
  Investigation memory              Complete
  Shared conversation identity      Complete
  Conversation titles               Complete
  Rename                            Complete
  Archive / Restore                 Complete
  Delete                            Complete
  Markdown tables                   Complete
  Streaming investigation           Complete
  Streaming challenge               Complete
  Automated backend tests           Complete
  Core documentation                Complete

The application is now at the point where additional work should
primarily improve reliability, security, evaluation, deployment
readiness, and maintainability.

------------------------------------------------------------------------

# 3. Roadmap Principles

Future development should preserve the existing architectural
boundaries.

The most important principle is:

``` text
Do not sacrifice architectural correctness
for additional AI functionality.
```

Future changes should continue to preserve:

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

and:

``` text
LLM
  ↓
Interpretation / orchestration
  ↓
Deterministic application logic
  ↓
Evidence
  ↓
LLM
  ↓
Explanation
```

------------------------------------------------------------------------

# 4. Phase 1 --- Documentation and Hardening

## Objective

Finish the engineering documentation and stabilize the current
implementation before adding production infrastructure.

### Activities

-   maintain README
-   maintain architecture documentation
-   maintain data-model documentation
-   maintain agent-design documentation
-   maintain API documentation
-   maintain evaluation documentation
-   maintain testing documentation
-   maintain architecture decisions
-   maintain roadmap
-   document environment configuration

### Success criteria

``` text
Documentation matches implementation
+
Known limitations are explicit
+
Tests remain green
```

This phase is effectively the current project completion boundary.

------------------------------------------------------------------------

# 5. Phase 2 --- Evaluation Framework

## Objective

Move from application-level tests toward systematic evaluation of AI
behavior.

The current automated tests validate software behavior, but a production
AI application also needs to evaluate the quality of model-driven
behavior.

### Planned capabilities

Create a representative evaluation dataset containing:

``` text
Question
Expected analytical intent
Expected tool(s)
Expected evidence
Expected numerical facts
Expected answer characteristics
```

Example:

``` text
Question:
Which region experienced the largest revenue decline?

Expected:
Regional performance analysis

Expected evidence:
Regional revenue comparison

Expected answer:
Grounded in returned analytical values
```

### Evaluation dimensions

Measure:

-   tool-selection accuracy
-   numerical accuracy
-   evidence groundedness
-   unsupported-claim rate
-   causal-claim discipline
-   investigation completeness
-   challenge usefulness
-   response structure

------------------------------------------------------------------------

# 6. Phase 3 --- Persistent Conversation Storage

## Objective

Replace the current in-memory conversation state with durable storage.

Current architecture:

``` text
FastAPI process
      ↓
In-memory ConversationManager
```

Future architecture:

``` text
FastAPI
   ↓
Conversation Repository
   ↓
Persistent Database
```

### Requirements

Persistent storage should support:

-   conversation metadata
-   messages
-   timestamps
-   archive state
-   investigation state
-   conversation ownership

### Important consideration

Persistence should not leak into the agent layer.

The intended architecture remains:

``` text
Agent
  ↓
Conversation service
  ↓
Conversation repository
  ↓
Database
```

------------------------------------------------------------------------

# 7. Phase 4 --- Authentication and Authorization

## Objective

Introduce enterprise identity and access control.

The current training implementation does not include authentication or
authorization.

A production system would need:

``` text
User
 ↓
Identity Provider
 ↓
Authentication
 ↓
Authorization
 ↓
Conversation
 ↓
Analytics
```

### Planned capabilities

-   enterprise identity integration
-   user identity propagation
-   role-based access
-   conversation ownership
-   permission-aware data access
-   audit information

### Data isolation

The system should ensure that:

``` text
User A
```

cannot access:

``` text
User B's
conversation or restricted data
```

------------------------------------------------------------------------

# 8. Phase 5 --- Enterprise Data Access

## Objective

Move from the training SQLite datastore toward enterprise data sources.

Potential production architecture:

``` text
Enterprise Sources
       ↓
Data Platform
       ↓
Approved Analytics Layer
       ↓
Analytics Tools
       ↓
Copilot
```

The exact data platform depends on the deployment environment and
organizational architecture.

The repository boundary should remain intact so that changing the
underlying datastore does not require rewriting the agent.

------------------------------------------------------------------------

# 9. Phase 6 --- Production Observability

## Objective

Make the application operationally observable.

Current logging provides basic workflow visibility.

A production implementation should introduce structured telemetry
around:

``` text
Request
 ↓
Agent execution
 ↓
Tool calls
 ↓
Database operations
 ↓
LLM calls
 ↓
Final response
```

### Metrics

Potential metrics include:

-   request latency
-   tool-call latency
-   LLM latency
-   token usage
-   error rate
-   tool failure rate
-   investigation completion rate
-   challenge completion rate
-   response streaming duration

### Tracing

A trace should make it possible to follow:

``` text
request_id
    ↓
conversation_id
    ↓
agent run
    ↓
tool calls
    ↓
analytics
    ↓
database
    ↓
LLM synthesis
```

------------------------------------------------------------------------

# 10. Phase 7 --- Reliability Engineering

## Objective

Improve resilience under production conditions.

Potential areas include:

-   timeouts
-   retry policies
-   circuit breakers where appropriate
-   graceful degradation
-   dependency failure handling
-   concurrency controls
-   rate limiting
-   resource limits

The existing design already establishes bounded agent and challenge
execution.

Future reliability work should build on that foundation rather than
removing those limits.

------------------------------------------------------------------------

# 11. Phase 8 --- Security Hardening

## Objective

Prepare the application for enterprise security requirements.

Potential areas:

### Secrets

Move production secrets into a managed secret store.

### Network

Introduce appropriate network controls and private connectivity where
required.

### API security

Add:

-   authentication
-   authorization
-   request validation
-   rate limiting
-   secure headers
-   controlled CORS

### Data security

Evaluate:

-   encryption
-   access policies
-   audit requirements
-   sensitive-data handling
-   data retention

### AI security

Evaluate:

-   prompt injection
-   indirect prompt injection
-   malicious tool arguments
-   excessive tool access
-   data exfiltration through model responses

------------------------------------------------------------------------

# 12. Phase 9 --- Model and Prompt Evaluation

## Objective

Treat model behavior as an engineering surface.

The application should maintain controlled evaluation cases for:

``` text
Simple questions
Multi-step questions
Ambiguous questions
Follow-up questions
Unsupported questions
Anomaly questions
Investigation questions
Challenge questions
```

### Prompt changes

Prompt modifications should be evaluated against a regression dataset
rather than judged only from one manual example.

The goal is:

``` text
Prompt change
   ↓
Evaluation suite
   ↓
Compare behavior
   ↓
Accept / revise
```

------------------------------------------------------------------------

# 13. Phase 10 --- Performance and Load Testing

## Objective

Understand how the application behaves under concurrent usage.

Areas to measure:

-   API throughput
-   concurrent conversations
-   database latency
-   tool execution latency
-   LLM latency
-   streaming performance
-   memory consumption

Example test scenarios:

``` text
1 user
10 concurrent users
50 concurrent users
100 concurrent users
```

Actual production targets should be determined from business
requirements rather than assumed in the training project.

------------------------------------------------------------------------

# 14. Phase 11 --- Deployment

## Objective

Move from local development to a repeatable deployment architecture.

A future deployment could follow:

``` text
Developer
   ↓
Git
   ↓
CI
   ↓
Tests
   ↓
Build
   ↓
Security checks
   ↓
Container / artifact
   ↓
Deployment
   ↓
Monitoring
```

### Deployment requirements

-   environment separation
-   secret management
-   health checks
-   readiness checks
-   logging
-   rollback strategy
-   deployment validation

The exact cloud services should be selected according to the target
enterprise environment.

------------------------------------------------------------------------

# 15. Phase 12 --- CI/CD

## Objective

Automate quality gates before deployment.

Potential pipeline:

``` text
Pull Request
    ↓
Lint
    ↓
Unit Tests
    ↓
Integration Tests
    ↓
Frontend Build
    ↓
Security Checks
    ↓
AI Evaluation Checks
    ↓
Build Artifact
    ↓
Deploy
```

A deployment should not proceed when critical quality gates fail.

------------------------------------------------------------------------

# 16. Phase 13 --- Advanced Analytics

Once the core architecture is stable, additional deterministic analytics
can be introduced without changing the agent boundary.

Potential areas include:

-   customer lifetime value
-   RFM analysis
-   churn indicators
-   basket analysis
-   price elasticity
-   promotion uplift
-   demand forecasting
-   inventory risk
-   regional opportunity analysis

The preferred pattern remains:

``` text
New analytical capability
        ↓
Analytics function
        ↓
Repository access
        ↓
Approved tool
        ↓
Agent
```

This avoids embedding analytical logic inside prompts.

------------------------------------------------------------------------

# 17. Phase 14 --- Advanced Investigation

The current investigation workflow can later be expanded.

Potential improvements include:

-   richer hypothesis structures
-   evidence confidence
-   evidence provenance
-   contradiction detection
-   evidence ranking
-   investigation history
-   reusable investigation templates

For example:

``` text
Hypothesis
    ↓
Supporting evidence
    ↓
Contradicting evidence
    ↓
Confidence / limitation
    ↓
Conclusion
```

These additions should be introduced only after the current
investigation architecture remains stable.

------------------------------------------------------------------------

# 18. Phase 15 --- Advanced Challenge Mode

Challenge Mode can later evolve into a more structured review framework.

Potential areas:

``` text
Original claim
     ↓
Evidence supporting claim
     ↓
Evidence contradicting claim
     ↓
Missing evidence
     ↓
Alternative explanation
     ↓
Recommended validation
```

The key architectural rule should remain:

> Challenge the conclusion using evidence rather than simply generating
> a contradictory opinion.

------------------------------------------------------------------------

# 19. Production Data Quality

The current synthetic dataset contains an intentional limitation:

``` text
Sales generation does not constrain sales
based on inventory stockouts.
```

Therefore:

``` text
stockout
≠
confirmed lost sale
```

A production data model could incorporate:

-   demand estimates
-   availability windows
-   lost-sales indicators
-   replenishment events
-   inventory movement
-   store-level demand
-   product substitution

This would allow stronger inventory investigations.

------------------------------------------------------------------------

# 20. Database Evolution

SQLite is appropriate for the current training application.

A future production implementation may require a managed relational
database or enterprise data platform.

The migration should primarily affect:

``` text
Repositories
+
Database configuration
```

rather than:

``` text
Agent
+
Tools
+
Frontend
```

This is one of the main benefits of maintaining the repository boundary.

------------------------------------------------------------------------

# 21. Frontend Evolution

The current frontend is intentionally focused on the conversational
workflow.

Future improvements could include:

-   richer chart interactions
-   downloadable analytical results
-   investigation timeline
-   evidence panels
-   source/provenance views
-   improved accessibility
-   responsive mobile layouts
-   performance optimization
-   code splitting

The current frontend bundle also has a Vite chunk-size warning.

Bundle optimization can therefore be addressed during future frontend
hardening.

------------------------------------------------------------------------

# 22. Documentation Evolution

Documentation should evolve with implementation.

Important documents include:

``` text
README.md
docs/architecture.md
docs/data-model.md
docs/agent-design.md
docs/api.md
docs/evaluation.md
docs/testing.md
docs/decisions.md
docs/roadmap.md
```

Whenever an architectural behavior changes, the relevant documentation
should be updated in the same engineering change.

------------------------------------------------------------------------

# 23. Suggested Future Priority

The roadmap should be interpreted as a sequence of engineering concerns
rather than a list of features to build immediately.

A reasonable progression is:

``` text
Current application
       ↓
Evaluation
       ↓
Persistent state
       ↓
Authentication / authorization
       ↓
Enterprise data
       ↓
Observability
       ↓
Reliability
       ↓
Security hardening
       ↓
Performance testing
       ↓
CI/CD
       ↓
Production deployment
```

The exact ordering can change based on deployment requirements.

------------------------------------------------------------------------

# 24. What Should Not Change Without Strong Reason

Several boundaries are foundational.

### The LLM should not become the database.

### The agent should not receive unrestricted SQL access.

### Deterministic numerical calculations should remain deterministic.

### Tool access should remain explicit and bounded.

### Investigation should remain inspectable.

### Challenge Mode should remain evidence-based.

### Conversation and analytical memory should remain conceptually separate.

### Database mechanics should remain behind repositories.

These principles should survive future technology changes.

------------------------------------------------------------------------

# 25. FDE Perspective

A useful FDE roadmap is not simply:

``` text
Build more features
```

It is:

``` text
Prove the system works
        ↓
Understand where it fails
        ↓
Make failures observable
        ↓
Make state durable
        ↓
Secure access
        ↓
Scale the system
        ↓
Operate it reliably
```

This progression turns a working prototype into an application that can
be evaluated for real-world deployment.

------------------------------------------------------------------------

# 26. Final Roadmap Mental Model

The current project has reached:

``` text
Working AI Application
        +
Deterministic Analytics
        +
Structured Investigation
        +
Challenge Workflow
        +
Conversation Memory
        +
Automated Tests
        +
Engineering Documentation
```

The next stage is not another core conversational feature.

It is:

``` text
Reliability
+
Evaluation
+
Security
+
Persistence
+
Observability
+
Deployment
```

That is the path from the current FDE training implementation toward a
production-grade enterprise analytical copilot.
