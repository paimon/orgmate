from datetime import timedelta

from orgmate.status import Status, ESC_COLORS as STATUS_ESC_COLORS


class Node:
    PUBLIC_FIELDS = ['name', 'flow', 'status', 'priority', 'aggregate', 'weight']
    PUBLIC_RO_FIELDS = PUBLIC_FIELDS + ['progress', 'duration']

    INDENT_WIDTH = 4
    ESC_RESET = '\033[0m'

    def __init__(self, parent, task, depth=0):
        self.parent = parent
        self.task = task
        self.depth = depth

    def __getattr__(self, attr):
        return str(getattr(self.task, attr))

    @property
    def name(self):
        indent = ' ' * self.depth * self.INDENT_WIDTH if self.depth else ''
        suffix = '/' if self.task.subtasks else ''
        esc_color = STATUS_ESC_COLORS[self.task.status]
        return f'{indent}{esc_color}{self.task.name}{suffix}{self.ESC_RESET}'

    @property
    def duration(self):
        seconds = self.task.log.get_duration().total_seconds()
        return str(timedelta(seconds=round(seconds)))

    @property
    def progress(self):
        val = self.task.progress
        if val is None:
            return '-'
        return f'{100 * val:.2f}%'

    def insert(self, subtask, after=False):
        idx = self.parent.subtasks.index(self.task)
        self.parent.add(subtask, idx + int(after))
        self.parent.refresh()

    def remove(self):
        self.parent.subtasks.remove(self.task)
        self.task.parents.remove(self.parent)
        self.parent.refresh()


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
