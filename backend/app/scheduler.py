from apscheduler.schedulers.background import BackgroundScheduler


def cleanup_old_results():
    from sqlmodel import Session, delete
    from app.database import engine
    from app.models.health_check import CheckResult
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    with Session(engine) as session:
        session.exec(delete(CheckResult).where(CheckResult.checked_at < cutoff))
        session.commit()


def start_scheduler():
    from app.services.checker.base import run_due_checks
    from app.services.docker_service import sync_all_docker
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_due_checks, "interval", seconds=15, id="health_checks")
    scheduler.add_job(sync_all_docker, "interval", seconds=30, id="docker_sync")
    scheduler.add_job(cleanup_old_results, "cron", hour=0, id="cleanup")
    scheduler.start()
