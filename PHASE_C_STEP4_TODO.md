# Phase C Step 4: Action Execution Engine (TODO)

This document outlines the next phase after the Action Executor scaffolding.

## Overview

Phase C Step 4 will implement **actual execution** of approved actions.

**Constraint**: Must NOT break Phase C Step 3 scaffolding or earlier phases.

## Scope

### 1. Execution Handlers

Implement action handlers behind interfaces:

```python
class ActionHandler(ABC):
    """Base class for action handlers."""

    @abstractmethod
    def execute(self, plan: ExecutionPlan, step: ExecutionStep) -> ExecutionResult:
        """Execute action. Return status."""
        pass

    @abstractmethod
    def rollback(self, result: ExecutionResult) -> bool:
        """Undo action. Return success."""
        pass
```

Handlers to implement:

- `FlagActionHandler`
- `ArchiveActionHandler`
- `LabelActionHandler`
- `ReadActionHandler`
- `SpamActionHandler`

### 2. Gmail API Integration

Abstract away Gmail details:

```python
class GmailService:
    """Wrapper around Gmail API."""

    def flag_message(self, email_id: str) -> bool:
        # TODO: Call Gmail API

    def archive_message(self, email_id: str) -> bool:
        # TODO: Call Gmail API

    # ... etc
```

**Important**: Use user's existing OAuth credentials (don't add new OAuth logic).

### 3. Execution Status Tracking

Extend `ActionRecommendation` model:

```sql
ALTER TABLE action_recommendations ADD COLUMN execution_plan_id TEXT;
ALTER TABLE action_recommendations ADD COLUMN execution_status TEXT;  -- PENDING, EXECUTING, COMPLETED, FAILED, ROLLED_BACK
ALTER TABLE action_recommendations ADD COLUMN last_execution_attempt TIMESTAMP;
ALTER TABLE action_recommendations ADD COLUMN execution_error TEXT;
```

Create `ExecutionLog` table:

```sql
CREATE TABLE execution_logs (
    id TEXT PRIMARY KEY,
    plan_id TEXT,
    step_index INT,
    action_type TEXT,
    status TEXT,  -- PENDING, IN_PROGRESS, COMPLETED, FAILED
    result JSON,  -- Action-specific result
    error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES execution_plans(id)
);
```

### 4. Rate Limiting & Retries

Implement exponential backoff:

```python
class ExecutionRetryPolicy:
    """Retry strategy for failed actions."""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        # Retry transient errors, not permanent ones

    def backoff_delay(self, attempt: int) -> float:
        # Exponential backoff with jitter
```

### 5. Approval Workflow

Add user approval for sensitive actions:

```python
class ApprovalRequest:
    plan_id: str
    user_id: str
    action_summary: str
    risk_score: float  # 0-100
    created_at: datetime
    expires_at: datetime  # 1 hour default

    def approve(self, user_id: str) -> bool:
        # User approves, execution proceeds

    def reject(self, user_id: str, reason: str) -> bool:
        # User rejects, mark plan as rejected
```

**Actions requiring approval**:

- Archive (score > 50)
- Delete operations (score > 75) -- but delete not in allowed list yet

### 6. Rollback & Reversal

Implement safe rollback:

```python
class RollbackManager:
    """Manage reversal of executed actions."""

    def create_snapshot(self, email_id: str) -> Snapshot:
        """Record email state before changes."""

    def rollback_action(self, log: ExecutionLog) -> bool:
        """Undo the action."""

    def rollback_plan(self, plan: ExecutionPlan) -> bool:
        """Undo all executed steps in plan."""
```

## Files to Create/Modify

### New Files

- `backend/executor/handlers/` (package)
  - `__init__.py`
  - `base.py` (ActionHandler ABC)
  - `flag_handler.py`
  - `archive_handler.py`
  - `label_handler.py`
  - `read_handler.py`
  - `spam_handler.py`
- `backend/executor/gmail_service.py` (Gmail API wrapper)
- `backend/executor/retry_policy.py` (Retry logic)
- `backend/executor/approval_workflow.py` (Approval requests)
- `backend/executor/rollback_manager.py` (Reversal logic)
- `backend/models.py` (extend: ExecutionLog, ApprovalRequest, ExecutionSnapshot)
- `backend/tests/test_action_handlers.py` (handler tests)
- `backend/tests/test_execution_engine.py` (integration tests)
- `backend/api/execution.py` (endpoints for status, approval, etc.)

### Modified Files

- `backend/executor/action_executor.py` (add execute() method)
- `backend/models.py` (add new tables)
- `backend/tests/test_rule_engine.py` (no changes, should still pass)
- `backend/tests/test_action_executor.py` (no changes, should still pass)

## Testing Strategy

1. **Unit Tests**

   - Each handler in isolation (with mocked Gmail)
   - Retry policy with various error scenarios
   - Approval workflow state machine

2. **Integration Tests**

   - Full plan execution (mock Gmail API)
   - Rollback after failed action
   - Retry logic with exponential backoff

3. **Regression Tests**

   - All Phase C Step 2 & 3 tests still pass
   - No changes to RuleEngine behavior
   - No database schema breaking changes

4. **E2E Tests**
   - Real Gmail API (sandbox account)
   - Full pipeline: classify → recommend → execute → verify in inbox

## Implementation Order

1. Create Gmail service wrapper (mock initially)
2. Implement base ActionHandler
3. Implement individual handlers (flag, archive, label, read, spam)
4. Add retry policy and backoff logic
5. Implement approval workflow
6. Add execution status tracking (database)
7. Implement rollback manager
8. Add API endpoints for status/approval
9. Write comprehensive tests
10. E2E verification with real Gmail (test account)

## Constraints

✅ **No Breaking Changes**

- Phase C Step 3 remains frozen
- Phase C Step 2 RuleEngine untouched
- All existing tests pass

✅ **Side Effects Only Behind Handlers**

- Gmail API calls encapsulated
- Easily mockable for testing
- Clear execution flow

✅ **Reversible**

- Rollback capabilities
- Audit trail of all changes
- User can revert if needed

✅ **Safe**

- Approval for sensitive actions
- Rate limiting to avoid throttling
- Retry logic for transient failures
- Snapshots before mutations

## Risk Mitigation

| Risk                 | Mitigation                                 |
| -------------------- | ------------------------------------------ |
| Gmail API errors     | Retry policy, exponential backoff          |
| Rate limiting        | Queue, batch operations, jitter            |
| Lost actions         | Execution logs, snapshots, rollback        |
| Unauthorized changes | Approval workflow, user override           |
| Data corruption      | Snapshot before changes, ACID transactions |

## Success Criteria

- [ ] 40+ unit tests passing (handlers, retry, approval)
- [ ] 20+ integration tests passing (full execution flow)
- [ ] All Phase C Step 2 & 3 tests still passing (62 tests)
- [ ] E2E test with real Gmail API (on test account)
- [ ] Zero regressions in Phase A/B
- [ ] Execution log fully auditable
- [ ] User-facing approval workflow mockup
- [ ] Rollback tested and verified

## Future Enhancements (Phase C Step 5+)

- Batch execution (multiple emails at once)
- Scheduled execution (execute later)
- Undo UI (let user revert via web)
- Execution analytics dashboard
- Machine learning feedback loop (learn from user overrides)
