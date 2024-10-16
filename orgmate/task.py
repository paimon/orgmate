from enum import Enum, auto

from orgmate.log import Log
from orgmate.state import State


class Flow(Enum):
    PARALLEL = auto()
    EXCLUSIVE = auto()
    SEQUENTIAL = auto()

    def __str__(self):
        return self.name.capitalize()


class StateInvariantViolation(Exception):
    pass


def aggregate_state(subtasks):
    if all(task.state == State.NEW for task in subtasks):
        return State.NEW
    if all(task.state == State.DONE for task in subtasks):
        return State.DONE
    if any(task.state == State.ACTIVE for task in subtasks):
        return State.ACTIVE
    return State.INACTIVE


class Node:
    def __init__(self, parent, task, depth):
        self.parent = parent
        self.task = task
        self.depth = depth

    def insert(self, subtask):
        idx = self.parent.subtasks.index(self.task)
        self.parent.add(subtask, idx)

    def remove(self):
        self.parent.subtasks.remove(self.task)
        self.task.parents.remove(self.parent)
        self.parent.update_state()


class Task:
    def __init__(self, name, state=State.NEW):
        self.name = name
        self.parents = []
        self.subtasks = []
        self.log = Log()
        self.jobs = []
        self.note = ''
        self.state = state
        self.flow = Flow.PARALLEL
        self.aggregate = True
        self.priority = 1
        self.weight = 1.0
        self.progress = 0

    def iter_prev_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = parent.subtasks.index(self)
            if idx > 0:
                yield parent.subtasks[idx - 1]

    def iter_next_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = parent.subtasks.index(self)
            if idx + 1 < len(parent.subtasks):
                yield parent.subtasks[idx + 1]

    def iter_sibling_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.EXCLUSIVE:
                continue
            yield from (task for task in parent.subtasks if task is not self)

    def iter_contexts(self):
        for parent in self.parents:
            if parent.aggregate:
                yield from parent.iter_contexts()
            else:
                yield parent

    def check_state(self, state):
        match state:
            case State.NEW:
                return (
                    all(task.state != State.DONE for task in self.iter_contexts()) and
                    all(task.state == State.NEW for task in self.subtasks) and
                    all(task.state == State.NEW for task in self.iter_next_tasks())
                )
            case State.ACTIVE:
                return (
                    all(task.state == State.ACTIVE for task in self.iter_contexts()) and
                    all(task.state == State.DONE for task in self.iter_prev_tasks()) and
                    all(task.state == State.NEW for task in self.iter_next_tasks()) and
                    all(task.state != State.ACTIVE for task in self.iter_sibling_tasks())
                )
            case State.INACTIVE:
                return (
                    all(task.state in (State.ACTIVE, State.INACTIVE) for task in self.iter_contexts()) and
                    all(task.state != State.ACTIVE for task in self.subtasks) and
                    all(task.state == State.DONE for task in self.iter_prev_tasks()) and
                    all(task.state == State.NEW for task in self.iter_next_tasks())
                )
            case State.DONE:
                return (
                    all(task.state != State.NEW for task in self.iter_contexts()) and
                    all(task.state == State.DONE for task in self.subtasks) and
                    all(task.state == State.DONE for task in self.iter_prev_tasks())
                )

    def get_available_states(self):
        return {state for state in State if self.check_state(state)}

    def get_next_states(self):
        if self.aggregate and self.subtasks:
            return set()
        next_states = set()
        match self.state:
            case State.NEW | State.INACTIVE:
                next_states = {State.ACTIVE}
            case State.ACTIVE:
                next_states = {State.INACTIVE, State.DONE}
        return next_states & self.get_available_states()

    def add(self, subtask, index=None):
        if index is None:
            self.subtasks.append(subtask)
            index = len(self.subtasks)
        else:
            self.subtasks.insert(index, subtask)
        subtask.parents.append(self)
        subtask.name = subtask.name.format(index)
        self.update_state()

    def iter_subtasks(self, max_depth=None, depth=0):
        if max_depth is not None and max_depth <= depth:
            return
        for task in self.subtasks:
            yield Node(self, task, depth)
            yield from task.iter_subtasks(max_depth, depth + 1)

    @property
    def state(self):
        return self.log.get_state()

    @state.setter
    def state(self, value):
        if value not in self.get_available_states():
            raise StateInvariantViolation
        self.log.update_state(value)
        for task in self.parents:
            task.update_state()

    @property
    def aggregate(self):
        return self._aggregate

    @aggregate.setter
    def aggregate(self, value):
        self._aggregate = value
        self.update_state()

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        self._weight = value if value >= 0 else None
        self.update_progress()

    def update_state(self):
        if self.aggregate and self.subtasks:
            self.state = aggregate_state(self.subtasks)
        self.update_progress()

    def _compute_progress(self):
        if self.state == State.DONE:
            return 100.0
        result, weight_sum = 0, 0
        for task in self.subtasks:
            progress = task.progress
            if task.weight is None or progress is None:
                return None
            result += task.weight * progress
            weight_sum += task.weight
        return result / weight_sum if weight_sum > 0 else 0

    def update_progress(self):
        self.progress = 100.0 * self._compute_progress()
