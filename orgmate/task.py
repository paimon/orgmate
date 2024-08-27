class Node:
    def __init__(self, parent, task, depth):
        self.parent = parent
        self.task = task
        self.depth = depth

    def delete(self):
        self.parent.subtasks.remove(self.task)


class Task:
    def __init__(self, name):
        self.name = name
        self.subtasks = []

    def add(self, subtask):
        self.subtasks.append(subtask)

    def iter_subtasks(self, max_depth=None, depth=0):
        if max_depth is not None and max_depth <= depth:
            return
        for task in self.subtasks:
            yield Node(self, task, depth)
            yield from task.iter_subtasks(max_depth, depth + 1)
