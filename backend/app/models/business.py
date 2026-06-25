from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BIGINT_ID, Base


JSON_DATA = JSON().with_variant(JSONB(), "postgresql")


class AuditColumnsMixin:
    created_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class Project(AuditColumnsMixin, Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    project_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    project_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lead_user_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", default="active")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, server_default="normal", default="normal")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    recent_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    members = relationship("ProjectMember", back_populates="project")
    lead_user = relationship("User", foreign_keys=[lead_user_id])
    samples = relationship("Sample", back_populates="project")
    experiments = relationship("Experiment", back_populates="project")
    experiment_records = relationship("ExperimentRecord", back_populates="project")
    daily_logs = relationship("DailyLog", back_populates="project")
    daily_report_items = relationship("DailyReportItem", back_populates="project")

    __table_args__ = (
        Index("idx_project_code", "project_code"),
        Index("idx_project_status", "status"),
    )


class ProjectMember(AuditColumnsMixin, Base):
    __tablename__ = "project_member"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=False)
    role_in_project: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member", default="member")

    project = relationship("Project", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member_project_user"),)


class Sample(AuditColumnsMixin, Base):
    __tablename__ = "sample"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    sample_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    project_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=False)
    compound_name: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sample_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    structure_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_molfile: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, server_default="normal", default="normal")
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    project = relationship("Project", back_populates="samples")
    sample_tests = relationship("SampleTest", back_populates="sample")

    __table_args__ = (
        Index("idx_sample_status", "status"),
        Index("idx_sample_code", "sample_code"),
        Index("idx_sample_due_date", "due_date"),
        Index("idx_sample_project", "project_id"),
    )


class TestMethod(AuditColumnsMixin, Base):
    __tablename__ = "test_method"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    spec_lower: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    spec_upper: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    spec_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)

    sample_tests = relationship("SampleTest", back_populates="test_method")


class SampleTest(AuditColumnsMixin, Base):
    __tablename__ = "sample_test"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    sample_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("sample.id"), nullable=False)
    test_method_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("test_method.id"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, server_default="normal", default="normal")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    sample = relationship("Sample", back_populates="sample_tests")
    test_method = relationship("TestMethod", back_populates="sample_tests")
    result = relationship("Result", back_populates="sample_test", uselist=False)
    assignee = relationship("User", foreign_keys=[assigned_to])

    __table_args__ = (UniqueConstraint("sample_id", "test_method_id", name="uq_sample_test_sample_method"),)


class Result(AuditColumnsMixin, Base):
    __tablename__ = "result"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    sample_test_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("sample_test.id"), unique=True, nullable=False)
    result_data: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON_DATA, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    submitted_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    judgment: Mapped[str | None] = mapped_column(String(10), nullable=True)
    entered_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending", default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    sample_test = relationship("SampleTest", back_populates="result")


class Experiment(AuditColumnsMixin, Base):
    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=False)
    experiment_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    experiment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    author_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_sample_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("sample.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    project = relationship("Project", back_populates="experiments")
    materials = relationship("ExperimentMaterial", back_populates="experiment")
    related_sample = relationship("Sample")

    __table_args__ = (
        Index("idx_experiment_no", "experiment_no"),
        Index("idx_experiment_project", "project_id"),
        Index("idx_experiment_status", "status"),
    )


class ExperimentMaterial(AuditColumnsMixin, Base):
    __tablename__ = "experiment_material"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("experiment.id"), nullable=False)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reagent_lot_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("reagent_lot.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    experiment = relationship("Experiment", back_populates="materials")
    reagent_lot = relationship("ReagentLot")


class ExperimentRecord(AuditColumnsMixin, Base):
    __tablename__ = "experiment_record"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    creator_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    experiment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    project = relationship("Project", back_populates="experiment_records")
    creator = relationship("User", foreign_keys=[creator_id])
    owner = relationship("User", foreign_keys=[owner_id])
    reagent_usages = relationship("ExperimentReagentUsage", back_populates="experiment_record", cascade="all, delete-orphan")
    participants = relationship("ExperimentRecordParticipant", back_populates="experiment_record", cascade="all, delete-orphan")
    attachments = relationship("ExperimentAttachment", back_populates="experiment_record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_experiment_record_project", "project_id"),
        Index("idx_experiment_record_status", "status"),
        Index("idx_experiment_record_type", "record_type"),
        Index("idx_experiment_record_date", "experiment_date"),
    )


