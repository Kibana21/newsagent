from __future__ import annotations
import logging
import subprocess
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("newsagent")


def run_daily() -> None:
    log.info("Starting daily pipeline")
    try:
        subprocess.run(
            [sys.executable, "-m", "src.main", "--days", "2", "--mode", "daily"],
            check=True,
        )
        log.info("Daily pipeline completed")
    except subprocess.CalledProcessError as e:
        log.exception("Daily pipeline failed: %s", e)
    except Exception:
        log.exception("Unexpected error during daily run")


def run_monthly() -> None:
    log.info("Starting monthly pipeline")
    try:
        subprocess.run(
            [sys.executable, "-m", "src.main", "--mode", "monthly"],
            check=True,
        )
        log.info("Monthly pipeline completed")
    except Exception:
        log.exception("Monthly pipeline failed")


def main() -> None:
    sched = BlockingScheduler(timezone="Asia/Singapore")
    sched.add_job(run_daily, CronTrigger(hour=8, minute=0), id="daily", name="Daily digest")
    sched.add_job(run_monthly, CronTrigger(day=1, hour=9, minute=0), id="monthly", name="Monthly digest")

    for job in sched.get_jobs():
        log.info("Scheduled %s (next run: %s)", job.name, job.next_run_time)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down scheduler")


if __name__ == "__main__":
    main()
