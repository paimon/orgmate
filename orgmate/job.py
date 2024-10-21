from datetime import datetime
from heapq import heapify, heappush, heappop


class Job:
    _schedule = []

    @classmethod
    def init_schedule(cls, root):
        for node in root.iter_subtasks():
            cls._schedule.extend(node.task.jobs)
        heapify(cls._schedule)        

    @classmethod
    def iter_pending(cls):
        while cls._schedule and cls._schedule[0].time < datetime.now():
            job = heappop(cls._schedule)
            if not job.remove():
                continue
            yield job
            if job.period:
                job.time += job.period
                job.add()

    def __init__(self, task, time, cmd, period):
        self.task = task
        self.time = time
        self.cmd = cmd
        self.period = period

    def __lt__(self, other):
        return self.time < other.time

    def __repr__(self):
        return f'Job(task={self.task}, time={self.time}, cmd={self.cmd}, period={self.period})'

    def add(self):
        self.task.jobs.append(self)
        heappush(self._schedule, self)

    def remove(self):
        jobs = self.task.jobs
        if self in jobs:
            jobs.remove(self)
            return True
        return False
