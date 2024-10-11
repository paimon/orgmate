from dataclasses import dataclass
from datetime import datetime

from orgmate.state import State


class Log:
    current_time = None

    @dataclass
    class Item:
        state: State
        timestamp: datetime

    def __init__(self):
        self.items = []

    def get_state(self):
        return self.items[-1].state

    def update_state(self, state):
        if self.items and self.get_state() == state:
            return
        timestamp = datetime.now() if self.current_time is None else self.current_time
        item = Log.Item(state, timestamp)
        self.items.append(item)
