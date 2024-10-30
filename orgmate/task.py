from enum import Enum, auto

from orgmate.log import Log
from orgmate.status import Status


INDENT_WIDTH = 4


class Flow(Enum):
    PARALLEL = auto()
    EXCLUSIVE = auto()
    SEQUENTIAL = auto()

    def __str__(self):
        return self.name.capitalize()


class StatusInvariantViolation(Exception):
    pass


def aggregate_status(subtasks):
    if all(task.status == Status.NEW for task in subtasks):
        return Status.NEW
    if all(task.status == Status.DONE for task in subtasks):
        return Status.DONE
    if any(task.status == Status.ACTIVE for task in subtasks):
        return Status.ACTIVE
    return Status.INACTIVE


class Node:
    def __init__(self, parent, task, depth):
        self.parent = parent
        self.task = task
        self.depth = depth

    def get_name(self):
        indent = ' ' * self.depth * INDENT_WIDTH
        suffix = '/' if self.task.subtasks else ''
        return f'{indent}{self.task.name}{suffix}'

    def insert(self, subtask, after=False):
        idx = self.parent.subtasks.index(self.task)
        self.parent.add(subtask, idx + int(after))

    def remove(self):
        self.parent.subtasks.remove(self.task)
        self.task.parents.remove(self.parent)
        self.parent.update_status()


class NodeFilter:
    def __init__(self, max_depth=None, skip_done=False, skip_seen=True):
        self.max_depth = max_depth
        self.skip_done = skip_done
        self.skip_seen = skip_seen
        self.seen = set()

    def check(self, node):
        if self.max_depth is not None and self.max_depth <= node.depth:
            return False
        if self.skip_done and node.task.status == Status.DONE:
            return False
        if node.parent in self.seen:
            return False
        if self.skip_seen and (node.task in self.seen):
            return False
        return True

    def finish(self, node):
        self.seen.add(node.task)


class Task:
    PUBLIC_FIELDS = ['name', 'flow', 'status', 'priority', 'aggregate']
    PUBLIC_RO_FIELDS = PUBLIC_FIELDS + ['progress']

    def __init__(self, name, status=Status.NEW, context_mode=False):
        self.name = name
        self.parents = []
        self.subtasks = []
        self.log = Log()
        self.jobs = []
        self.note = ''
        self.status = status
        self.flow = Flow.PARALLEL
        self.weight = 1.0
        self.progress = 0
        if context_mode:
            self.aggregate = False
            self.priority = 0
        else:
            self.aggregate = True
            self.priority = 1

    def __repr__(self):
        return f'Task(name={self.name}, status={self.status})'

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

    def check_status(self, status):
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

    def get_available_statuses(self):
        return {status for status in Status if self.check_status(status)}

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
        self.update_status()

    def iter_subtasks(self, node_filter=None, depth=0):
        if node_filter is None:
            node_filter = NodeFilter()
        for task in self.subtasks:
            node = Node(self, task, depth)
            if node_filter.check(node):
                yield node
                yield from task.iter_subtasks(node_filter, depth + 1)
                node_filter.finish(node)

    @property
    def status(self):
        return self.log.get_status()

    @status.setter
    def status(self, value):
        if value not in self.get_available_statuses():
            raise StatusInvariantViolation
        self.log.update_status(value)
        for task in self.parents:
            task.update_status()

    @property
    def aggregate(self):
        return self._aggregate

    @aggregate.setter
    def aggregate(self, value):
        self._aggregate = value
        self.update_status()

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        self._weight = value if value >= 0 else None
        self.update_progress()

    def update_status(self):
        if self.aggregate and self.subtasks:
            self.status = aggregate_status(self.subtasks)
        self.update_progress()

    def _compute_progress(self):
        if self.status == Status.DONE:
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
