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
    def __init__(self, name, state=State.NEW):
        self.name = name
        self.parents = []
        self.subtasks = []
        self.state = state
        self.flow = Flow.PARALLEL

    def _prev_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = self.subtasks.index(self)
            if idx > 0:
                yield self.subtasks[idx - 1]

    def _next_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = self.subtasks.index(self)
            if idx < len(self.subtasks):
                yield self.subtasks[idx + 1]

    def _sibling_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.EXCLUSIVE:
                continue
            yield from (task for task in parent.subtasks if task is not self)

    def check_state(self, state):
        match state:
            case State.NEW:
                return (
                    all(task.state != State.DONE for task in self.parents) and
                    all(task.state == State.NEW for task in self.subtasks) and
                    all(task.state == State.NEW for task in self._next_tasks())
                )
            case State.ACTIVE:
                return (
                    all(task.state == State.ACTIVE for task in self.parents) and
                    all(task.state == State.DONE for task in self._prev_tasks()) and
                    all(task.state == State.NEW for task in self._next_tasks()) and
                    all(task.state != State.ACTIVE for task in self._sibling_tasks())
                )
            case State.INACTIVE:
                return (
                    all(task.state in (State.ACTIVE, State.INACTIVE) for task in self.parents) and
                    all(task.state != State.ACTIVE for task in self.subtasks) and
                    all(task.state == State.DONE for task in self._prev_tasks()) and
                    all(task.state == State.NEW for task in self._next_tasks())
                )
            case State.DONE:
                return (
                    all(task.state != State.NEW for task in self.parents) and
                    all(task.state == State.DONE for task in self.subtasks) and
                    all(task.state == State.DONE for task in self._prev_tasks())
                )

    def available_states(self):
        return {state for state in State if self.check_state(state)}

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
