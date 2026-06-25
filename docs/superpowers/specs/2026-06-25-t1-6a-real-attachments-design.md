# T1.6A Real Attachments Design

## Goal

Deliver a real, locally stored attachment lifecycle for experiment records, daily reports, samples, test tasks, and test results:

`upload -> list/detail -> controlled download -> soft delete -> deleted download denied`

The work is limited to T1.6A. It does not add object storage, audit workflows, user management, inventory enhancements, AI, search, statistics, or broad T1.5 refactoring.

## Scope and compatibility

- Keep the canonical roles: `admin`, `director`, `project_manager`, `operator`.
- Keep the existing physical table names `sample_test` and `result`.
- Public attachment APIs expose only `test_task` and `test_result`; internal table names never appear in the attachment contract.
- Upgrade the existing generic `attachment` table and `/api/attachments` module.
- Do not use MinIO, S3, OSS, or another remote object store in T1.6A.
- Do not migrate legacy metadata from `experiment_attachment` or `daily_report_attachment`. Those tables remain for compatibility and are documented as technical debt.
- Remove T1.6A attachment UI dependence on mock attachment data without changing unrelated mock business modules.

## Public entity contract

The only accepted `entity_type` values are:

- `experiment`
- `daily_report`
- `sample`
- `test_task`
- `test_result`

Public-to-internal mapping:

| Public `entity_type` | Internal model/table |
|---|---|
| `experiment` | `ExperimentRecord` / `experiment_record` |
| `daily_report` | `DailyReport` / `daily_report` |
| `sample` | `Sample` / `sample` |
| `test_task` | `SampleTest` / `sample_test` |
| `test_result` | `Result` / `result` |

The attachment DTO contains:

- `id`
- `entity_type`
- `entity_id`
- `project_id`
- `original_filename`
- `storage_key`
- `content_type`
- `file_size`
- `checksum_sha256`
- `storage_backend`
- `uploaded_by`
- `uploaded_at`
- `deleted_at`

`storage_key` is an opaque logical key, not a server path. API responses never expose the configured storage root or a resolved filesystem path.

## Data model and migration

The existing `attachment` table is upgraded rather than replaced:

- add non-null `project_id` referencing `project.id`;
- rename or migrate legacy public-facing columns into:
  - `file_name` -> `original_filename`;
  - `file_type` / `content_type_detected` -> `content_type`;
  - `sha256` -> `checksum_sha256`;
- add non-null `storage_backend`, defaulting to `local`;
- add nullable `deleted_at`;
- keep `storage_key`, `file_size`, `uploaded_by`, and `uploaded_at`;
- add an index for active entity listing and an index for `project_id`;
- preserve existing rows where safely possible, but migration must not invent a project for legacy rows whose entity mapping cannot be resolved.

Because the current baseline attachment feature only enables `daily_log`, and `daily_log` is outside the T1.6A public contract, the migration may delete existing `attachment` rows before enforcing the new non-null contract. This repository has no accepted T1.6A production attachment data at the baseline commit.

## Entity resolver

A single resolver receives `entity_type`, `entity_id`, current user, and requested action. It returns a structured resolved entity containing:

- canonical public entity type;
- entity ID;
- resolved `project_id`;
- underlying business object;
- whether the object currently allows attachment editing.

The resolver performs object lookup and authorization together so an attacker cannot combine a valid ID with a forged `entity_type`.

Resolution rules:

- `experiment`: load `ExperimentRecord`; `project_id` comes directly from the record.
- `sample`: load `Sample`; `project_id` comes directly from the sample.
- `test_task`: load `SampleTest`; `project_id` comes from `task.sample.project_id`.
- `test_result`: load `Result`; `project_id` comes from `result.sample_test.sample.project_id`.
- `daily_report`: load `DailyReport`; collect distinct non-null project IDs from report items.

Daily-report upload has an explicit unique-project invariant:

1. one linked project: upload is allowed and attachment `project_id` is that project;
2. zero linked projects: upload returns HTTP 400;
3. multiple linked projects: upload returns HTTP 400.

The exact error detail is:

`Daily report attachments require exactly one linked project.`

