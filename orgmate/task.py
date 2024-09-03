from enum import Enum, auto


class State(Enum):
    NEW = auto()
    ACTIVE = auto()
    IDLE = auto()
    FINISHED = auto()


class Flow(Enum):
    PARALLEL = auto()
    EXCLUSIVE = auto()
    SEQUENTIAL = auto()


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


class Task:
    def __init__(self, name):
        self.name = name
        self.subtasks = []
        self.state = State.NEW
        self.flow = Flow.PARALLEL

    def add(self, subtask):
        self.subtasks.append(subtask)

    def iter_subtasks(self, max_depth=None, depth=0):
        if max_depth is not None and max_depth <= depth:
            return
        for task in self.subtasks:
            yield Node(self, task, depth)
            yield from task.iter_subtasks(max_depth, depth + 1)
