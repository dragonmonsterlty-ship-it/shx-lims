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
    DailyReportItem,
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
from app.schemas.daily_report import DailyReportCreate, DailyReportItemCreate, DailyReportReview  # noqa: E402
from app.schemas.experiment_record import ExperimentRecordCreate  # noqa: E402
from app.schemas.testing import SampleCreate, TestResultCreate, TestTaskCreate  # noqa: E402
from app.services import daily_reports as daily_report_service  # noqa: E402
from app.services import experiment_records as experiment_record_service  # noqa: E402
from app.services import testing as testing_service  # noqa: E402


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
    db.add(report)


def testing_workflow(db, project_item: Project, analyst: User, manager: User, admin: User) -> None:
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
    db.commit()

    pending_sample = db.query(Sample).filter(Sample.sample_code == "DEMO-SAMPLE-PENDING").one_or_none()
    if pending_sample is None:
        pending_data = testing_service.create_sample(
            db,
            manager,
            SampleCreate(
                project_id=project_item.id,
                sample_no="DEMO-SAMPLE-PENDING",
                name="待检测样品：稳定性留样",
                type="compound",
                source="MVP demo seed",
                batch_no="DEMO-BATCH-PENDING",
                amount=Decimal("10.0000"),
                unit="mg",
                storage_condition="2-8 C",
                notes="用于演示待处理检测任务。",
            ),
        )
        pending_sample = db.query(Sample).filter(Sample.id == pending_data["id"]).one()
    pending_task = (
        db.query(SampleTest)
        .filter(SampleTest.sample_id == pending_sample.id, SampleTest.test_method_id == method.id)
        .one_or_none()
    )
    if pending_task is None:
        testing_service.create_task(
            db,
            manager,
            TestTaskCreate(
                sample_id=pending_sample.id,
                method_id=method.id,
                assigned_to=analyst.id,
                priority="normal",
            ),
        )

    completed_sample = db.query(Sample).filter(Sample.sample_code == "DEMO-SAMPLE-COMPLETE").one_or_none()
    if completed_sample is not None:
        return
    completed_data = testing_service.create_sample(
        db,
        manager,
        SampleCreate(
            project_id=project_item.id,
            sample_no="DEMO-SAMPLE-COMPLETE",
            name="已完成样品：MVP 含量测定",
            type="compound",
            source="MVP demo seed",
            batch_no="DEMO-BATCH-COMPLETE",
            amount=Decimal("12.0000"),
            unit="mg",
            storage_condition="室温避光",
            notes="用于演示完整检测与审核闭环。",
        ),
    )
    task_data = testing_service.create_task(
        db,
        manager,
        TestTaskCreate(
            sample_id=completed_data["id"],
            method_id=method.id,
            assigned_to=analyst.id,
            priority="high",
        ),
    )
    testing_service.change_task_status(db, analyst, task_data["id"], "in_progress")
    result_data = testing_service.create_result(
        db,
        analyst,
        TestResultCreate(
            task_id=task_data["id"],
            result_data={"assay": 99.6, "unit": "%", "judgment": "pass"},
            conclusion="含量符合演示规格。",
        ),
    )
    testing_service.submit_result(db, analyst, result_data["id"])
    testing_service.approve_result(db, manager, result_data["id"], "演示审核通过")