This restriction applies only to daily-report attachment upload. Daily reports themselves continue to support zero or multiple projects. Item-level or user-level attachments for multi-project reports are outside T1.6A.

## Authorization

Every list, detail, download, upload, and delete operation re-resolves the target object and verifies that the stored attachment `project_id` matches the currently resolved project. A mismatch is denied and never silently repaired.

| Role | View/list/download | Upload | Delete |
|---|---|---|---|
| `admin` | global | global | global |
| `project_manager` | only managed project objects | only managed project objects | only managed project objects |
| `operator` | only business objects already visible under existing rules | only visible objects that remain editable | only own uploads on visible, editable objects |
| `director` | global read-only | denied | denied |

Entity-specific operator rules:

- `experiment`: reuse existing experiment visibility; upload/delete require existing edit permission and an editable record status.
- `daily_report`: only the report owner may upload/delete, and only while status is `draft` or `returned`.
- `sample`: reuse T1.5 project visibility for reads; upload/delete require project membership and a non-terminal sample.
- `test_task`: only the assigned operator may read/upload; upload/delete require a non-terminal task.
- `test_result`: only the assigned task operator may read/upload; upload/delete require result status `draft` or `rejected`.

For operators, deletion additionally requires `attachment.uploaded_by == current_user.id`.

Cross-project and unauthorized object access returns 404 where existing read rules hide resource existence. Explicit role prohibitions such as director upload/delete return 403.

## API

The unified API surface is:

- `POST /api/attachments`
  - multipart form fields: `entity_type`, `entity_id`, `file`;
  - returns HTTP 201 with a typed attachment response envelope.
- `GET /api/attachments?entity_type=&entity_id=`
  - both query parameters are required;
  - returns active attachments only, ordered by upload time/ID.
- `GET /api/attachments/{id}`
  - returns active attachment metadata.
- `GET /api/attachments/{id}/download`
  - returns a controlled backend response with sanitized `Content-Disposition`.
- `DELETE /api/attachments/{id}`
  - performs soft deletion and returns a typed deletion response.

The legacy `POST /api/attachments/upload` endpoint is removed. OpenAPI routes use explicit Pydantic DTOs rather than bare `dict` response models.

## Local storage

Define a storage protocol with operations equivalent to:

- `save(content, suffix) -> storage_key`
- `open(storage_key) -> file/stream`
- `delete(storage_key)` for future lifecycle maintenance

T1.6A supplies only `LocalAttachmentStorage`.

Configuration:

- `ATTACHMENT_STORAGE_ROOT`, default `backend/storage/attachments`;
- `ATTACHMENT_MAX_SIZE_BYTES`, default `20 * 1024 * 1024`;
- `ATTACHMENT_ALLOWED_EXTENSIONS`, configurable allow-list;
- `ATTACHMENT_STORAGE_BACKEND`, fixed/validated as `local`.

Storage keys use generated UUID material and optional safe suffixes in generated subdirectories. User-controlled names never become filesystem paths. Storage path resolution verifies the final path remains under the configured root.

Soft deletion does not immediately remove the physical file. This keeps metadata/file lifecycle reversible and avoids a database/file partial-failure window. Physical garbage collection is explicitly deferred.

## Upload security

- Stream/read with a hard configured maximum; reject oversized files with HTTP 413.
- Reject missing extensions.
- Reject dangerous extensions including at least:
  - `exe`, `bat`, `cmd`, `ps1`, `sh`, `js`, `html`, `htm`.
- Reject dangerous declared or detected MIME types including executable, shell/script, JavaScript, and HTML types.
- Sanitize the display filename:
  - strip directory components;
  - reject absolute paths and traversal intent;
  - remove control characters;
  - normalize empty/unsafe names to an error rather than inventing a misleading name.
- Detect basic MIME signatures for PDF, PNG, JPEG, ZIP-based office documents, and plain text/CSV.
- Compare the detected family, extension, and declared MIME. A dangerous or contradictory combination is rejected.
- Compute SHA-256 while processing the upload.
- Generate unique storage keys so repeated original names never overwrite another object.

## Backend component boundaries

