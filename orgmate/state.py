from enum import Enum, auto


class State(Enum):
    NEW = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DONE = auto()

    def __str__(self):
        return self.name.capitalize()