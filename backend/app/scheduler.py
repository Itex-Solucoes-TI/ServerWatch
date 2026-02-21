from apscheduler.schedulers.background import BackgroundScheduler


def cleanup_old_results():
    from sqlmodel import Session, delete
    from app.database import engine
    from app.models.health_check import CheckResult
    from app.models.snmp_metric import SnmpMetric
    from datetime import datetime, timedelta
    with Session(engine) as session:
        # Check results: mantém 30 dias
        cutoff = datetime.utcnow() - timedelta(days=30)
        session.exec(delete(CheckResult).where(CheckResult.checked_at < cutoff))
        # SNMP raw (coletados a cada 30s): mantém 7 dias
        snmp_cutoff = datetime.utcnow() - timedelta(days=7)
        session.exec(delete(SnmpMetric).where(SnmpMetric.collected_at < snmp_cutoff))
        session.commit()


def start_scheduler():
    from app.services.checker.base import run_due_checks
    from app.services.docker_service import sync_all_docker
    from app.services.snmp_service import run_snmp_collection
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_due_checks, "interval", seconds=15, id="health_checks")
    scheduler.add_job(sync_all_docker, "interval", seconds=30, id="docker_sync")
    scheduler.add_job(run_snmp_collection, "interval", seconds=30, id="snmp_collection")
    scheduler.add_job(cleanup_old_results, "cron", hour=0, id="cleanup")
    scheduler.start()
