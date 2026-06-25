from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.business import (  # noqa: E402
    DailyReport,
    DailyReportAttachment,
    DailyReportItem,
    ExperimentAttachment,
    ExperimentRecord,
    ExperimentReagentUsage,
    InventoryTxn,
    Project,
    ProjectMember,
    Reagent,
    ReagentLot,
    Sample,
    SampleTest,
    TestMethod,
    ExperimentRecordParticipant,
)
from app.models.user import User  # noqa: E402


DEFAULT_PASSWORD = "password123"


def user(db, username: str, full_name: str, role: str, department: str) -> User:
    existing = db.query(User).filter(User.username == username).one_or_none()
    if existing is not None:
        existing.full_name = full_name
        existing.email = f"{username}@example.local"
        existing.password_hash = hash_password(DEFAULT_PASSWORD)
        existing.role = role
        existing.department = department
        existing.is_active = True
        existing.must_change_password = False
        return existing
    created = User(
        username=username,
        full_name=full_name,
        email=f"{username}@example.local",
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=role,
        department=department,
        is_active=True,
        must_change_password=False,
    )
    db.add(created)
    db.flush()
    return created


def deactivate_legacy_pm_account(db) -> None:
    legacy_pm = db.query(User).filter(User.username == "pm").one_or_none()
    if legacy_pm is not None:
        legacy_pm.is_active = False


def project(db, code: str, name: str, lead: User, created_by: int) -> Project:
    existing = db.query(Project).filter(Project.project_code == code).one_or_none()
    if existing is not None:
        existing.name = name
        existing.lead_user_id = lead.id
        existing.status = "active"
        existing.is_deleted = False
        return existing
    created = Project(
        project_code=code,
        name=name,
        project_type="assay",
        lead_user_id=lead.id,
        status="active",
        priority="normal",
        description="Demo project for frontend integration",
        current_stage="MVP validation",
        progress=35,
        created_by=created_by,
    )
    db.add(created)
    db.flush()
    return created


def member(db, project_id: int, user_id: int, role_in_project: str, created_by: int) -> None:
    existing = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id).one_or_none()
    if existing is not None:
        existing.role_in_project = role_in_project
        return
    db.add(ProjectMember(project_id=project_id, user_id=user_id, role_in_project=role_in_project, created_by=created_by))


def reagent(db, name: str, cas_no: str, unit: str, min_stock: Decimal, created_by: int) -> Reagent:
    existing = db.query(Reagent).filter(Reagent.name == name, Reagent.cas_no == cas_no).first()
    if existing is not None:
        existing.is_active = True
        existing.default_unit = unit
        existing.min_stock = min_stock
        return existing
    created = Reagent(
        name=name,
        cas_no=cas_no,
        catalog_no=f"{name[:3].upper()}-DEMO",
        manufacturer="Demo Vendor",
        grade="HPLC",
        default_unit=unit,
        min_stock=min_stock,
        created_by=created_by,
    )
    db.add(created)
    db.flush()
    return created


def lot(db, item: Reagent, lot_no: str, quantity: Decimal, location: str, created_by: int) -> ReagentLot:
    existing = db.query(ReagentLot).filter(ReagentLot.reagent_id == item.id, ReagentLot.lot_no == lot_no).one_or_none()
    if existing is not None:
        existing.quantity = quantity
        existing.status = "in_stock" if quantity > 0 else "depleted"
        return existing
    created = ReagentLot(
        reagent_id=item.id,
        lot_no=lot_no,
        quantity=quantity,
        unit=item.default_unit,
        location=location,
        status="in_stock" if quantity > 0 else "depleted",
        created_by=created_by,
    )
    db.add(created)
    db.flush()
    return created


def inventory_txn(db, lot_id: int, quantity: Decimal, balance_after: Decimal, operator_id: int) -> None:
    exists = db.query(InventoryTxn).filter(InventoryTxn.reagent_lot_id == lot_id, InventoryTxn.reference == "demo seed").first()
    if exists is None:
        db.add(
            InventoryTxn(
                reagent_lot_id=lot_id,
                txn_type="in",
                quantity=quantity,
                balance_after=balance_after,
                reference="demo seed",
                operator_id=operator_id,
            )
        )


