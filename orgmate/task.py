class Task:
    def __init__(self, name):
        self.name = name
        self.subtasks = []

    def add(self, subtask):
        self.subtasks.append(subtask)
