from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.deps import get_session, get_company_id, require_role
from app.services.backup_service import export_company_backup, import_company_backup
from app.services.audit_service import log

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("")
def export_backup(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    try:
        data = export_company_backup(session, company_id)
        log(session, user.id, "EXPORT", company_id, "BACKUP", None)
        session.commit()
        return data
    except ValueError as e:
        raise HTTPException(404, str(e))




@router.post("")
def import_backup(
    data: dict,
    replace: bool = False,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    try:
        if data.get("version") != 1:
            raise HTTPException(400, "Versão de backup não suportada")
        import_company_backup(session, company_id, data, replace=replace)
        log(session, user.id, "IMPORT", company_id, "BACKUP", None)
        session.commit()
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))
