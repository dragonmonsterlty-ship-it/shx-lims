# T1.6A Real Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and verify the unified, locally stored T1.6A attachment lifecycle for experiment records, daily reports, samples, test tasks, and test results.

**Architecture:** Upgrade the existing generic attachment table, resolve every public entity through one authorization-aware resolver, store bytes behind a local-storage protocol, and expose one typed API. A reusable React `AttachmentPanel` calls the real API for all five entity types and leaves T1.5 business flow behavior intact.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2, Alembic, pytest, React 18, TypeScript, Ant Design 5, React Query, Axios, Vitest, PowerShell.

---

## File map

Backend:

- Modify `backend/app/core/config.py`: local attachment settings.
- Modify `backend/app/models/business.py`: canonical attachment persistence fields.
- Modify `backend/app/models/__init__.py`: keep model exports/import registration valid if required.
- Create `backend/alembic/versions/202606250003_complete_t1_6a_attachments.py`: schema/data transition.
- Replace `backend/app/schemas/attachment.py`: public enum and typed DTOs.
- Replace `backend/app/services/storage.py`: storage protocol plus local implementation.
- Create `backend/app/services/attachment_entities.py`: five-entity resolver and permission rules.
- Replace `backend/app/services/attachments.py`: security validation and lifecycle orchestration.
- Replace `backend/app/api/attachments.py`: five required HTTP operations.
- Modify `backend/app/services/experiment_records.py`: expose narrow existing view/edit checks and stop serializing legacy metadata attachments into the T1.6A UI contract.
- Modify `backend/app/services/daily_reports.py`: expose narrow existing view/edit checks and stop treating legacy metadata attachments as real files.
- Modify `backend/app/schemas/experiment_record.py` and `backend/app/schemas/daily_report.py`: remove legacy attachment write fields from active create/update contracts if they conflict with the unified API.
- Modify `backend/tests/test_attachments.py`: full attachment behavior and authorization suite.
- Modify `backend/tests/test_contract_smoke.py`: typed OpenAPI route assertions.

Frontend:

- Modify `frontend/src/types/attachment.ts`: canonical entity and DTO fields.
- Modify `frontend/src/api/endpoints.ts`: unified list/create/detail/download/delete endpoints.
- Replace `frontend/src/services/attachment.ts`: always-real API operations.
- Create `frontend/src/services/attachment.test.ts`: request contract tests.
- Create `frontend/src/components/attachments/AttachmentPanel.tsx`: reusable UI.
- Create `frontend/src/components/attachments/AttachmentPanel.test.tsx`: state, permission, and error tests.
- Create `frontend/src/components/attachments/index.ts`: public component export.
- Modify `frontend/src/auth/permissions.ts`: attachment-specific visibility helpers.
- Modify `frontend/src/auth/permissions.test.ts`: role/object attachment capability tests.
- Modify `frontend/src/pages/experiments/ExperimentDetailPage.tsx`: experiment integration.
- Modify `frontend/src/pages/dailyReports/DailyReportDetailPage.tsx`: daily-report integration.
- Modify `frontend/src/pages/samples/SampleDetailPage.tsx`: sample, task, and result integrations.
- Modify `frontend/src/services/experiment.ts` and `frontend/src/services/dailyReport.ts`: remove legacy/mock attachment list paths.
- Modify `frontend/src/api/adapters.ts` and tests if legacy attachment adaptation remains referenced.
- Modify `frontend/src/api/mock/db.ts` and `frontend/src/api/mock/server.ts`: remove T1.6A mock attachment data/handlers only.

Acceptance:

- Modify `scripts/verify-fullstack.ps1`: T1.6A multipart smoke.
- Create `docs/T1.6A_ATTACHMENTS.md`: final operator/developer documentation.

### Task 1: Lock the database contract and configuration

**Files:**

- Modify: `backend/app/core/config.py`
- Modify: `backend/app/models/business.py`
- Create: `backend/alembic/versions/202606250003_complete_t1_6a_attachments.py`
- Test: `backend/tests/test_data_model.py`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write failing model/config tests**

Add assertions that `Attachment` exposes:

```python
{
    "id",
    "entity_type",
    "entity_id",
    "project_id",
    "original_filename",
    "storage_key",
    "content_type",
    "file_size",
    "checksum_sha256",
    "storage_backend",
    "uploaded_by",
    "uploaded_at",
    "deleted_at",
}
```

Add settings assertions:

```python
assert settings.attachment_max_size_bytes == 20 * 1024 * 1024
assert settings.attachment_storage_backend == "local"
assert settings.attachment_storage_root
assert "exe" in settings.attachment_blocked_extension_set
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_data_model.py tests/test_attachments.py -q
```

Expected: failure because the canonical fields/settings do not exist.

- [ ] **Step 3: Implement the model and settings**

Use these settings names:

```python
attachment_storage_root: str = "storage/attachments"
attachment_storage_backend: str = "local"
attachment_max_size_bytes: int = 20 * 1024 * 1024
attachment_allowed_extensions: str = "jpg,jpeg,png,pdf,txt,csv,xlsx,xls,docx,doc"
attachment_blocked_extensions: str = "exe,bat,cmd,ps1,sh,js,mjs,cjs,html,htm"
attachment_blocked_mime_types: str = (
    "application/x-msdownload,application/x-executable,"
    "application/x-sh,text/x-shellscript,text/html,"
    "application/javascript,text/javascript"
)
```

Validate `attachment_storage_backend == "local"` at runtime. Add normalized set properties for allowed extensions, blocked extensions, and blocked MIME types.

Define the canonical model fields and indexes:

```python
project_id = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=False)
original_filename = mapped_column(String(255), nullable=False)
content_type = mapped_column(String(120), nullable=False)
file_size = mapped_column(BIGINT_ID, nullable=False)
checksum_sha256 = mapped_column(String(64), nullable=False)
storage_backend = mapped_column(String(20), nullable=False, default="local", server_default="local")
deleted_at = mapped_column(DateTime(timezone=True), nullable=True)
```

Keep `entity_type`, `entity_id`, `storage_key`, `uploaded_by`, and `uploaded_at`.

- [ ] **Step 4: Add the migration**

Create revision `202606250003` with `down_revision = "202606250002"`.

Migration order:

1. delete baseline `attachment` rows because their public `daily_log` entity is outside T1.6A;
2. rename `file_name` to `original_filename`;
3. rename `sha256` to `checksum_sha256`;
4. rename `content_type_detected` to `content_type`;
5. drop legacy `file_type`, `thumbnail_key`, `upload_status`, and `preview_status`;
6. add `project_id`, `storage_backend`, and `deleted_at`;
7. make canonical columns non-null;
8. add `idx_attachment_project` and an active entity index.

The downgrade restores the legacy column shape without attempting to reconstruct deleted baseline rows.

- [ ] **Step 5: Run migration and tests to verify GREEN**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_data_model.py tests/test_attachments.py -q
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Expected: model/config tests pass and Alembic reaches `202606250003`.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/core/config.py backend/app/models/business.py backend/alembic/versions/202606250003_complete_t1_6a_attachments.py backend/tests/test_data_model.py backend/tests/test_attachments.py
git commit -m "feat(backend): add T1.6A attachment schema"
```

### Task 2: Implement safe local storage

**Files:**

- Replace: `backend/app/services/storage.py`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write failing storage tests**

Cover:

```python
def test_local_storage_generates_unique_opaque_keys(tmp_path): ...
def test_local_storage_rejects_key_outside_root(tmp_path): ...
def test_local_storage_round_trip_does_not_expose_real_path(tmp_path): ...
```

Assert two saves of `report.pdf` produce different keys and both resolve under `tmp_path`, while keys such as `../secret` are rejected.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_attachments.py -k "local_storage" -q
```

Expected: failure because current storage calls MinIO.

- [ ] **Step 3: Implement the protocol and local adapter**

Define:

```python
class AttachmentStorage(Protocol):
    def save(self, content: bytes, suffix: str) -> str: ...
    def read(self, storage_key: str) -> bytes: ...
    def exists(self, storage_key: str) -> bool: ...
    def delete(self, storage_key: str) -> None: ...
```

`LocalAttachmentStorage` must:

- resolve a configured root to an absolute path;
- generate `<uuid-prefix>/<uuid><safe-suffix>`;
- create parent directories;
- use exclusive creation (`xb`) to prevent overwrite;
- resolve and verify every key remains under root;
- return only the relative POSIX-style storage key.

Expose a factory:

```python
def get_attachment_storage() -> AttachmentStorage:
    return LocalAttachmentStorage(settings.attachment_storage_root)
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the same targeted tests and expect all selected tests to pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/storage.py backend/tests/test_attachments.py
git commit -m "feat(backend): add safe local attachment storage"
```

### Task 3: Build the five-entity resolver and permission matrix