def browser_workflow(
    db,
    first_project: Project,
    operator: User,
    analyst: User,
    manager: User,
    admin: User,
) -> None:
    draft_record = db.query(ExperimentRecord).filter(ExperimentRecord.code == "EXP-DEMO-A-DRAFT").one_or_none()
    if draft_record is None:
        draft_record = experiment_record_service.create_record(
            db,
            operator,
            ExperimentRecordCreate(
                project_id=first_project.id,
                code="EXP-DEMO-A-DRAFT",
                title="MVP Demo 草稿实验：样品前处理",
                record_type="analysis",
                owner_id=operator.id,
                participant_ids=[operator.id, analyst.id],
                experiment_date=date(2026, 6, 28),
                objective="建立可重复的样品前处理流程。",
                procedure="称量、溶解、定容并过滤。",
                result_summary="前处理已完成，等待仪器检测。",
                conclusion="流程可用于后续检测。",
                next_step="由 analyst 执行 HPLC 检测。",
                risk_note="演示数据，不用于正式报告。",
            ),
        )

    submitted = db.query(ExperimentRecord).filter(ExperimentRecord.code == "EXP-DEMO-A-SUBMITTED").one_or_none()
    if submitted is None:
        submitted = experiment_record_service.create_record(
            db,
            operator,
            ExperimentRecordCreate(
                project_id=first_project.id,
                code="EXP-DEMO-A-SUBMITTED",
                title="MVP Demo 已提交实验：方法确认",
                record_type="analysis",
                owner_id=operator.id,
                participant_ids=[operator.id],
                experiment_date=date(2026, 6, 27),
                objective="确认演示检测方法可执行。",
                procedure="按方法条件完成系统适用性与样品检测。",
                result_summary="系统适用性符合预期。",
                conclusion="方法满足本轮演示需要。",
                next_step="项目负责人复核结果。",
                risk_note="无阻塞风险。",
            ),
        )
        experiment_record_service.submit_record(db, operator, submitted.id)

    draft_report = (
        db.query(DailyReport)
        .filter(DailyReport.user_id == operator.id, DailyReport.summary == "MVP Demo 多事项日报")
        .one_or_none()
    )
    if draft_report is None:
        daily_report_service.create_report(
            db,
            operator,
            DailyReportCreate(
                report_date=date(2026, 6, 28),
                summary="MVP Demo 多事项日报",
                issues="暂无阻塞问题。",
                next_plan="完成检测并提交项目负责人审核。",
                items=[
                    DailyReportItemCreate(
                        project_id=first_project.id,
                        experiment_record_id=draft_record.id,
                        work_type="experiment",
                        content="完成样品前处理实验记录。",
                        progress_note="实验步骤已记录。",
                        hours_spent=Decimal("2.00"),
                        next_step="交接 analyst 检测。",
                    ),
                    DailyReportItemCreate(
                        project_id=first_project.id,
                        work_type="documentation",
                        content="整理方法与交接说明。",
                        progress_note="文档已更新。",
                        hours_spent=Decimal("1.00"),
                        next_step="等待项目负责人复核。",
                        sort_order=2,
                    ),
                ],
            ),
        )

    confirmed_report = (
        db.query(DailyReport)
        .filter(DailyReport.user_id == operator.id, DailyReport.summary == "MVP Demo 已确认日报")
        .one_or_none()
    )
    if confirmed_report is None:
        confirmed_report = daily_report_service.create_report(
            db,
            operator,
            DailyReportCreate(
                report_date=date(2026, 6, 27),
                summary="MVP Demo 已确认日报",
                next_plan="进入下一轮样品检测。",
                items=[
                    DailyReportItemCreate(
                        project_id=first_project.id,
                        experiment_record_id=submitted.id,
                        work_type="analysis",
                        content="完成方法确认实验并提交。",
                    )
                ],
            ),
        )
        daily_report_service.submit_report(db, operator, confirmed_report.id)
        daily_report_service.review_report(
            db,
            manager,
            confirmed_report.id,
            DailyReportReview(review_comment="演示日报确认通过"),
        )

    testing_workflow(db, first_project, analyst, manager, admin)


def seed_database(db) -> None:
    admin = user(db, "admin", "Demo Admin", "admin", "System")
    director = user(db, "director", "演示主管", "director", "Management")
    manager = user(db, "project_manager", "演示项目负责人", "project_manager", "Chemistry")
    deactivate_legacy_pm_account(db)
    researcher = user(db, "researcher", "Demo Researcher", "operator", "Chemistry")
    operator = user(db, "operator", "Demo Operator", "operator", "Lab")
    analyst = user(db, "analyst", "Demo Analyst", "operator", "Analytical")

    first_project = project(db, "DEMO-001", "MVP Demo Project A", manager, admin.id)
    second_project = project(db, "DEMO-002", "MVP Demo Project B", manager, admin.id)
    db.flush()

    member(db, first_project.id, manager.id, "manager", admin.id)
    member(db, first_project.id, researcher.id, "member", admin.id)
    member(db, first_project.id, operator.id, "member", admin.id)
    member(db, first_project.id, analyst.id, "member", admin.id)
    member(db, second_project.id, manager.id, "manager", admin.id)

    methanol = reagent(db, "Methanol", "67-56-1", "mL", Decimal("10.0000"), admin.id)
    acetonitrile = reagent(db, "Acetonitrile", "75-05-8", "mL", Decimal("10.0000"), admin.id)
    db.flush()
    lot_a = lot(db, methanol, "MEOH-DEMO-001", Decimal("50.0000"), "Cabinet A", admin.id)
    lot_b = lot(db, acetonitrile, "ACN-DEMO-001", Decimal("20.0000"), "Cabinet B", admin.id)
    db.flush()
    inventory_txn(db, lot_a.id, Decimal("50.0000"), Decimal("50.0000"), operator.id)
    inventory_txn(db, lot_b.id, Decimal("20.0000"), Decimal("20.0000"), operator.id)

    first_record = experiment_record(db, "EXP-DEMO-001", first_project.id, researcher, operator, lot_a, [operator.id])
    second_record = experiment_record(db, "EXP-DEMO-002", second_project.id, manager, manager, lot_b, [manager.id])
    db.flush()
    daily_report(db, researcher, first_project.id, first_record.id, "Demo daily report for assay project")
    daily_report(db, manager, second_project.id, second_record.id, "Demo daily report for formulation project")
    db.commit()
    browser_workflow(db, first_project, operator, analyst, manager, admin)


def main() -> None:
    db = SessionLocal()
    try:
        seed_database(db)
        print("Demo seed data ready. Users use password: password123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
