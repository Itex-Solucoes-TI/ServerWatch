from sqlmodel import Session, select
from app.database import engine
from app.models.health_check import HealthCheck, CheckResult
from datetime import datetime, timedelta


def run_due_checks():
    with Session(engine) as session:
        checks = session.exec(select(HealthCheck).where(HealthCheck.active == True)).all()
        for check in checks:
            due = (
                check.last_checked_at is None or
                datetime.utcnow() >= check.last_checked_at + timedelta(seconds=check.interval_sec)
            )
            if due:
                execute_check(check, session)


def execute_check(check: HealthCheck, session: Session):
    from app.services.checker import url_checker, port_checker, db_checker, telnet_checker, ping_checker, ssh_checker
    from app.models.server import Server

    if getattr(check, "use_ssh", False) and check.server_id:
        server = session.get(Server, check.server_id)
        if server and server.ssh_host and server.ssh_user:
            result = ssh_checker.check(check, server)
        else:
            fn = {"URL": url_checker.check, "PORT": port_checker.check, "DATABASE": db_checker.check,
                  "TELNET": telnet_checker.check, "PING": ping_checker.check}.get(check.check_type)
            result = fn(check) if fn else None
    else:
        from app.services.checker import snmp_checker
        checker_map = {
            "URL": url_checker.check,
            "PORT": port_checker.check,
            "DATABASE": db_checker.check,
            "TELNET": telnet_checker.check,
            "PING": ping_checker.check,
            "SNMP": snmp_checker.check,
        }
        fn = checker_map.get(check.check_type)
        result = fn(check) if fn else None
    if not result:
        return
    check.last_checked_at = datetime.utcnow()
    session.add(result)
    session.add(check)
    session.commit()
    try:
        from app.services.notification_service import evaluate_alerts
        evaluate_alerts(check, result, session)
    except Exception:
        pass
    try:
        from app.services.ws_manager import broadcast_check_update
        broadcast_check_update(check, result)
    except Exception:
        pass