**Files:**

- Create: `backend/app/services/attachment_entities.py`
- Modify: `backend/app/services/experiment_records.py`
- Modify: `backend/app/services/daily_reports.py`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write failing resolver tests**

Create fixtures for two projects, manager, director, assigned operator, other-project operator, experiment record, daily reports with zero/one/two projects, sample, task, and result.

Test each mapping:

```python
assert resolve_attachment_entity(..., "test_task", task.id).project_id == project.id
assert resolve_attachment_entity(..., "test_result", result.id).project_id == project.id
```

Test the exact daily-report upload error:

```python
assert response.status_code == 400
assert response.json()["message"] == "Daily report attachments require exactly one linked project."
```

Test:

- admin global action;
- director read but upload/delete denied;
- manager only managed project;
- operator experiment participation;
- operator assigned task/result;
- operator unauthorized object hidden;
- terminal object edit denial.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_attachments.py -k "resolver or permission or daily_report" -q
```

Expected: failure because no unified resolver exists.

- [ ] **Step 3: Implement resolver types and actions**

Define:

```python
AttachmentEntityType = Literal["experiment", "daily_report", "sample", "test_task", "test_result"]
AttachmentAction = Literal["read", "upload", "delete"]

@dataclass(frozen=True)
class ResolvedAttachmentEntity:
    entity_type: AttachmentEntityType
    entity_id: int
    project_id: int
    object: object
    editable: bool
```

Implement one dispatcher with private resolver functions. Reuse existing service functions:

- experiment: `get_record_or_404`, `ensure_can_view_record`, `ensure_can_edit_record`;
- daily report: `get_report_or_404`, `ensure_can_view_report`, `ensure_can_modify_report`;
- sample/task/result: `get_sample`, `get_task`, `get_result`, and existing view/edit rules.

Use narrow new helpers where T1.5 currently has no reusable upload/editability predicate:

```python
ensure_can_upload_sample_attachment(...)
ensure_can_upload_task_attachment(...)
ensure_can_upload_result_attachment(...)
```

Do not change T1.5 state transitions.

- [ ] **Step 4: Run tests and verify GREEN**

Run the targeted resolver/permission tests and expect all to pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/attachment_entities.py backend/app/services/experiment_records.py backend/app/services/daily_reports.py backend/app/services/testing.py backend/tests/test_attachments.py
git commit -m "feat(backend): resolve attachment entities and permissions"
```

### Task 4: Implement upload security and attachment lifecycle service

**Files:**

- Replace: `backend/app/schemas/attachment.py`
- Replace: `backend/app/services/attachments.py`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write failing lifecycle/security tests**

Add tests for:

- success with SHA-256 and `storage_backend == "local"`;
- list filters by exact public entity pair;
- detail;
- download bytes and sanitized filename;
- soft delete and subsequent 404;
- 20 MB configurable limit returning 413;
- blocked extension;
- blocked declared MIME;
- HTML content disguised as `.txt`;
- traversal/absolute/control-character filename rejection;
- repeated original filename never overwrites;
- stored project mismatch denied;
- operator may delete only their own upload.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_attachments.py -k "upload or download or delete or traversal or dangerous or oversized" -q
```

Expected: failures against the old daily-log-only implementation.

- [ ] **Step 3: Define typed schemas**

Use a string enum:

```python
class AttachmentEntityType(StrEnum):
    experiment = "experiment"
    daily_report = "daily_report"
    sample = "sample"
    test_task = "test_task"
    test_result = "test_result"
```

Define `AttachmentRead` with canonical fields and `AttachmentDeleteResult`:

```python
class AttachmentDeleteResult(BaseModel):
    id: int
    deleted: bool = True
```

Define aliases:

```python
AttachmentResponse = ApiResponse[AttachmentRead]
AttachmentListResponse = ApiResponse[list[AttachmentRead]]
AttachmentDeleteResponse = ApiResponse[AttachmentDeleteResult]
```

- [ ] **Step 4: Implement validation**

Implement:

```python
sanitize_original_filename(filename: str) -> str
detect_content_type(filename: str, content: bytes) -> str
validate_upload(filename: str, declared_type: str | None, content: bytes) -> ValidatedUpload
```

Rules:

- reject path separators, drive/absolute path forms, `..`, and control characters;
- enforce allow-list and deny-list;
- detect PDF/PNG/JPEG/ZIP/HTML/script/plain families;
- reject dangerous or contradictory declared/detected types;
- compute `hashlib.sha256(content).hexdigest()`.

- [ ] **Step 5: Implement service orchestration**

Service sequence for upload:

1. validate entity enum;
2. resolve with action `upload`;
3. read and validate bytes;
4. save bytes;
5. insert attachment with resolver project ID;
6. if database commit fails, best-effort delete the just-written object;
7. return persisted model.

For list/detail/download/delete:

- filter `deleted_at.is_(None)`;
- re-resolve business object;
- verify `attachment.project_id == resolved.project_id`;
- return 404 for deleted records;
- mark `deleted_at = datetime.now(UTC)` without physical deletion.

- [ ] **Step 6: Run tests and verify GREEN**

Run the full attachment test module:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_attachments.py -q
```

