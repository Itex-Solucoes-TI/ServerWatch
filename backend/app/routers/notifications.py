from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.notification import NotificationChannel, AlertRule

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/channels")
def list_channels(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    return session.exec(select(NotificationChannel).where(NotificationChannel.company_id == company_id)).all()


@router.post("/channels")
def create_channel(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    ch = NotificationChannel(company_id=company_id, **{k: data.get(k) for k in ["name", "channel_type", "target", "active"] if data.get(k) is not None})
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return ch


@router.put("/channels/{ch_id}")
def update_channel(
    ch_id: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    ch = session.get(NotificationChannel, ch_id)
    if not ch or ch.company_id != company_id:
        raise HTTPException(404)
    for k in ["name", "channel_type", "target", "active"]:
        if k in data:
            setattr(ch, k, data[k])
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return ch


@router.get("/rules")
def list_rules(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    return session.exec(select(AlertRule).where(AlertRule.company_id == company_id)).all()


@router.post("/rules")
def create_rule(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    r = AlertRule(company_id=company_id, **{k: data.get(k) for k in ["check_id", "channel_id", "fail_threshold", "active"] if data.get(k) is not None})
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    r = session.get(AlertRule, rule_id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    for k in ["check_id", "channel_id", "fail_threshold", "active"]:
        if k in data:
            setattr(r, k, data[k])
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


@router.delete("/channels/{ch_id}")
def delete_channel(
    ch_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    ch = session.get(NotificationChannel, ch_id)
    if not ch or ch.company_id != company_id:
        raise HTTPException(404)
    for r in session.exec(select(AlertRule).where(AlertRule.channel_id == ch_id)).all():
        session.delete(r)
    session.delete(ch)
    session.commit()
    return {"ok": True}


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    r = session.get(AlertRule, rule_id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    session.delete(r)
    session.commit()
    return {"ok": True}
