from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.health_check import HealthCheck, CheckResult
from app.models.notification import AlertRule
from app.services.checker.base import execute_check

router = APIRouter(prefix="/checks", tags=["checks"])


@router.get("")
def list_checks(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    checks = session.exec(select(HealthCheck).where(HealthCheck.company_id == company_id)).all()
    result = []
    for c in checks:
        last = session.exec(select(CheckResult).where(CheckResult.check_id == c.id).order_by(CheckResult.checked_at.desc()).limit(1)).first()
        d = {"id": c.id, "name": c.name, "check_type": c.check_type, "target": c.target, "interval_sec": c.interval_sec, "timeout_sec": c.timeout_sec, "server_id": c.server_id, "router_id": c.router_id, "use_ssh": getattr(c, "use_ssh", False), "active": c.active, "last_checked_at": c.last_checked_at, "last_status": last.status if last else None, "last_message": last.message if last else None}
        result.append(d)
    return result


@router.post("")
def create_check(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    check = HealthCheck(company_id=company_id, **{k: data.get(k) for k in [
        "name", "check_type", "target", "interval_sec", "timeout_sec", "expected_status",
        "server_id", "router_id", "use_ssh", "active"
    ] if data.get(k) is not None})
    check.interval_sec = check.interval_sec or 60
    check.timeout_sec = check.timeout_sec or 10
    session.add(check)
    session.commit()
    session.refresh(check)
    return check


@router.get("/{check_id}")
def get_check(
    check_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    check = session.get(HealthCheck, check_id)
    if not check or check.company_id != company_id:
        raise HTTPException(404)
    return check


@router.put("/{check_id}")
def update_check(
    check_id: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    check = session.get(HealthCheck, check_id)
    if not check or check.company_id != company_id:
        raise HTTPException(404)
    for k in ["name", "check_type", "target", "interval_sec", "timeout_sec", "expected_status", "server_id", "router_id", "use_ssh", "active"]:
        if k in data:
            setattr(check, k, data[k])
    session.add(check)
    session.commit()
    session.refresh(check)
    return check


@router.delete("/{check_id}")
def delete_check(
    check_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    check = session.get(HealthCheck, check_id)
    if not check or check.company_id != company_id:
        raise HTTPException(404)
    for r in session.exec(select(CheckResult).where(CheckResult.check_id == check_id)).all():
        session.delete(r)
    for ar in session.exec(select(AlertRule).where(AlertRule.check_id == check_id)).all():
        session.delete(ar)
    session.delete(check)
    session.commit()
    return {"ok": True}


@router.get("/{check_id}/results")
def get_results(
    check_id: int,
    limit: int = 50,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    check = session.get(HealthCheck, check_id)
    if not check or check.company_id != company_id:
        raise HTTPException(404)
    return session.exec(
        select(CheckResult).where(CheckResult.check_id == check_id).order_by(CheckResult.checked_at.desc()).limit(limit)
    ).all()


@router.post("/{check_id}/run")
def run_check_now(
    check_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    check = session.get(HealthCheck, check_id)
    if not check or check.company_id != company_id:
        raise HTTPException(404)
    execute_check(check, session)
    session.refresh(check)
    last = session.exec(select(CheckResult).where(CheckResult.check_id == check_id).order_by(CheckResult.checked_at.desc()).limit(1)).first()
    return {"check": check, "result": last}
