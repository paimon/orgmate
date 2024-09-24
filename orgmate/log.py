from dataclasses import dataclass
from datetime import datetime

from orgmate.state import State


class Log:
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
        item = Log.Item(state, datetime.now())
        self.items.append(item)