class ExperimentReagentUsage(AuditColumnsMixin, Base):
    __tablename__ = "experiment_reagent_usage"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    experiment_record_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("experiment_record.id"), nullable=False)
    reagent_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("reagent.id"), nullable=True)
    lot_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("reagent_lot.id"), nullable=True)
    reagent_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lot_code_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(200), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    outbound_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending", default="pending")
    shortage_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    dispensed_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    dispensed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment_record = relationship("ExperimentRecord", back_populates="reagent_usages")
    reagent = relationship("Reagent")
    lot = relationship("ReagentLot")

    __table_args__ = (Index("idx_experiment_reagent_usage_record", "experiment_record_id"),)


class ExperimentRecordParticipant(Base):
    __tablename__ = "experiment_record_participant"

    experiment_record_id: Mapped[int] = mapped_column(
        BIGINT_ID, ForeignKey("experiment_record.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), primary_key=True)

    experiment_record = relationship("ExperimentRecord", back_populates="participants")
    user = relationship("User")


class ExperimentAttachment(AuditColumnsMixin, Base):
    __tablename__ = "experiment_attachment"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    experiment_record_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("experiment_record.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BIGINT_ID, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)

    experiment_record = relationship("ExperimentRecord", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (Index("idx_experiment_attachment_record", "experiment_record_id"),)


class DailyReport(AuditColumnsMixin, Base):
    __tablename__ = "daily_report"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    items = relationship("DailyReportItem", back_populates="daily_report", cascade="all, delete-orphan")
    attachments = relationship("DailyReportAttachment", back_populates="daily_report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_daily_report_user_date", "user_id", "report_date"),
        Index("idx_daily_report_status", "status"),
        Index("idx_daily_report_date", "report_date"),
    )


class DailyReportItem(AuditColumnsMixin, Base):
    __tablename__ = "daily_report_item"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    daily_report_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("daily_report.id"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=True)
    experiment_record_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("experiment_record.id"), nullable=True)
    work_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    progress_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours_spent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    problem_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)

    daily_report = relationship("DailyReport", back_populates="items")
    project = relationship("Project", back_populates="daily_report_items")
    experiment_record = relationship("ExperimentRecord")

    __table_args__ = (
        Index("idx_daily_report_item_report", "daily_report_id"),
        Index("idx_daily_report_item_project", "project_id"),
        Index("idx_daily_report_item_experiment_record", "experiment_record_id"),
    )


class DailyReportAttachment(AuditColumnsMixin, Base):
    __tablename__ = "daily_report_attachment"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    daily_report_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("daily_report.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BIGINT_ID, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)

    daily_report = relationship("DailyReport", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (Index("idx_daily_report_attachment_report", "daily_report_id"),)


class Reagent(AuditColumnsMixin, Base):
    __tablename__ = "reagent"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cas_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    catalog_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    min_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)

    lots = relationship("ReagentLot", back_populates="reagent")


class ReagentLot(AuditColumnsMixin, Base):
    __tablename__ = "reagent_lot"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    reagent_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("reagent.id"), nullable=False)
    lot_no: Mapped[str] = mapped_column(String(80), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0", default=0)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    controlled_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="in_stock", default="in_stock")

    reagent = relationship("Reagent", back_populates="lots")
    inventory_txns = relationship("InventoryTxn", back_populates="reagent_lot")

    __table_args__ = (UniqueConstraint("reagent_id", "lot_no", name="uq_reagent_lot_reagent_lot_no"),)


class InventoryTxn(Base):
    __tablename__ = "inventory_txn"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    reagent_lot_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("reagent_lot.id"), nullable=False)
    txn_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    operator_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual", default="manual")
    source_id: Mapped[int | None] = mapped_column(BIGINT_ID, nullable=True)
    shortage_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    txn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    reagent_lot = relationship("ReagentLot", back_populates="inventory_txns")
    operator = relationship("User", foreign_keys=[operator_id])


class DailyLog(AuditColumnsMixin, Base):
    __tablename__ = "daily_log"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("project.id"), nullable=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_sample_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("sample.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    reviewed_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)

    project = relationship("Project", back_populates="daily_logs")
    related_sample = relationship("Sample")

    __table_args__ = (
        Index("idx_daily_log_user_date", "user_id", "log_date"),
        Index("idx_daily_log_project", "project_id"),
    )


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_type_detected: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BIGINT_ID, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="uploaded", default="uploaded")
    preview_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    uploader = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (Index("idx_attachment_entity", "entity_type", "entity_id"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(60), nullable=False)
    record_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    business_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    changed_by: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("user.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    changed_fields: Mapped[dict | None] = mapped_column(JSON_DATA, nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON_DATA, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON_DATA, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)

    actor = relationship("User", foreign_keys=[changed_by])
