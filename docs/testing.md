# Testing Guide

## 1. Purpose

This document explains how to run, understand, and extend the automated
tests for the Nexa Consumer Products Analytics Copilot.

The testing strategy follows the architecture of the application:

``` text
API
 ↓
Agent / Orchestration
 ↓
Tools
 ↓
Analytics
 ↓
Repositories
 ↓
Database
```

Tests are organized so that deterministic application logic can be
validated independently from LLM-powered behavior.

The goal is not simply to prove that the application starts. The goal is
to verify that:

-   analytical results are correct
-   application boundaries are respected
-   conversation state behaves correctly
-   investigation state is preserved
-   challenge behavior is bounded
-   API contracts remain stable
-   failures are handled predictably

------------------------------------------------------------------------

# 2. Testing Philosophy

The project follows a layered testing strategy.

``` text
              End-to-End
                  ▲
                  │
            Integration
                  ▲
                  │
          Agent / Workflow
                  ▲
                  │
        Analytics / Tools
                  ▲
                  │
        Repository / Unit
```

The lower layers should contain the largest number of tests because they
are:

-   faster
-   deterministic
-   easier to debug
-   less dependent on external services

LLM-powered tests should be targeted rather than used for every
assertion.

------------------------------------------------------------------------

# 3. Test Location

Backend tests are stored under:

``` text
backend/tests/
```

The test suite is executed from the backend directory.

Expected project structure:

``` text
backend/
├── app/
├── database/
├── data/
├── tests/
│   ├── ...
│   └── ...
├── requirements.txt
└── ...
```

------------------------------------------------------------------------

# 4. Environment Setup

Activate the backend virtual environment before running the tests.

### Windows PowerShell

``` powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

### Windows Command Prompt

``` cmd
cd backend
.venv\Scripts\activate
```

If the project uses another virtual-environment location, activate that
environment instead.

------------------------------------------------------------------------

# 5. Running the Complete Test Suite

From:

``` text
backend/
```

run:

``` bash
pytest
```

A successful run should report the test count and completion status.

The latest completed full backend run was:

``` text
76 passed, 2 deselected, 1 warning
```

The warning was a dependency-level `anyio`/Starlette deprecation warning
and did not cause the test suite to fail.

------------------------------------------------------------------------

# 6. Running Tests Verbosely

For more detail:

``` bash
pytest -v
```

This prints individual test names and their results.

Useful when:

-   debugging a failed test
-   reviewing which behavior is covered
-   checking a specific feature after a refactor

------------------------------------------------------------------------

# 7. Running a Specific Test File

A single test file can be executed directly.

Example:

``` bash
pytest tests/test_session.py
```

Another example:

``` bash
pytest tests/test_conversations_api.py
```

This is useful when working on a specific feature without running the
entire suite.

------------------------------------------------------------------------

# 8. Running a Specific Test

A single test can be selected with `-k`.

Example:

``` bash
pytest -k conversation
```

This runs tests whose names match `conversation`.

Another example:

``` bash
pytest -k anomaly
```

This is useful when validating one behavior during development.

------------------------------------------------------------------------

# 9. Test Categories

The current project contains several categories of tests.

## 9.1 Session Tests

Conversation session behavior is tested independently from FastAPI.

The session manager tests verify:

-   session creation
-   session retrieval
-   history management
-   message insertion
-   timestamp updates
-   rename behavior
-   archive behavior
-   unarchive behavior
-   deletion
-   clearing conversation state

This validates the domain behavior before API integration is considered.

------------------------------------------------------------------------

## 9.2 Conversation API Tests

The conversation API tests validate the HTTP contract.

They cover:

-   creating a conversation
-   creating a conversation with a supplied ID
-   listing conversations
-   retrieving a conversation
-   archive behavior
-   delete behavior
-   archived conversation filtering

The tests are intentionally contract-focused.

For example:

``` text
POST /api/conversations
        ↓
