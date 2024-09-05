from enum import Enum, auto


class State(Enum):
    NEW = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DONE = auto()


class Flow(Enum):
    PARALLEL = auto()
    EXCLUSIVE = auto()
    SEQUENTIAL = auto()


class StateInvariantViolation(Exception):
    pass


class Node:
    def __init__(self, parent, task, depth):
        self.parent = parent
        self.task = task
        self.depth = depth

    def insert(self, subtask):
        subtasks = self.parent.subtasks
        idx = subtasks.index(self.task)
        subtasks.insert(idx, subtask)

    def remove(self):
        self.parent.subtasks.remove(self.task)
        self.task.parents.remove(self.parent)


class Task:
    def __init__(self, name):
        self.name = name
        self.parents = []
        self.subtasks = []
        self.state = State.NEW
        self.flow = Flow.PARALLEL

    def check_state(self, state):
        match state:
            case State.NEW:
                return True
            case State.ACTIVE:
                return True
            case State.INACTIVE:
                return True
            case State.DONE:
                return True

    def available_states(self):
        return [state for state in State if self.check_state(state)]

    def add(self, subtask):
        self.subtasks.append(subtask)
        subtask.parents.append(self)

    def iter_subtasks(self, max_depth=None, depth=0):
        if max_depth is not None and max_depth <= depth:
            return
        for task in self.subtasks:
            yield Node(self, task, depth)
            yield from task.iter_subtasks(max_depth, depth + 1)

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value):
        if value not in self.available_states():
            raise StateInvariantViolation
        self.__state = value