Expected: all attachment tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/schemas/attachment.py backend/app/services/attachments.py backend/tests/test_attachments.py
git commit -m "feat(backend): implement attachment lifecycle and security"
```

### Task 5: Expose the typed unified API and OpenAPI contract

**Files:**

- Replace: `backend/app/api/attachments.py`
- Modify: `backend/tests/test_contract_smoke.py`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write failing API/OpenAPI tests**

Assert paths and verbs:

```python
paths = app.openapi()["paths"]
assert "post" in paths["/api/attachments"]
assert "get" in paths["/api/attachments"]
assert "get" in paths["/api/attachments/{attachment_id}"]
assert "get" in paths["/api/attachments/{attachment_id}/download"]
assert "delete" in paths["/api/attachments/{attachment_id}"]
assert "/api/attachments/upload" not in paths
```

Assert JSON operations have response schemas referencing explicit DTOs rather than an untyped object.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/test_contract_smoke.py tests/test_attachments.py -q
```

Expected: old `/upload` route and bare `dict` responses fail assertions.

- [ ] **Step 3: Implement thin API routes**

Use:

```python
@router.post("", response_model=AttachmentResponse, status_code=201)
@router.get("", response_model=AttachmentListResponse)
@router.get("/{attachment_id}", response_model=AttachmentResponse)
@router.get("/{attachment_id}/download", response_class=Response)
@router.delete("/{attachment_id}", response_model=AttachmentDeleteResponse)
```

Download sets:

```python
Content-Disposition: attachment; filename*=UTF-8''<quoted-safe-name>
X-Content-Type-Options: nosniff
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the same command and expect all selected tests to pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/attachments.py backend/tests/test_contract_smoke.py backend/tests/test_attachments.py
git commit -m "feat(api): expose unified attachment endpoints"
```

### Task 6: Replace the frontend mock service with the real API

**Files:**

- Modify: `frontend/src/types/attachment.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Replace: `frontend/src/services/attachment.ts`
- Create: `frontend/src/services/attachment.test.ts`
- Modify: `frontend/src/api/mock/db.ts`
- Modify: `frontend/src/api/mock/server.ts`
- Modify: `frontend/src/services/experiment.ts`
- Modify: `frontend/src/services/dailyReport.ts`
- Modify: `frontend/src/api/adapters.ts`
- Test: `frontend/src/api/adapters.test.ts`

- [ ] **Step 1: Write failing service tests**

Mock `httpClient` and assert:

```typescript
await listAttachments('sample', 12)
// GET /attachments with params { entity_type: 'sample', entity_id: 12 }

await uploadAttachment('test_task', 15, file, onProgress)
// POST /attachments with FormData

await downloadAttachment(8)
// GET /attachments/8/download with responseType: 'blob'

await deleteAttachment(8)
// DELETE /attachments/8
```

Assert the browser download helper uses the response `Content-Disposition` filename and revokes the object URL.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
npm.cmd run test -- src/services/attachment.test.ts
```

Expected: failures because the service still calls mock handlers and has no download.

- [ ] **Step 3: Implement canonical types and endpoints**

Use:

```typescript
export type AttachmentEntity =
  | 'experiment'
  | 'daily_report'
  | 'sample'
  | 'test_task'
  | 'test_result'
```

Canonical fields match backend DTO names exactly.

Endpoints:

```typescript
attachments: {
  root: '/attachments',
  detail: (id) => `/attachments/${id}`,
  download: (id) => `/attachments/${id}/download`,
}
```

- [ ] **Step 4: Implement always-real service**

Use `httpClient` for blob/header access and `request<T>` for JSON operations. Do not branch on `USE_MOCK`.

Normalize all failures with `normalizeApiError`. Provide upload progress percentage when Axios reports a total.