ConversationManager
        ↓
Full conversation response
```

The API test verifies the complete contract rather than only checking
HTTP `200`.

------------------------------------------------------------------------

# 10. Chat / Conversation Integration Tests

The chat integration tests verify that Copilot and conversation memory
work together.

Important behaviors include:

### First message

``` text
User
 ↓
/api/chat
 ↓
Conversation history updated
```

### Follow-up message

``` text
User
 ↓
/api/chat
 ↓
Existing history supplied to agent
 ↓
New response
 ↓
History updated again
```

### Conversation isolation

``` text
Conversation A
      X
Conversation B
```

History from one conversation must not leak into another.

The tests also verify that conversation timestamps change after
activity.

------------------------------------------------------------------------

# 11. Investigation Memory Tests

Investigation memory is separate from ordinary conversation message
history.

Tests verify that a completed investigation can store:

``` text
Plan
Evidence
Answer
```

against the shared conversation/investigation ID.

The tests also verify that:

-   investigation context can be retrieved
-   different investigations remain isolated
-   investigation and chat can share the same conversation identity
-   completed investigation context is available for Challenge Mode

This distinction is important:

``` text
Conversation History
        +
Investigation Analytical Memory
```

They are related but serve different purposes.

------------------------------------------------------------------------

# 12. Agent and Tool Tests

Agent tests validate the orchestration boundary.

Important areas include:

-   approved tool definitions
-   tool dispatch
-   argument parsing
-   tool result serialization
-   product-limit validation
-   error handling
-   bounded tool iterations

The agent must not be able to execute arbitrary SQL.

The intended path is:

``` text
Groq
 ↓
Approved tool
 ↓
Analytics
 ↓
Repository
 ↓
Database
```

------------------------------------------------------------------------

# 13. Repository Tests

Repositories are the application's database-access boundary.

Tests should verify that repository methods:

-   execute the expected database operation
-   return structured Python data
-   correctly apply filters
-   correctly aggregate or retrieve requested data
-   handle empty results
-   use parameterized values for dynamic inputs

Repository tests should not require the LLM.

This makes database correctness independently testable.

------------------------------------------------------------------------

# 14. Analytics Tests

Analytics functions should be tested independently wherever possible.

Examples include:

``` text
sales.py
products.py
customers.py
promotions.py
inventory.py
```

Typical assertions include:

``` text
expected total
expected ranking
expected percentage
expected grouping
expected ordering
```

For example:

``` text
Input:
three monthly revenue values

Expected:
correct monthly aggregation
```

The test should validate the analytical logic rather than whether Groq
describes the result correctly.

------------------------------------------------------------------------

# 15. Anomaly Detection Tests

The anomaly engine is deterministic and therefore suitable for precise
tests.

Current configuration:

``` text
MIN_HISTORY_MONTHS = 3
LOW_ANOMALY_THRESHOLD = 10%
MEDIUM_ANOMALY_THRESHOLD = 20%
HIGH_ANOMALY_THRESHOLD = 30%
```

The test suite should verify:

-   insufficient history is ignored
-   the current month is excluded from its own baseline
-   three-month rolling history is used
-   deviation percentage is correct
-   anomaly direction is correct
-   threshold classification is correct
-   zero baseline does not produce invalid calculations
-   normal months are excluded from the anomaly result

Example:

``` text
Previous 3 months:
100
100
100

Current month:
140
```

Expected:

``` text
Baseline = 100
Deviation = 40%
Classification = high
Direction = up
```

------------------------------------------------------------------------

# 16. Investigation Tests

Investigation tests validate the multi-stage workflow.

The workflow is:

``` text
Question
   ↓
Planning
   ↓
Hypothesis generation
   ↓
Evidence collection
   ↓
