from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import re

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.business import RefStandard
from app.models.user import User
from app.schemas.ref_standard import RefStandardCreate, RefStandardUpdate
from app.services.audit_logs import record_audit
from app.services.module_access import ensure_module


REFSTD_MODULE = "refstd"
AUTO_CODE_PATTERN = re.compile(r"^RS-(\d{4})-(\d{4})$")
EDITABLE_FIELDS = (
    "name",
    "batch_no",
    "source",
    "spec",
    "assigned_value",
    "unit",
    "storage_condition",
    "expires_at",
    "notes",
)


def ensure_can_read_ref_standards(current_user: User) -> None:
    ensure_module(current_user, REFSTD_MODULE)


def ensure_can_write_ref_standards(current_user: User) -> None:
    ensure_can_read_ref_standards(current_user)
    if current_user.role == "viewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reference standard write permission required")


def current_year() -> int:
    return datetime.now(UTC).year


def _next_code(db: Session, year: int) -> str:
    value = db.execute(
        text(
            "INSERT INTO ref_standard_code_counter (year, last_value) VALUES (:year, 1) "
            "ON CONFLICT (year) DO UPDATE SET last_value = ref_standard_code_counter.last_value + 1 "
            "RETURNING last_value"
        ),
        {"year": year},
    ).scalar_one()
    if value > 9999:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reference standard annual code sequence exhausted")
    return f"RS-{year:04d}-{value:04d}"


def _reserve_manual_code(db: Session, code: str) -> None:
    match = AUTO_CODE_PATTERN.fullmatch(code)
    if match is None:
        return
    year, value = (int(part) for part in match.groups())
    db.execute(
        text(
            "INSERT INTO ref_standard_code_counter (year, last_value) VALUES (:year, :value) "
            "ON CONFLICT (year) DO UPDATE SET last_value = CASE "
            "WHEN ref_standard_code_counter.last_value < excluded.last_value THEN excluded.last_value "
            "ELSE ref_standard_code_counter.last_value END"
        ),
        {"year": year, "value": value},
    )


def _snapshot(standard: RefStandard) -> dict:
    return {
        "id": standard.id,
        "code": standard.code,
        "name": standard.name,
        "batch_no": standard.batch_no,
        "source": standard.source,
        "spec": standard.spec,
        "assigned_value": standard.assigned_value,
        "initial_amount": standard.initial_amount,
        "current_amount": standard.current_amount,
        "unit": standard.unit,
        "storage_condition": standard.storage_condition,
        "expires_at": standard.expires_at,
        "status": standard.status,
        "notes": standard.notes,
        "created_by": standard.created_by,
        "created_at": standard.created_at,
        "updated_at": standard.updated_at,
        "is_deleted": standard.is_deleted,
    }


def _duplicate_code(exc: IntegrityError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reference standard code already exists")


def get_ref_standard_or_404(db: Session, standard_id: int) -> RefStandard:
    standard = db.scalar(
        select(RefStandard).where(RefStandard.id == standard_id, RefStandard.is_deleted.is_(False))
    )
    if standard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference standard not found")
    return standard


def _paginate(db: Session, stmt: Select, page: int, page_size: int) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_ref_standards(
    db: Session,
    current_user: User,
    *,
    keyword: str | None = None,
    code: str | None = None,
    name: str | None = None,
    batch_no: str | None = None,
    source: str | None = None,
    status_filter: str | None = None,
    expiring_within_days: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    ensure_can_read_ref_standards(current_user)
    stmt = select(RefStandard).where(RefStandard.is_deleted.is_(False)).order_by(RefStandard.id.desc())
    if keyword:
        pattern = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(RefStandard.code.ilike(pattern), RefStandard.name.ilike(pattern), RefStandard.batch_no.ilike(pattern))
        )
    for value, column in ((code, RefStandard.code), (name, RefStandard.name), (batch_no, RefStandard.batch_no)):
        if value:
            stmt = stmt.where(column.ilike(f"%{value.strip()}%"))
    if source is not None:
        stmt = stmt.where(RefStandard.source == source)
    if status_filter is not None:
        stmt = stmt.where(RefStandard.status == status_filter)
    if expiring_within_days is not None:
        today = date.today()
        stmt = stmt.where(
            RefStandard.expires_at.is_not(None),
            RefStandard.expires_at >= today,
            RefStandard.expires_at <= today + timedelta(days=expiring_within_days),
        )
    return _paginate(db, stmt, page, page_size)


def create_ref_standard(db: Session, current_user: User, payload: RefStandardCreate) -> RefStandard:
    ensure_can_write_ref_standards(current_user)
    code = payload.code
    if code is None:
        code = _next_code(db, current_year())
    else:
        _reserve_manual_code(db, code)

    values = payload.model_dump(exclude={"code"})
    standard = RefStandard(
        **values,
        code=code,
        current_amount=Decimal(payload.initial_amount),
        status="in_stock",
        created_by=current_user.id,
    )
    db.add(standard)
    try:
        db.flush()
        record_audit(
            db,
            current_user,
            action="create",
            entity_type="ref_standard",
            entity_id=standard.id,
            after_data=_snapshot(standard),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_code(exc) from exc
    db.refresh(standard)
    return standard


def read_ref_standard(db: Session, current_user: User, standard_id: int) -> RefStandard:
    ensure_can_read_ref_standards(current_user)
    return get_ref_standard_or_404(db, standard_id)


def update_ref_standard(
    db: Session,
    current_user: User,
    standard_id: int,
    payload: RefStandardUpdate,
) -> RefStandard:
    ensure_can_write_ref_standards(current_user)
    standard = get_ref_standard_or_404(db, standard_id)
    if standard.status == "disposed":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Disposed reference standard cannot be edited")

    updates = payload.model_dump(exclude_unset=True)
    before: dict = {}
    after: dict = {}
    for field in EDITABLE_FIELDS:
        if field not in updates:
            continue
        old_value = getattr(standard, field)
        new_value = updates[field]
        if old_value != new_value:
            before[field] = old_value
            after[field] = new_value
            setattr(standard, field, new_value)

    if after:
        standard.updated_by = current_user.id
        standard.updated_at = datetime.now(UTC)
        record_audit(
            db,
            current_user,
            action="update",
            entity_type="ref_standard",
            entity_id=standard.id,
            before_data=before,
            after_data=after,
            metadata={"changed_fields": list(after)},
        )
        db.commit()
        db.refresh(standard)
    return standard


def dispose_ref_standard(db: Session, current_user: User, standard_id: int) -> RefStandard:
    ensure_can_write_ref_standards(current_user)
    standard = get_ref_standard_or_404(db, standard_id)
    if standard.status == "disposed":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reference standard is already disposed")

    before = {"status": standard.status}
    standard.status = "disposed"
    standard.updated_by = current_user.id
    standard.updated_at = datetime.now(UTC)
    record_audit(
        db,
        current_user,
        action="dispose",
        entity_type="ref_standard",
        entity_id=standard.id,
        before_data=before,
        after_data={"status": "disposed"},
        metadata={"changed_fields": ["status"]},
    )
    db.commit()
    db.refresh(standard)
    return standard
