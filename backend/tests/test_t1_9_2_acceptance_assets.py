from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_verify_fullstack_contains_admin_audit_rc_smoke_contract():
    script = (ROOT / "scripts" / "verify-fullstack.ps1").read_text(encoding="utf-8")

    for marker in [
        "== T1.9.2 admin and audit RC smoke ==",
        "/admin/users",
        "/audit-logs?page=1&page_size=10",
        '"/audit-logs/entity/$($entity.Type)/$($entity.Id)"',
        "@{ Type = 'experiment'",
        "@{ Type = 'daily_report'",
        "@{ Type = 'sample'",
        "admin user list",
        "ordinary member audit list rejected",
        "cross-project entity timelines rejected",
    ]:
        assert marker in script


def test_real_api_verifier_covers_admin_audit_and_three_entity_timelines():
    script = (ROOT / "frontend" / "scripts" / "verify-real-api.mjs").read_text(encoding="utf-8")

    for marker in [
        "'/admin/users'",
        "'/audit-logs?page=1&page_size=10'",
        "'experiment', createdExperiment.id",
        "'daily_report', report.id",
        "'sample', sample.id",
        "`/audit-logs/entity/${entityType}/${entityId}`",
        "assertTimeline",
        "assertManagerAuditScope",
        "`${item.entity_type}:${item.entity_id}`",
        "`experiment:${crossExperiment.id}`",
        "`daily_report:${crossReport.id}`",
        "`sample:${crossSample.id}`",
    ]:
        assert marker in script


def test_fullstack_verifier_propagates_real_api_failure():
    script = (ROOT / "scripts" / "verify-fullstack.ps1").read_text(encoding="utf-8")

    assert "Assert-NativeExitCode 'npm run verify:api' $LASTEXITCODE" in script