Synthesis
```

Tests should verify that the stages connect correctly.

## Planning

Verify that the planner returns only valid investigation areas.

## Hypotheses

Verify that generated hypotheses have the expected structure and can be
validated.

## Evidence

Verify that selected investigation areas map to approved analytics
tools.

## Synthesis

Verify that evidence and hypotheses are passed into the synthesis stage.

------------------------------------------------------------------------

# 17. Challenge Tests

Challenge Mode has a deliberately bounded architecture.

``` text
Completed Investigation
        ↓
Existing Evidence
        ↓
Direct Challenge Reviewer
        ↓
One bounded Groq call
        ↓
Streamed report
```

Tests should verify:

-   latest investigation is required
-   existing investigation evidence is reused
-   challenge preparation succeeds with valid investigation state
-   challenge output contains the expected sections/events
-   challenge synthesis remains bounded
-   compatibility events remain available to the frontend

The challenge implementation should not silently expand into another
broad evidence-collection workflow.

------------------------------------------------------------------------

# 18. Streaming Tests

Investigation and Challenge use:

``` text
application/x-ndjson
```

Tests should validate:

-   response content type
-   event serialization
-   event ordering
-   token streaming
-   completion events
-   error events

### Investigation expected sequence

``` text
investigation_started
plan
hypotheses
answer_start
token...
answer_end
```

### Challenge expected sequence

``` text
challenge_started
claims
challenge_plan
challenge_evidence
answer_start
token...
answer_end
```

The exact number of `token` events is not fixed.

The client should concatenate token data in arrival order.

------------------------------------------------------------------------

# 19. API Error Tests

The API should be tested for expected failure paths.

Examples:

### Invalid message

A message outside the configured request constraints should fail
validation.

### Missing configuration

Readiness should fail when the Groq API key is unavailable.

### Agent runtime failure

The API should convert the runtime failure into a controlled HTTP
response.

### Unexpected exception

The API should return a controlled server error rather than exposing an
uncontrolled traceback to the client.

------------------------------------------------------------------------

# 20. Frontend Validation

The frontend currently uses Vite.

A production build can be validated with:

``` bash
cd frontend
npm run build
```

A successful build confirms that:

-   TypeScript compilation succeeds
-   imports resolve
-   React components compile
-   Vite can produce the production bundle

The current build has completed successfully.

Vite also reports a bundle-size warning because the main JavaScript
bundle is larger than the configured warning threshold.

That warning is not currently treated as a build failure.

------------------------------------------------------------------------

# 21. Frontend Conversation Testing

The frontend conversation workflow should be manually validated after
major UI changes.

Minimum scenarios:

### New conversation

``` text
Click New Chat
    ↓
New conversation ID
    ↓
Empty history
    ↓
New Chat title
```

### First question

``` text
Enter question
    ↓
User message appears
    ↓
Assistant answer appears
    ↓
Conversation moves to recent activity
```

### Follow-up

``` text
Ask second question
    ↓
Previous context remains visible
```

### Investigation

``` text
Switch to Investigation
    ↓
Use same conversation
    ↓
Investigation response appears
```

### Challenge

``` text
Complete investigation
    ↓
Challenge conclusion
    ↓
Challenge stream appears
```

### Archive

``` text
Archive conversation
    ↓
Conversation disappears from active list
```

### Restore

``` text
Restore conversation
    ↓
Conversation returns to active list
```

### Delete

``` text
Delete conversation
    ↓
Conversation removed
```

------------------------------------------------------------------------

# 22. Test Isolation

Tests should avoid depending on the order in which other tests execute.

A test should be able to run independently.

Bad pattern:

``` text
test_a()
creates global state

test_b()
assumes test_a already ran
```

Preferred pattern:

``` text
test_b()
creates its own required state
```

This is especially important for the in-memory:

``` text
ConversationManager
InvestigationSessionManager
```

because global state can otherwise leak between tests.

------------------------------------------------------------------------

# 23. Mocking External LLM Calls

Tests should avoid unnecessary calls to the real Groq API.

For deterministic tests, mock the external LLM boundary.

This provides:

-   faster tests
-   lower API usage
-   repeatable results
-   predictable failures
-   no dependency on model availability

A mocked response should reproduce the structure expected by the
application.

For example:

``` text
Agent
 ↓
