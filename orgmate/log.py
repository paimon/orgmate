from dataclasses import dataclass
from datetime import datetime, timedelta

from orgmate.status import Status


FINISHED_TASK_TTL = timedelta(days=90)


class Log:
    current_time = None

    @dataclass
    class Item:
        status: Status
        timestamp: datetime

    def __init__(self):
        self.items = []
        self.set_status(Status.NEW)

    def get_status(self):
        return self.items[-1].status

    def get_duration(self):
        return datetime.now() - self.items[-1].timestamp

    def set_status(self, status):
        if self.items and self.get_status() == status:
            return
        timestamp = datetime.now() if self.current_time is None else self.current_time
        item = Log.Item(status, timestamp)
        self.items.append(item)

    def is_obsolete(self):
        return self.get_status() == Status.DONE and self.get_duration() > FINISHED_TASK_TTL