- [ ] **Step 5: Remove T1.6A mock paths**

Remove mock attachment fixtures and `mockServer.attachments`. Remove experiment/daily-report attachment list helpers that read embedded legacy metadata. Keep unrelated mock behavior unchanged.

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```powershell
npm.cmd run test -- src/services/attachment.test.ts src/api/adapters.test.ts
npm.cmd run typecheck
```

Expected: selected tests and typecheck pass.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/types/attachment.ts frontend/src/api/endpoints.ts frontend/src/services/attachment.ts frontend/src/services/attachment.test.ts frontend/src/api/mock/db.ts frontend/src/api/mock/server.ts frontend/src/services/experiment.ts frontend/src/services/dailyReport.ts frontend/src/api/adapters.ts frontend/src/api/adapters.test.ts
git commit -m "feat(frontend): connect real attachment service"
```

### Task 7: Build the reusable attachment panel and permission helpers

**Files:**

- Create: `frontend/src/components/attachments/AttachmentPanel.tsx`
- Create: `frontend/src/components/attachments/AttachmentPanel.test.tsx`
- Create: `frontend/src/components/attachments/index.ts`
- Modify: `frontend/src/auth/permissions.ts`
- Modify: `frontend/src/auth/permissions.test.ts`

- [ ] **Step 1: Write failing permission tests**

Define attachment capability helpers that accept explicit facts rather than duplicating backend lookups:

```typescript
canUploadAttachment(user, { entityType, projectId, editable, ownerId, assignedTo }, scope)
canDeleteAttachment(user, attachment, context, scope)
```

Test:

- director false for upload/delete;
- admin true;
- manager only managed project;
- operator only editable authorized context;
- operator delete requires own upload.

- [ ] **Step 2: Write failing component tests**

Test:

- initial loading and list;
- file type/20 MB hint;
- successful upload refresh and success message;
- backend 413 message;
- dangerous-type message;
- network error message;
- download failure message;
- soft delete refresh;
- upload/delete buttons hidden for director;
- buttons hidden when `canUpload`/`canDelete` are false.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
npm.cmd run test -- src/auth/permissions.test.ts src/components/attachments/AttachmentPanel.test.tsx
```

Expected: component/helpers are missing.

- [ ] **Step 4: Implement the component**

Props:

```typescript
interface AttachmentPanelProps {
  entityType: AttachmentEntity
  entityId: Id
  canUpload: boolean
  canDelete: (attachment: Attachment) => boolean
}
```

Use React Query keys:

```typescript
['attachments', entityType, entityId]
```

Use AntD `Upload`, `Table`, `Progress`/button loading, `Popconfirm`, and `Alert`/`Typography.Text`. Set `beforeUpload={() => false}` so the component controls the request. Show no success message until the service promise resolves.

- [ ] **Step 5: Run tests and verify GREEN**

Run the same test command and `npm.cmd run typecheck`.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/components/attachments frontend/src/auth/permissions.ts frontend/src/auth/permissions.test.ts
git commit -m "feat(frontend): add reusable attachment panel"
```

### Task 8: Integrate all five public entity types

**Files:**

- Modify: `frontend/src/pages/experiments/ExperimentDetailPage.tsx`
- Modify: `frontend/src/pages/dailyReports/DailyReportDetailPage.tsx`
- Modify: `frontend/src/pages/samples/SampleDetailPage.tsx`
- Test: add focused page/integration tests under matching page folders or extend existing service tests.

- [ ] **Step 1: Write failing integration assertions**

Render representative pages and assert:

- experiment passes `entityType="experiment"`;
- daily report passes `entityType="daily_report"`;
- sample passes `entityType="sample"`;
- task row exposes `entityType="test_task"` with task ID;
- result area exposes `entityType="test_result"` only when a result ID exists.

Assert director has no upload/delete controls.

- [ ] **Step 2: Run tests and verify RED**

Run the new focused tests. Expected: current pages contain mock/metadata tables and no unified panel.

- [ ] **Step 3: Integrate experiment and daily report**

Replace the legacy attachment tabs/tables and informational mock alerts with `AttachmentPanel`.

Derive:

- project ID and manager scope from loaded entity;
- editable state from current record/report status;
- operator ownership/participation facts from loaded DTO.

- [ ] **Step 4: Integrate sample, task, and result**

Add a sample attachment tab/card. In each task row, provide an expandable or modal attachment panel for the task and, when `result_id` exists, a separate result attachment panel.

Keep task/result state transitions and forms unchanged.

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```powershell
npm.cmd run test
npm.cmd run typecheck
```

Expected: all frontend tests and typecheck pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/pages/experiments/ExperimentDetailPage.tsx frontend/src/pages/dailyReports/DailyReportDetailPage.tsx frontend/src/pages/samples/SampleDetailPage.tsx frontend/src
git commit -m "feat(frontend): integrate attachments across LIMS records"
```

