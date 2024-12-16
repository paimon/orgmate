from enum import Enum, auto
from functools import cached_property

from orgmate.log import Log
from orgmate.status import Status
from orgmate.node import Node, NodeFilter


class Flow(Enum):
    PARALLEL = auto()
    EXCLUSIVE = auto()
    SEQUENTIAL = auto()

    def __str__(self):
        return self.name.capitalize()


def aggregate_status(subtasks):
    if all(task.status == Status.NEW for task in subtasks):
        return Status.NEW
    if all(task.status == Status.DONE for task in subtasks):
        return Status.DONE
    if any(task.status == Status.ACTIVE for task in subtasks):
        return Status.ACTIVE
    return Status.INACTIVE


class Task:
    PUBLIC_FIELDS = ['name', 'flow', 'status', 'priority', 'aggregate', 'weight']
    PUBLIC_RO_FIELDS = PUBLIC_FIELDS + ['progress']

    def __init__(self, name, context_mode=False):
        self.name = name
        self.parents = []
        self.subtasks = []
        self.log = Log()
        self.flow = Flow.SEQUENTIAL
        self.note = ''
        self.jobs = []
        if context_mode:
            self.aggregate = False
            self.priority = 0
        else:
            self.aggregate = True
            self.priority = 1
        self.weight = 1.0

    def __repr__(self):
        return f'Task(name={self.name}, status={self.status})'

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('progress', None)
        return state

    def iter_prev_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = parent.subtasks.index(self)
            if idx > 0:
                yield parent.subtasks[idx - 1]
            if parent.aggregate:
                yield from parent.iter_prev_tasks()

    def iter_next_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.SEQUENTIAL:
                continue
            idx = parent.subtasks.index(self)
            if idx + 1 < len(parent.subtasks):
                yield parent.subtasks[idx + 1]
            if parent.aggregate:
                yield from parent.iter_next_tasks()

    def iter_sibling_tasks(self):
        for parent in self.parents:
            if parent.flow != Flow.EXCLUSIVE:
                continue
            yield from (task for task in parent.subtasks if task is not self)
            if parent.aggregate:
                yield from parent.iter_sibling_tasks()

    def iter_contexts(self):
        for parent in self.parents:
            if parent.aggregate:
                yield from parent.iter_contexts()
            else:
                yield parent

    def _check_status(self, status):
        match status:
            case Status.NEW:
                return (
                    all(task.status != Status.DONE for task in self.iter_contexts()) and
                    all(task.status == Status.NEW for task in self.subtasks) and
                    all(task.status == Status.NEW for task in self.iter_next_tasks())
                )
            case Status.ACTIVE:
                return (
                    all(task.status == Status.ACTIVE for task in self.iter_contexts()) and
                    all(task.status == Status.DONE for task in self.iter_prev_tasks()) and
                    all(task.status == Status.NEW for task in self.iter_next_tasks()) and
                    all(task.status != Status.ACTIVE for task in self.iter_sibling_tasks())
                )
            case Status.INACTIVE:
                return (
                    all(task.status in (Status.ACTIVE, Status.INACTIVE) for task in self.iter_contexts()) and
                    all(task.status != Status.ACTIVE for task in self.subtasks) and
                    all(task.status == Status.DONE for task in self.iter_prev_tasks()) and
                    all(task.status == Status.NEW for task in self.iter_next_tasks())
                )
            case Status.DONE:
                return (
                    all(task.status != Status.NEW for task in self.iter_contexts()) and
                    all(task.status == Status.DONE for task in self.subtasks) and
                    all(task.status == Status.DONE for task in self.iter_prev_tasks())
                )

    def _check_flow(self, flow):
        match flow:
            case Flow.EXCLUSIVE:
                return sum(t.status == Status.ACTIVE for t in self.subtasks) <= 1
            case Flow.SEQUENTIAL:
                return (
                    sum(t.status == Status.ACTIVE or t.status == Status.INACTIVE for t in self.subtasks) <= 1 and
                    all(t1.status.value >= t2.status.value for t1, t2 in zip(self.subtasks, self.subtasks[1:]))
                )
            case _:
                return True

    def get_available_statuses(self):
        return {status for status in Status if self._check_status(status)}

    def get_next_statuses(self):
        if self.aggregate and self.subtasks:
            return set()
        next_statuses = set()
        match self.status:
            case Status.NEW | Status.INACTIVE:
                next_statuses = {Status.ACTIVE}
            case Status.ACTIVE:
                next_statuses = {Status.INACTIVE, Status.DONE}
        return next_statuses & self.get_available_statuses()

    def add(self, subtask, index=None):
        if index is None:
            self.subtasks.append(subtask)
            index = len(self.subtasks)
        else:
            self.subtasks.insert(index, subtask)
        subtask.parents.append(self)
        subtask.name = subtask.name.format(index)
        self.refresh()

    def iter_subtasks(self, node_filter=None, depth=None):
        if node_filter is None:
            node_filter = NodeFilter()
        for task in self.subtasks:
            node = Node(self, task, depth)
            if node_filter.check(node):
                yield node
                yield from task.iter_subtasks(node_filter, None if depth is None else depth + 1)
                node_filter.finish(node)

    def is_relevant(self):
        return self.priority > 0 and self.get_next_statuses()

    @property
    def status(self):
        return self.log.get_status()

    @status.setter
    def status(self, value):
        if self.aggregate and self.subtasks:
            return
        self.log.set_status(value)
        self.refresh()

    @property
    def aggregate(self):
        return self._aggregate

    @aggregate.setter
    def aggregate(self, value):
        self._aggregate = value
        self.refresh()

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        self._weight = value if value >= 0 else None
        self.refresh()

    @cached_property
    def progress(self):
        if self.status == Status.DONE:
            return 1.0
        if not self.aggregate:
            return None
        result, weight_sum = 0, 0
        for task in self.subtasks:
            progress = task.progress
            if task.weight is None or progress is None:
                return None
            result += task.weight * progress
            weight_sum += task.weight
        return result / weight_sum if weight_sum > 0 else 0

    def refresh(self):
        if self.aggregate and self.subtasks:
            self.log.set_status(aggregate_status(self.subtasks))
        if hasattr(self, 'progress'):
            del self.progress
        for task in self.parents:
            task.refresh()

    def checkattr(self, attr, value):
        name = f'_check_{attr}'
        if hasattr(self, name):
            return getattr(self, name)(value)
        return True