- `models/business.py`: attachment persistence fields only.
- `schemas/attachment.py`: enum and typed request/response DTOs.
- `services/attachment_entities.py`: entity resolution and authorization.
- `services/storage.py`: local storage protocol and implementation only.
- `services/attachments.py`: upload/list/detail/download/delete orchestration and security validation.
- `api/attachments.py`: thin HTTP translation, multipart parsing, typed response models, and controlled download response.

Existing experiment, daily-report, and T1.5 services remain authoritative for their business access rules. Only narrow reusable permission helpers are extracted or exposed when necessary.

## Frontend design

Create a reusable `AttachmentPanel` component responsible for:

- loading and rendering the attachment list;
- selecting and uploading a file;
- upload loading/progress state;
- controlled download;
- soft-delete action with confirmation;
- explicit size/type guidance;
- clear messages for 413, forbidden type, permission denial, missing/deleted file, and network failure.

The attachment service always calls the real API, even if unrelated modules run in mock mode.

Integrations:

- experiment detail: `entity_type="experiment"`;
- daily-report detail: `entity_type="daily_report"`;
- sample detail: `entity_type="sample"`;
- each test-task row/detail area: `entity_type="test_task"`;
- each available result row/detail area: `entity_type="test_result"`.

The task and result integrations stay inside the existing sample-detail/testing workflow; no new broad business module or T1.6B page is introduced.

Button visibility:

- director never sees upload/delete controls;
- project manager controls are shown only for managed-project objects;
- operator controls are shown only when the frontend can establish object access/editability;
- backend authorization remains authoritative;
- no success message is shown until the backend request succeeds.

The component follows the existing AntD Pro work-area visual rules and adds no decorative UI.

## Testing

Backend tests use a temporary local storage directory and cover at least:

1. successful upload and typed metadata;
2. list by `entity_type` and `entity_id`;
3. successful controlled download;
4. soft delete followed by denied download;
5. oversized upload rejection;
6. dangerous extension/MIME rejection;
7. traversal filename rejection or sanitization;
8. cross-project entity and attachment denial;
9. director upload/delete denial;
10. unauthorized operator upload/download/delete denial;
11. sample/test-task/test-result permissions;
12. experiment/daily-report permissions;
13. daily report with zero or multiple projects rejected with the exact message;
14. storage-key uniqueness and non-disclosure of filesystem paths;
15. OpenAPI contains the five unified routes with typed schemas.

Frontend tests cover:

- service URLs, multipart payload, download, and delete;
- role-based control visibility;
- upload/list/delete refresh behavior;
- explicit error messages;
- the five required entity integrations.

Required frontend commands:

- `npm run typecheck`
- `npm run lint`
- `npm run test`
- `npm run build`

## Full-stack smoke and browser acceptance

Extend `scripts/verify-fullstack.ps1` without weakening the existing T1.5 smoke. T1.6A smoke performs:

1. manager uploads a file to a sample;
2. list contains the attachment;
3. download bytes match;
4. delete succeeds;
5. download after deletion fails;
6. director upload fails;
7. a user from another project cannot access the attachment directly.

The PowerShell script keeps ASCII operational strings for Windows PowerShell 5.1 compatibility.

Browser acceptance verifies the real backend UI for:

- experiment attachment;
- daily-report attachment on a single-project report;
- sample attachment;
- test-task attachment;
- test-result attachment;
- director read-only controls;
- a representative upload, download, delete, and error path.

## Documentation and technical debt

`docs/T1.6A_ATTACHMENTS.md` documents:

- public contract and internal mapping;
- API surface;
- permission matrix;
- size/type restrictions;
- local storage configuration;
- storage abstraction extension point;
- daily-report unique-project rule;
- known limitations and technical debt.

Known T1.6A limitations:

- local disk only;
- no antivirus or content-disarm scanning;
- no resumable/chunked upload;
- no deduplication despite SHA-256;
- no preview or thumbnail generation;
- no automatic physical-file garbage collection after soft delete;
- no migration of legacy experiment/daily-report metadata attachments;
- no multi-project daily-report attachment; future support requires item-level or user-level design.

## Completion boundary

T1.6A is complete only after migration, backend API, resolver, local storage, frontend integrations, automated tests, full-stack smoke, browser acceptance, documentation, clean git status, and final commit are all evidenced. Work stops at that point and does not enter T1.6B.