def experiment_record(
    db,
    code: str,
    project_id: int,
    creator: User,
    owner: User,
    lot_item: ReagentLot,
    participant_ids: list[int],
) -> ExperimentRecord:
    existing = db.query(ExperimentRecord).filter(ExperimentRecord.code == code).one_or_none()
    if existing is not None:
        existing.conclusion = "Continue follow-up work"
        existing.next_step = "Review and plan the next run"
        existing.risk_note = "Demo risk note"
        existing.participants = [ExperimentRecordParticipant(user_id=user_id) for user_id in participant_ids]
        return existing
    created = ExperimentRecord(
        project_id=project_id,
        code=code,
        title=f"{code} demo experiment",
        record_type="analysis",
        status="draft",
        creator_id=creator.id,
        owner_id=owner.id,
        experiment_date=date(2026, 6, 23),
        objective="Support frontend detail view",
        procedure="Prepare sample and run analytical method",
        result_summary="Demo result summary",
        conclusion="Continue follow-up work",
        next_step="Review and plan the next run",
        risk_note="Demo risk note",
        created_by=creator.id,
    )
    created.participants = [ExperimentRecordParticipant(user_id=user_id) for user_id in participant_ids]
    created.reagent_usages.append(
        ExperimentReagentUsage(
            reagent_id=lot_item.reagent_id,
            lot_id=lot_item.id,
            reagent_name_snapshot=lot_item.reagent.name,
            lot_code_snapshot=lot_item.lot_no,
            quantity=Decimal("1.0000"),
            unit=lot_item.unit,
            purpose="demo usage metadata",
            created_by=creator.id,
        )
    )
    created.attachments.append(
        ExperimentAttachment(
            file_name=f"{code}.pdf",
            file_type="pdf",
            file_size=1024,
            storage_key=f"demo/experiments/{code}.pdf",
            description="Demo attachment metadata only",
            uploaded_by=creator.id,
            created_by=creator.id,
        )
    )
    db.add(created)
    db.flush()
    return created


def daily_report(db, owner: User, project_id: int, record_id: int, summary: str) -> None:
    existing = db.query(DailyReport).filter(DailyReport.user_id == owner.id, DailyReport.summary == summary).one_or_none()
    if existing is not None:
        if len(existing.items) < 2:
            existing.items.append(
                DailyReportItem(
                    project_id=project_id,
                    work_type="documentation",
                    content="Updated experiment notes and handoff",
                    problem_note="No blocking issue",
                    next_step="Continue tomorrow",
                    sort_order=2,
                    created_by=owner.id,
                )
            )
        return
    report = DailyReport(
        user_id=owner.id,
        report_date=date(2026, 6, 23),
        status="draft",
        summary=summary,
        issues="No blocker",
        next_plan="Continue demo validation",
        created_by=owner.id,
    )
    report.items.append(
        DailyReportItem(
            project_id=project_id,
            experiment_record_id=record_id,
            work_type="analysis",
            content="Completed demo analytical work",
            progress_note="80%",
            hours_spent=Decimal("2.50"),
            next_step="Review data",
            created_by=owner.id,
        )
    )
    report.items.append(
        DailyReportItem(
            project_id=project_id,
            experiment_record_id=None,
            work_type="documentation",
            content="Updated experiment notes and handoff",
            problem_note="No blocking issue",
            next_step="Continue tomorrow",
            sort_order=2,
            created_by=owner.id,
        )
    )
    report.attachments.append(
        DailyReportAttachment(
            file_name="demo-chromatogram.pdf",
            file_type="pdf",
            file_size=2048,
            storage_key="demo/daily-reports/chromatogram.pdf",
            description="Demo daily report attachment metadata only",
            uploaded_by=owner.id,
            created_by=owner.id,
        )
    )
    db.add(report)


