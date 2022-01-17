import logging

from apscheduler.job import Job
from flask import Flask
from flask_apscheduler import APScheduler
from typing import List

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self, app: Flask):
        self.app = app
        # Initialize Flask APScheduler
        self.scheduler = APScheduler()
        self.scheduler.init_app(self.app)

    def list_jobs(self) -> List[Job]:
        return self.scheduler.get_jobs()

    def remove_jobs(self):
        jobs = self.list_jobs()
        num_jobs = len(jobs)
        logger.info(f"Removing {num_jobs} jobs from the scheduler.")
        self.scheduler.remove_all_jobs()

    def delete_job(self, job_to_delete: str):
        try:
            self.scheduler.remove_job(id=job_to_delete)
            return None
        except Exception as error:
            logger.error(f"Unable to delete job {job_to_delete}: {error}")
            return error

    def start(self):
        logger.info("Starting task scheduler...")
        try:
            self.scheduler.start()
        except Exception as error:
            logger.error(f"Error starting task scheduler: {error}")


def job_definitions(scheduler: APScheduler):
    """Contains definitions for scheduled jobs

    https://apscheduler.readthedocs.io/en/3.x/index.html
    """

    # Job Definitions
    # scheduler.add_job(
    #    id="my_job",
    #    func=myfunc,
    #    args=["foobar", "foobaz"],
    #    trigger="interval",
    #    name="Weekly Job Doing XYZ",
    #    days=7,
    #    replace_existing=True,
    # )
