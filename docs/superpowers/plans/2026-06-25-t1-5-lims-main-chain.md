# T1.5 LIMS Main Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the real sample -> test task -> result -> review/return workflow.

**Architecture:** Extend the existing Sample/TestMethod/SampleTest/Result persistence model, expose focused FastAPI routers backed by service-layer authorization and state machines, then replace the frontend mock-only T1.5 services with typed real API calls. Preserve existing T1.4 role and table compatibility.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, pytest, React 18, TypeScript, React Query, AntD Pro, Vitest, PowerShell.

---

### Task 1: Contract and migration

**Files:**
- Modify: `backend/app/models/business.py`
- Create: `backend/alembic/versions/202606250002_complete_t1_5_lims_main_chain.py`
- Modify: `backend/tests/test_data_model.py`

- [ ] Write failing metadata/model tests for the new Sample, TestMethod, TestTask, and TestResult fields.
- [ ] Run `pytest tests/test_data_model.py -q` with `TEST_DATABASE_URL=sqlite+pysqlite:///:memory:` and confirm contract failures.
- [ ] Add the minimum columns, indexes, relationships, compatibility aliases, and migration operations.
- [ ] Re-run the targeted tests and a temporary SQLite `alembic upgrade head`.

### Task 2: Backend schemas, services, routes, and authorization

**Files:**
- Create: `backend/app/schemas/testing.py`
- Create: `backend/app/services/testing.py`
- Create: `backend/app/api/testing.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_testing_workflow.py`
- Modify: `backend/tests/test_contract_smoke.py`

- [ ] Write failing API tests for sample/method CRUD, task assignment and transitions, result draft/submit/approve/reject/resubmit, four-role behavior, invalid assignees, and cross-project access.
- [ ] Run the new test module and verify failures are missing-route/behavior failures.
- [ ] Implement Pydantic DTOs with explicit enums and forbidden extra fields on writes.
- [ ] Implement project-scoped query helpers, manager/operator/reviewer checks, and state transition maps in the service layer.
- [ ] Add thin routers for `/samples`, `/test-methods`, `/test-tasks`, and `/test-results`.
- [ ] Extend OpenAPI smoke assertions and run targeted tests until green.
- [ ] Run the full backend suite.

### Task 3: Frontend typed API and capability tests

**Files:**
- Modify: `frontend/src/types/sample.ts`
- Modify: `frontend/src/types/result.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/api/adapters.ts`
- Modify: `frontend/src/api/adapters.test.ts`
- Modify: `frontend/src/auth/permissions.ts`
- Modify: `frontend/src/auth/permissions.test.ts`
- Modify: `frontend/src/services/sample.ts`
- Modify: `frontend/src/services/result.ts`

- [ ] Write failing adapter and permission tests for T1.5 DTO mapping and role capabilities.
- [ ] Run targeted Vitest files and verify expected failures.
- [ ] Add typed DTO adapters, request payload builders, endpoints, and real-mode services; retain mock fallback only outside the T1.5 real acceptance path.
- [ ] Re-run targeted tests and typecheck.

### Task 4: Frontend workflow UI

**Files:**
- Create: `frontend/src/pages/samples/SampleFormModal.tsx`
- Modify: `frontend/src/pages/samples/SampleListPage.tsx`
- Modify: `frontend/src/pages/samples/SampleDetailPage.tsx`
- Modify: `frontend/src/pages/testing/TestingReviewPage.tsx`
- Modify: `frontend/src/components/status.ts`

- [ ] Add sample create/edit/status controls based on T1.5 capabilities.
- [ ] Add task creation, method selection, assignee selection, reassignment, and legal status controls on sample detail.
- [ ] Add result draft edit/save/submit UI for the assigned operator.
- [ ] Replace the testing placeholder with submitted-result approve/reject queue and require a rejection reason.
- [ ] Run frontend typecheck, lint, tests, and build; fix every introduced failure.

### Task 5: Demo data, full-stack smoke, and documentation

**Files:**
- Modify: `backend/scripts/seed_demo.py`
- Modify: `backend/scripts/export_openapi.py` or regenerate `backend/docs/openapi.json`
- Modify: `frontend/scripts/verify-real-api.mjs`
- Modify: `scripts/verify-fullstack.ps1`
- Create: `docs/T1.5_LIMS_MAIN_CHAIN.md`
- Modify: `README.md`

- [ ] Seed a sample, active method, assigned analyst task, and draft/submitted review fixtures without adding T1.6 data.
- [ ] Extend real API smoke to create sample/task/result, submit, approve, and verify final state.
- [ ] Keep PowerShell operational messages ASCII for Windows PowerShell 5.1.
- [ ] Document API, state machines, permission mapping, migration, and browser acceptance accounts.
- [ ] Export OpenAPI and verify the committed contract contains all T1.5 routes.

### Task 6: Final verification and commit

**Files:**
- Review all changed files.

- [ ] Run backend `compileall`, Alembic upgrade, seed, and full pytest.
- [ ] Run frontend `typecheck`, `lint`, `test`, and `build`.
- [ ] Start/confirm PostgreSQL, backend, and frontend; run `scripts/verify-fullstack.ps1`.
- [ ] Perform browser acceptance as `project_manager` and `analyst`, including rejection with comment and successful resubmission/approval.
- [ ] Run `git diff --check`, inspect scope, and confirm no T1.6 work.
- [ ] Create one final clear T1.5 commit and record `git status` plus full commit hash.
