from enum import Enum, auto


class Status(Enum):
    NEW = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DONE = auto()

    def __str__(self):
        return self.name.capitalize()

ESC_COLORS = {
    Status.NEW: '\033[37m',
    Status.ACTIVE: '\033[32m',
    Status.INACTIVE: '\033[34m',
    Status.DONE: '\033[90m',
}
