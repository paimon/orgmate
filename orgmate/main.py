from argparse import ArgumentParser
from cmd import Cmd
from pathlib import Path

import getpass
import os
import shelve

from orgmate.task import Task


class OrgMate(Cmd):
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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-d', '--dir', default='~/.orgmate')
    parser.add_argument('-c', '--clear-state', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    dir = Path(args.dir).expanduser()
    dir.mkdir(parents=True, exist_ok=True)
    os.chdir(dir)
    OrgMate(args.clear_state).cmdloop()


if __name__ == '__main__':
    main()