### Task 9: Extend full-stack smoke and write T1.6A documentation

**Files:**

- Modify: `scripts/verify-fullstack.ps1`
- Create: `docs/T1.6A_ATTACHMENTS.md`
- Modify: `backend/scripts/seed_demo.py` only if deterministic cross-project smoke data is missing.

- [ ] **Step 1: Add a failing/unfinished T1.6A smoke block**

Add helpers for multipart upload and expected HTTP failure without changing existing JSON helper behavior.

Smoke sequence:

1. log in manager, director, and a user outside the sample project;
2. choose/create a manager-owned sample;
3. upload a small `.txt` or `.pdf`;
4. list and find returned ID;
5. download and compare bytes;
6. director upload must fail 403;
7. cross-project direct metadata/download must fail 404/403;
8. manager deletes;
9. download after deletion must fail 404.

Keep operational output ASCII.

- [ ] **Step 2: Write documentation**

Document:

- canonical DTO;
- entity mapping;
- APIs;
- exact permission matrix;
- daily-report unique-project rule and error;
- file limits and blocked types;
- `ATTACHMENT_STORAGE_ROOT`, `ATTACHMENT_MAX_SIZE_BYTES`, allowed/blocked settings;
- local storage key behavior;
- future storage protocol extension point;
- limitations/technical debt listed in the approved design.

- [ ] **Step 3: Run script syntax/static checks**

Run:

```powershell
[void][scriptblock]::Create((Get-Content -Raw .\scripts\verify-fullstack.ps1))
git diff --check
```

Expected: no parse or whitespace errors.

- [ ] **Step 4: Commit**

```powershell
git add scripts/verify-fullstack.ps1 docs/T1.6A_ATTACHMENTS.md backend/scripts/seed_demo.py
git commit -m "docs: add T1.6A attachment acceptance"
```

### Task 10: Full verification, browser acceptance, and final commit

**Files:**

- Any files required by defects discovered during verification, with a failing regression test before each fix.

- [ ] **Step 1: Backend static and migration verification**

Run in order:

```powershell
Set-Location backend
$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m pytest -q
```

Record exact exit codes, pass count, and warnings.

- [ ] **Step 2: Frontend verification**

Run in order:

```powershell
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

Record exact results.

- [ ] **Step 3: Full-stack verification**

With database/backend running:

```powershell
Set-Location ..
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-fullstack.ps1
```

Require the existing T1.5 flow and new T1.6A flow both to pass.

- [ ] **Step 4: Browser acceptance**

Run the real frontend/backend and verify:

- manager uploads/lists/downloads/deletes sample attachment;
- experiment and single-project daily-report panels operate;
- assigned operator can use task/result attachments;
- director sees list/download only;
- oversized/blocked type error is explicit;
- deleted download fails;
- no page exposes a real server path.

Capture screenshots or precise route/account/action evidence. If browser tooling is unavailable, report browser acceptance as not executed rather than inferring success.

- [ ] **Step 5: Requirement audit**

Check every numbered requirement in the user objective against:

- migration/model;
- resolver code and tests;
- API/OpenAPI;
- frontend integrations;
- backend/frontend test output;
- full-stack smoke;
- browser evidence;
- documentation.

Fix any gap with a failing regression test first.

- [ ] **Step 6: Final repository checks**

Run:

```powershell
git diff --check
git status --short
git log -5 --oneline
```

If verification fixes remain uncommitted:

```powershell
git add <intended-files>
git commit -m "feat(fullstack): complete T1.6A real attachments"
```

Confirm the final worktree is clean and capture `git rev-parse HEAD`.

- [ ] **Step 7: Final report and stop**

Report:

1. modified files;
2. APIs;
3. migration;
4. contract/mapping;
5. permission matrix;
6. storage configuration;
7. security limits;
8. test commands/results;
9. `verify-fullstack.ps1` result;
10. browser acceptance;
11. risks/technical debt;
12. git status;
13. final commit hash.

Stop after T1.6A. Do not begin T1.6B.
