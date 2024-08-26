from cmd import Cmd

import getpass
import shelve

from orgmate.task import Task

class CLI(Cmd):
    def __init__(self, clear_state):
        super().__init__()
        self.clear_state = clear_state

    def _select_task(self, task):
        self.task = task
        self.prompt = f'{task.name} > '

    def _list_subtasks(self, max_depth=None):
        self.last_nodes.clear()
        for idx, node in enumerate(self.task.iter_subtasks(max_depth), 1):
            print(idx, '\t'* node.depth + node.task.name)
            self.last_nodes.append(node)

    def preloop(self):
        self.db = shelve.open('state')
        if not self.clear_state and 'root' in self.db:
            self.root = self.db['root']
        else:
            self.root = Task(getpass.getuser())
        self._select_task(self.root)
        self.last_nodes = []

    def postloop(self):
        self.db['root'] = self.root
        self.db.close()

    def do_add(self, arg):
        subtask = Task(arg)
        self.task.add(subtask)

    def do_list(self, _):
        self._list_subtasks(1)

    def do_tree(self, _):
        self._list_subtasks()

    def do_sel(self, arg):
        if not arg:
            self._select_task(self.root)
            return
        idx = int(arg) - 1
        self._select_task(self.last_nodes[idx].task)

    def do_EOF(self, _):
        return True
