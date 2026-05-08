"""Task Scheduler for Automated Daily Analysis

Schedules regular data sync, scoring, and report generation.
"""

import time
from datetime import datetime, time as datetime_time
from typing import Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import config
from src.logger import get_logger
from src.data.pipeline import DataPipeline
from src.analysis.scoring import MultiFactorScorer
from src.llm.report_generator import ReportGenerator
from src.llm.llm_client import LLMClient

logger = get_logger(__name__)


class ScheduledTask:
    """Base class for scheduled tasks"""

    def __init__(self, name: str):
        """Initialize task

        Args:
            name: Task name
        """
        self.name = name
        self.last_run: Optional[datetime] = None
        self.last_status: str = "pending"
        self.last_error: Optional[str] = None

    def run(self):
        """Execute task - must be implemented by subclass"""
        raise NotImplementedError


class DataSyncTask(ScheduledTask):
    """Task for synchronizing data from Tushare"""

    def __init__(self):
        super().__init__("DataSync")

    def run(self):
        """Execute data sync"""
        try:
            logger.info("Starting scheduled data sync...")
            with DataPipeline() as pipeline:
                results = pipeline.full_sync()
            self.last_run = datetime.now()
            self.last_status = "success"
            logger.info(f"Data sync completed: {results['status']}")
        except Exception as e:
            self.last_run = datetime.now()
            self.last_status = "error"
            self.last_error = str(e)
            logger.error(f"Data sync failed: {e}")


class ScoringTask(ScheduledTask):
    """Task for calculating stock scores"""

    def __init__(self):
        super().__init__("Scoring")
        self.last_scores = []

    def run(self):
        """Execute stock scoring"""
        try:
            logger.info("Starting scheduled stock scoring...")
            scorer = MultiFactorScorer()
            scores = scorer.score_top_stocks(limit=100, min_score=50.0)
            self.last_run = datetime.now()
            self.last_status = "success"
            self.last_scores = scores
            logger.info(f"Stock scoring completed: {len(scores)} stocks scored")
        except Exception as e:
            self.last_run = datetime.now()
            self.last_status = "error"
            self.last_error = str(e)
            logger.error(f"Stock scoring failed: {e}")


class ReportGenerationTask(ScheduledTask):
    """Task for generating daily reports"""

    def __init__(self, report_generator: Optional[ReportGenerator] = None):
        super().__init__("ReportGeneration")
        self.report_generator = report_generator or ReportGenerator()
        self.last_report: Optional[str] = None

    def run(self, scores=None):
        """Execute report generation

        Args:
            scores: List of StockScore objects (if None, will score first)
        """
        try:
            logger.info("Starting scheduled report generation...")

            # Score stocks if not provided
            if scores is None:
                scorer = MultiFactorScorer()
                scores = scorer.score_top_stocks(limit=50, min_score=60.0)

            if not scores:
                logger.warning("No scores available for report generation")
                self.last_status = "skipped"
                return

            # Generate report
            report = self.report_generator.generate_daily_summary(scores)
            self.last_run = datetime.now()
            self.last_status = "success"
            self.last_report = report
            logger.info("Report generation completed")

        except Exception as e:
            self.last_run = datetime.now()
            self.last_status = "error"
            self.last_error = str(e)
            logger.error(f"Report generation failed: {e}")


class TaskScheduler:
    """Manages scheduled tasks"""

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self.tasks = {}
        self._initialize_tasks()
        logger.info("TaskScheduler initialized")

    def _initialize_tasks(self):
        """Initialize all tasks"""
        self.tasks["data_sync"] = DataSyncTask()
        self.tasks["scoring"] = ScoringTask()
        self.tasks["report_generation"] = ReportGenerationTask()

    def schedule_daily_routine(
        self,
        sync_time: str = "09:30",
        score_time: str = "09:35",
        report_time: str = "09:40",
    ):
        """Schedule daily routine tasks

        Args:
            sync_time: Time to sync data (HH:MM format)
            score_time: Time to score stocks (HH:MM format)
            report_time: Time to generate reports (HH:MM format)
        """
        sync_hour, sync_minute = map(int, sync_time.split(":"))
        score_hour, score_minute = map(int, score_time.split(":"))
        report_hour, report_minute = map(int, report_time.split(":"))

        # Schedule data sync (weekdays only)
        self.scheduler.add_job(
            self.tasks["data_sync"].run,
            CronTrigger(
                day_of_week="mon-fri",
                hour=sync_hour,
                minute=sync_minute,
            ),
            id="daily_sync",
            name="Daily Data Sync",
        )
        logger.info(f"Scheduled daily data sync at {sync_time}")

        # Schedule stock scoring (weekdays only)
        self.scheduler.add_job(
            self.tasks["scoring"].run,
            CronTrigger(
                day_of_week="mon-fri",
                hour=score_hour,
                minute=score_minute,
            ),
            id="daily_scoring",
            name="Daily Stock Scoring",
        )
        logger.info(f"Scheduled daily stock scoring at {score_time}")

        # Schedule report generation (weekdays only)
        # Pass scoring task's results to report task
        def generate_report_with_scores():
            scores = self.tasks["scoring"].last_scores
            self.tasks["report_generation"].run(scores=scores)

        self.scheduler.add_job(
            generate_report_with_scores,
            CronTrigger(
                day_of_week="mon-fri",
                hour=report_hour,
                minute=report_minute,
            ),
            id="daily_report",
            name="Daily Report Generation",
        )
        logger.info(f"Scheduled daily report generation at {report_time}")

    def schedule_periodic_task(
        self,
        task_name: str,
        interval_minutes: int = 30,
        immediately: bool = False,
    ):
        """Schedule periodic task

        Args:
            task_name: Name of the task (data_sync, scoring, report_generation)
            interval_minutes: Interval in minutes
            immediately: Whether to run immediately
        """
        if task_name not in self.tasks:
            logger.warning(f"Task {task_name} not found")
            return

        if immediately:
            logger.info(f"Running {task_name} immediately...")
            self.tasks[task_name].run()

        self.scheduler.add_job(
            self.tasks[task_name].run,
            "interval",
            minutes=interval_minutes,
            id=f"periodic_{task_name}",
            name=f"Periodic {task_name.replace('_', ' ')} every {interval_minutes}m",
        )
        logger.info(f"Scheduled periodic {task_name} every {interval_minutes} minutes")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("TaskScheduler started")
        else:
            logger.warning("TaskScheduler is already running")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("TaskScheduler stopped")
        else:
            logger.warning("TaskScheduler is not running")

    def pause(self):
        """Pause the scheduler"""
        self.scheduler.pause()
        logger.info("TaskScheduler paused")

    def resume(self):
        """Resume the scheduler"""
        self.scheduler.resume()
        logger.info("TaskScheduler resumed")

    def list_jobs(self) -> list:
        """List all scheduled jobs

        Returns:
            List of job information dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run_time": job.next_run_time,
                }
            )
        return jobs

    def get_task_status(self, task_name: str) -> dict:
        """Get task status

        Args:
            task_name: Task name

        Returns:
            Task status dictionary
        """
        if task_name not in self.tasks:
            return {"error": f"Task {task_name} not found"}

        task = self.tasks[task_name]
        return {
            "name": task.name,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_status": task.last_status,
            "last_error": task.last_error,
        }
