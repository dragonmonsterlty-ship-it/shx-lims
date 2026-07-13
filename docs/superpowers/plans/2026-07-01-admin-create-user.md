# Admin Create User Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-only account creation flow to the existing user management page, including password hashing, audit logging, validation, tests, and documentation.

**Architecture:** Extend the existing admin user schema, service, and router rather than adding a registration subsystem. Add one typed frontend service operation and one AntD modal within the existing admin page, while retaining the current menu and route guards.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Argon2, pytest, React 18, TypeScript, Ant Design 5, Ant Design Pro, Vitest.

---

### Task 1: Backend create-user contract

**Files:**
- Modify: `backend/app/schemas/user.py`
- Modify: `backend/app/services/admin_users.py`
- Modify: `backend/app/api/admin_users.py`
- Test: `backend/tests/test_audit_admin.py`

- [x] **Step 1: Write failing API tests**

Add tests which POST the six request fields, assert admin success, `UserRead` response safety, stored Argon2 hash, `must_change_password=true`, a `create/user` audit row, successful login, non-admin 403, and duplicate username 409.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL="sqlite+pysqlite:///:memory:"
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_audit_admin.py -q
```

Expected: the create-user tests fail because `POST /api/admin/users` is not implemented.

- [x] **Step 3: Add the request schema**

Define `AdminUserCreate` with trimmed `username` and `display_name`, optional validated email, password length 8–255, role validation against the existing role set, and `is_active=true`.

- [x] **Step 4: Implement the service transaction**

Add `create_admin_user(db, current_user, payload)` which calls `ensure_admin_user`, rejects duplicate usernames with 409, hashes the password using `hash_password`, sets `must_change_password=true`, flushes for the new ID, records the safe audit payload, commits once, and returns the refreshed user.

- [x] **Step 5: Add the API route**

Add `POST /users` ahead of dynamic user routes and return `ApiResponse[UserRead]`.

- [x] **Step 6: Run focused tests and verify GREEN**

Repeat the focused pytest command. Expected: all tests in `test_audit_admin.py` pass.

### Task 2: Frontend service contract

**Files:**
- Modify: `frontend/src/types/admin.ts`
- Modify: `frontend/src/services/admin.ts`
- Modify: `frontend/src/services/admin.test.ts`

- [x] **Step 1: Write a failing service test**

Assert `createAdminUser(payload)` calls:

```ts
request({
  method: 'POST',
  url: '/admin/users',
  data: payload,
})
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
npm.cmd --prefix frontend run test -- src/services/admin.test.ts
```

Expected: failure because `createAdminUser` is not exported.

- [x] **Step 3: Add types and service**

Add `AdminUserCreate` with `username`, `display_name`, optional `email`, `password`, `role`, and `is_active`, then implement and export `createAdminUser`.

- [x] **Step 4: Run the focused test and verify GREEN**

Repeat the focused Vitest command. Expected: service tests pass.

### Task 3: Admin create-account modal

**Files:**
- Modify: `frontend/src/pages/admin/AdminUsersPage.tsx`
- Modify: `frontend/src/pages/admin/AdminUsersPage.test.ts`

- [x] **Step 1: Write failing page tests**

Add interaction-oriented assertions for the “添加账号” button, modal visibility, required/length/email rules, submit through `createAdminUser`, success message, modal close, form reset, table reload, duplicate username mapping, and 403 messaging.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
npm.cmd --prefix frontend run test -- src/pages/admin/AdminUsersPage.test.ts
```

Expected: failure because the create-account UI does not exist.

- [x] **Step 3: Implement minimal AntD UI**

Add ProTable `toolBarRender`, one create modal and form state, existing role options, `Switch` with `valuePropName="checked"`, and submit/error handling. Preserve the existing reset-password modal and table behavior.

- [x] **Step 4: Run focused frontend tests and verify GREEN**

Repeat the focused Vitest command. Expected: page tests pass.

### Task 4: Account provisioning documentation

**Files:**
- Modify: `README.md`

- [x] **Step 1: Add the deployment rule**

Document that self-service registration is disabled and that an admin creates accounts from “管理员管理 → 添加账号”; note that initial-password accounts must change their password after first login.

- [x] **Step 2: Verify the diff preserves existing README edits**

Run:

```powershell
git diff -- README.md
```

Expected: both pre-existing LAN deployment documentation and the new account-provisioning paragraph remain intact.

### Task 5: Full verification and requirement audit

**Files:**
- Verify all modified files.

- [x] **Step 1: Run backend tests**

```powershell
$env:TEST_DATABASE_URL="sqlite+pysqlite:///:memory:"
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

- [x] **Step 2: Run frontend tests and static checks**

```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

- [x] **Step 3: Run the authoritative repository verifier**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-fullstack.ps1
```

- [x] **Step 4: Audit scope and diff**

Run `git diff --check`, `git status --short`, and inspect the scoped diff. Confirm no public registration route/page was introduced, no unrelated behavior changed, and every acceptance criterion has direct test or source evidence.
