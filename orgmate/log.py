from dataclasses import dataclass
from datetime import datetime

from orgmate.status import Status


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

    def set_status(self, status):
        if self.items and self.get_status() == status:
            return
        timestamp = datetime.now() if self.current_time is None else self.current_time
        item = Log.Item(status, timestamp)
        self.items.append(item)
