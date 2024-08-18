class Task:
    def __init__(self, name):
        self.name = name
        self.subtasks = []

    def append_subtask(self, subtask):
        self.subtasks.append(subtask)