def testing_workflow(db, project_item: Project, analyst: User, admin: User) -> None:
    method = db.query(TestMethod).filter(TestMethod.code == "HPLC-DEMO-T15").one_or_none()
    if method is None:
        method = TestMethod(
            code="HPLC-DEMO-T15",
            name="Demo HPLC Assay",
            category="assay",
            version="1.0",
            description="T1.5 demo method",
            method="assay",
            is_active=True,
            created_by=admin.id,
        )
        db.add(method)
        db.flush()
    else:
        method.is_active = True

    sample = db.query(Sample).filter(Sample.sample_code == "DEMO-SAMPLE-T15").one_or_none()
    if sample is None:
        sample = Sample(
            sample_code="DEMO-SAMPLE-T15",
            project_id=project_item.id,
            compound_name="Demo compound",
            name="T1.5 demo assay sample",
            sample_type="compound",
            source="demo seed",
            batch_no="DEMO-BATCH-T15",
            amount=Decimal("10.0000"),
            unit="mg",
            storage_condition="2-8 C",
            status="in_testing",
            priority="normal",
            created_by=admin.id,
        )
        db.add(sample)
        db.flush()
    else:
        sample.is_deleted = False
        sample.project_id = project_item.id

    task = (
        db.query(SampleTest)
        .filter(SampleTest.sample_id == sample.id, SampleTest.test_method_id == method.id)
        .one_or_none()
    )
    if task is None:
        task = SampleTest(
            sample_id=sample.id,
            test_method_id=method.id,
            assigned_to=analyst.id,
            status="pending",
            priority="normal",
            created_by=admin.id,
        )
        db.add(task)
    else:
        task.assigned_to = analyst.id
        if task.result is None:
            task.status = "pending"
    if task.result is not None and task.result.status not in {"approved", "rejected", "submitted", "draft"}:
        task.result.status = "draft"


def seed_database(db) -> None:
    admin = user(db, "admin", "Demo Admin", "admin", "System")
    director = user(db, "director", "演示主管", "director", "Management")
    manager = user(db, "project_manager", "演示项目负责人", "project_manager", "Chemistry")
    deactivate_legacy_pm_account(db)
    researcher = user(db, "researcher", "Demo Researcher", "operator", "Chemistry")
    operator = user(db, "operator", "Demo Operator", "operator", "Lab")
    analyst = user(db, "analyst", "Demo Analyst", "operator", "Analytical")

    first_project = project(db, "DEMO-001", "Demo Assay Project", manager, admin.id)
    second_project = project(db, "DEMO-002", "Demo Formulation Project", manager, admin.id)
    db.flush()

    member(db, first_project.id, manager.id, "manager", admin.id)
    member(db, first_project.id, researcher.id, "member", admin.id)
    member(db, first_project.id, operator.id, "member", admin.id)
    member(db, first_project.id, analyst.id, "member", admin.id)
    member(db, second_project.id, manager.id, "manager", admin.id)
    member(db, second_project.id, researcher.id, "member", admin.id)
    member(db, second_project.id, operator.id, "member", admin.id)

    methanol = reagent(db, "Methanol", "67-56-1", "mL", Decimal("10.0000"), admin.id)
    acetonitrile = reagent(db, "Acetonitrile", "75-05-8", "mL", Decimal("10.0000"), admin.id)
    db.flush()
    lot_a = lot(db, methanol, "MEOH-DEMO-001", Decimal("50.0000"), "Cabinet A", admin.id)
    lot_b = lot(db, acetonitrile, "ACN-DEMO-001", Decimal("20.0000"), "Cabinet B", admin.id)
    db.flush()
    inventory_txn(db, lot_a.id, Decimal("50.0000"), Decimal("50.0000"), operator.id)
    inventory_txn(db, lot_b.id, Decimal("20.0000"), Decimal("20.0000"), operator.id)

    first_record = experiment_record(db, "EXP-DEMO-001", first_project.id, researcher, operator, lot_a, [operator.id])
    second_record = experiment_record(db, "EXP-DEMO-002", second_project.id, researcher, analyst, lot_b, [operator.id])
    db.flush()
    daily_report(db, researcher, first_project.id, first_record.id, "Demo daily report for assay project")
    daily_report(db, operator, second_project.id, second_record.id, "Demo daily report for formulation project")
    testing_workflow(db, first_project, analyst, admin)
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed_database(db)
        print("Demo seed data ready. Users use password: password123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