Mock Groq response
 ↓
Tool call
 ↓
Deterministic result
```

Real-model testing should be reserved for targeted
integration/evaluation scenarios.

------------------------------------------------------------------------

# 24. Testing Data Access Boundaries

One architectural test principle is:

> Every layer should use the layer below it through its defined
> interface.

Expected:

``` text
Agent → Tools
Tools → Analytics
Analytics → Repositories
Repositories → Database
```

Unexpected:

``` text
Agent → SQLite
Tools → SQLite
Analytics → sqlite3
```

This boundary should be preserved during future refactoring.

------------------------------------------------------------------------

# 25. Regression Testing

Before changing an established feature:

``` text
1. Run the relevant focused tests.
2. Make the change.
3. Run the focused tests again.
4. Run the full suite.
5. Build the frontend if frontend code changed.
```

Recommended workflow:

``` bash
pytest -k <feature>
```

then:

``` bash
pytest
```

For frontend changes:

``` bash
npm run build
```

This is particularly important because conversation state is shared
across:

``` text
Copilot
Investigation
Challenge
```

A change in one area can therefore affect another.

------------------------------------------------------------------------

# 26. Recommended Pre-Commit Checklist

Before committing backend changes:

``` text
[ ] Focused tests pass
[ ] Full backend suite passes
[ ] No accidental debug prints
[ ] No secrets committed
[ ] API contract unchanged or documented
[ ] Repository boundary preserved
[ ] Agent iteration limits preserved
[ ] Error handling preserved
```

Before committing frontend changes:

``` text
[ ] TypeScript compiles
[ ] npm run build passes
[ ] Conversation flow checked
[ ] Investigation flow checked
[ ] Challenge flow checked
[ ] No broken API contract
```

Before committing documentation:

``` text
[ ] File path is correct
[ ] Examples match current implementation
[ ] Known limitations are documented
[ ] No future feature is described as implemented
```

------------------------------------------------------------------------

# 27. Known Testing Limitations

The current test strategy has several limitations.

## In-memory state

Conversation state exists only inside the running backend process.

Therefore, persistence across backend restarts is not currently tested.

## Synthetic data

The application uses synthetic CPG data.

Test results therefore validate application behavior rather than
real-world CPG business distributions.

## LLM variability

LLM outputs can vary between model versions or model configurations.

Tests that depend on exact natural-language output should therefore be
avoided.

Prefer testing:

``` text
structure
tool selection
groundedness
numeric facts
workflow behavior
```

rather than exact wording.

------------------------------------------------------------------------

# 28. Testing Mental Model

The project should be tested from the bottom up:

``` text
                  User Experience
                        ↑
                   API Contract
                        ↑
                Agent / Workflow
                        ↑
                  Tool Boundary
                        ↑
                   Analytics
                        ↑
                  Repository
                        ↑
                    Database
```

If a final answer is wrong, debugging should move downward through these
boundaries.

For example:

``` text
Wrong answer
    ↓
Check final synthesis
    ↓
Check evidence
    ↓
Check tool selection
    ↓
Check analytics
    ↓
Check repository
    ↓
Check source data
```

This is much more reliable than immediately blaming the LLM.

------------------------------------------------------------------------

# 29. Final Testing Principle

The most important testing rule for Nexa is:

> **Test the business truth independently from the language model.**

The database and deterministic analytics establish what the system
knows.

The agent determines how to retrieve and combine that information.

The LLM turns evidence into a useful explanation.

Therefore:

``` text
Correct Data
    +
Correct Analytics
    +
Correct Orchestration
    +
Grounded Synthesis
    +
Reliable API
    =
Trustworthy Analytical Application
```

That is the testing mindset expected from an FDE building an enterprise
AI application.
