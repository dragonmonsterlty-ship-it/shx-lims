# T1.5 LIMS Main Chain Design

## Goal

Deliver the real API workflow: sample registration -> test task assignment -> result draft/submission -> manager approval or rejection, without entering T1.6.

## Scope and compatibility

- Keep the existing canonical roles: `admin`, `director`, `project_manager`, `operator`.
- T1.5 capability mapping:
  - `admin`: global management and review.
  - `project_manager`: manage and review projects they lead.
  - `operator`: researcher/analyst behavior; read assigned project data, execute assigned tasks, edit and submit own results.
  - `director`: viewer behavior for T1.5; global read-only access.
- Keep physical table names `sample_test` and `result` for migration safety. They implement the public `TestTask` and `TestResult` contracts.
- Do not add attachment upload, object storage, audit-log workflows, inventory enhancements, AI, barcode/scan, or global search.

## Data contract

### Sample

Public fields: `id`, `project_id`, `sample_no`, `name`, `type`, `source`, `batch_no`, `amount`, `unit`, `storage_condition`, `status`, `created_by`, `created_at`, `updated_by`, `updated_at`.

Compatibility fields already used by the frontend remain available where useful: `sample_code`, `sample_type`, `priority`, `received_at`, `due_date`, `notes`, `is_deleted`.

Statuses: `registered`, `in_testing`, `pending_review`, `completed`, `cancelled`.

### TestMethod

Fields: `id`, `code`, `name`, `category`, `version`, `description`, `is_active`, audit fields.

Only `admin` may create, edit, activate, or deactivate methods. All authenticated roles may list active methods; administrators may include inactive methods.

### TestTask

Stored in `sample_test`. Public fields: `id`, `sample_id`, `method_id`, `assigned_to`, `status`, `priority`, `due_date`, `created_by`, `created_at`, `updated_by`, `updated_at`, plus sample/method display summaries.

Statuses: `pending -> in_progress -> completed`, and `pending|in_progress -> cancelled`. A task can reach `completed` only after its result is approved.

### TestResult

Stored in `result`. Public fields: `id`, `task_id`, `result_data`, `conclusion`, `status`, `submitted_by`, `submitted_at`, `reviewed_by`, `reviewed_at`, `review_comment`, audit fields.

Statuses: `draft -> submitted -> approved|rejected`; `rejected -> draft` happens when the assignee edits the rejected result. Re-submission then follows `draft -> submitted`.

## API

- Samples: `GET/POST /api/samples`, `GET/PATCH/DELETE /api/samples/{id}`, `POST /api/samples/{id}/status`.
- Methods: `GET/POST /api/test-methods`, `GET/PATCH /api/test-methods/{id}`, `POST /api/test-methods/{id}/activation`.
- Tasks: `GET/POST /api/test-tasks`, `GET /api/test-tasks/{id}`, `PATCH /api/test-tasks/{id}/assignee`, `POST /api/test-tasks/{id}/status`.
- Results: `GET/POST /api/test-results`, `GET/PATCH /api/test-results/{id}`, `POST /api/test-results/{id}/submit`, `POST /api/test-results/{id}/approve`, `POST /api/test-results/{id}/reject`.

All responses use the existing `{code,message,data}` envelope and paginated lists use `{items,total,page,page_size}`.

## Authorization and row filtering

- Project visibility is derived from existing project membership/lead rules.
- Managers can create/update samples and tasks only inside projects they lead.
- Operators can view samples in projects where they are members, but task/result execution is limited to tasks assigned to themselves.
- Review is limited to `admin` or the task sample's project manager. Reviewers cannot approve or reject their own submitted result unless they are `admin`.
- Cross-project object IDs return `404` for reads to avoid existence disclosure and `403` for prohibited writes where the object is already in an authorized parent context.
- Assignees must be active members of the sample's project.

## Frontend

- Replace T1.5 mock service paths with real API calls.
- Sample list supports create/edit/status actions and detail navigation.
- Sample detail contains task creation, reassignment, legal status changes, and result draft/submission actions.
- `/testing` becomes the submitted-result review queue with approve/reject; rejection comment is required.
- Keep AntD Pro work-area styling and avoid decorative elements inside data forms/tables.

## Verification

- Backend tests cover CRUD, state machines, role capabilities, invalid foreign keys, and cross-project denial.
- OpenAPI smoke asserts all T1.5 routes.
- Frontend runs Vitest, typecheck, lint, and build.
- `scripts/verify-fullstack.ps1` runs an authenticated T1.5 API chain.
- Browser acceptance uses `project_manager` and `analyst` demo accounts against the real backend.

