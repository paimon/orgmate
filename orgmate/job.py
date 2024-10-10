class Job:
    def __init__(self, task, time, cmd, period):
        self.task = task
        self.time = time
        self.cmd = cmd
        self.period = period

    def add(self):
        self.task.jobs.append(self)

    def remove(self):
        self.task.jobs.remove(self)
